import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import metajsonparser as mp
import numba.cuda
import seaborn as sns
from cuml.dask.cluster import KMeans
from dask.distributed import Client, performance_report
from dask_cuda import LocalCUDACluster
from dask_ml.preprocessing import MinMaxScaler
from linetimer import CodeTimer

if __name__ == "__main__":

    print(numba.cuda.gpus)


    def get_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--data-dir", default="/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml")
        parser.add_argument("--files", nargs="+", default=["*.json"])
        parser.add_argument("--reps", default=1, type=int)
        parser.add_argument("--protocol", choices=["tcp", "ucx"])
        parser.add_argument("--enable-infiniband", action="store_true")
        parser.add_argument("--enable-nvlink", action="store_true", help='requires protocol="ucx"')
        parser.add_argument("--rmm-pool-size", type=float, required=False)
        parser.add_argument("--jit-unspill", action="store_true")
        parser.add_argument("--mp-blocksize", required=True)
        parser.add_argument("--mp-force-host-read", action="store_true")
        parser.add_argument("--mp-pinned-read", action="store_true")
        parser.add_argument("--mp-force-gpu-preprocess", action="store_true")
        return parser


    parser = get_parser()
    args = parser.parse_args()

    print(f"{args=}")

    slurm_job_id = os.environ["SLURM_JOB_ID"]
    results_dir = Path(f"results-{slurm_job_id}")
    results_dir.mkdir()

    cluster = LocalCUDACluster(
        local_directory=Path(args.data_dir) / "tmp",
        shared_filesystem=True,
        protocol=args.protocol,
        enable_infiniband=args.enable_infiniband,
        enable_nvlink=args.enable_nvlink,
        rmm_pool_size=args.rmm_pool_size,
        pre_import=["cudf", "metajsonparser"],
        jit_unspill=args.jit_unspill  # Test czy nie bedzie OOM
    )
    client = Client(cluster)


    def read_ddf(path):
        input_ddf = mp.read_json_ddf(
            path, blocksize=args.mp_blocksize, force_host_read=args.mp_force_host_read, pinned_read=args.mp_pinned_read,
            force_gpu_preprocess=args.mp_force_gpu_preprocess
        )
        if len(input_ddf.columns) > 3:
            input_ddf = input_ddf.rename(
                columns=dict(zip(input_ddf.columns, ["user_id", "gmap_id", "rating", "category", "latitude", "longitude"]))
            )
            input_ddf = input_ddf[["rating", "latitude", "longitude"]]
        else:
            input_ddf = input_ddf.rename(
                columns=dict(zip(input_ddf.columns, ["rating", "latitude", "longitude"]))
            )
        return input_ddf


    for _ in range(args.reps):
        with CodeTimer("ddf-preprocessing"):
            ddf = read_ddf([Path(args.data_dir) / f for f in args.files])

    scaler = MinMaxScaler()

    for _ in range(args.reps):
        with performance_report(filename=results_dir / "dask-scaler-report.html"):
            with CodeTimer("ddf-scaler-fit"):
                ddf = scaler.fit_transform(ddf)

    cluster_counts = list(range(1, 11))
    for _ in range(args.reps):
        scores = []
        for k in cluster_counts:
            print(f"Fitting kmeans with {k} clusters")
            kmeans = KMeans(n_clusters=k, client=client, random_state=1)

            with performance_report(filename=results_dir / f"dask-kmeans-fit-{k}-report.html"):
                with CodeTimer("ddf-kmeans-fit"):
                    kmeans.fit(ddf)

            with performance_report(filename=results_dir / f"dask-kmeans-score-{k}-report.html"):
                with CodeTimer("ddf-kmeans-score"):
                    score = kmeans.score(ddf)
                    scores.append(score.get())

    print(f"{client.get_worker_logs()=}")

    print(f"{scores=}")
    ax = sns.lineplot(x=cluster_counts, y=scores)
    ax.set_xlabel("cluster count")
    ax.set_ylabel("interia score")
    plt.savefig(results_dir / "kmeans-scores.jpg")

    client.shutdown()
