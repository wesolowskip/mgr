if __name__ == "__main__":

    import argparse
    import os
    from pathlib import Path

    import numba.cuda
    from dask.distributed import Client
    from cuda_cluster import CPUAgnosticCUDACluster
    from dask_cuda import LocalCUDACluster

    print(numba.cuda.gpus)


    def get_parser():
        parser = argparse.ArgumentParser()
        default_data_dir = "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml"
        parser.add_argument("--data-dir", default=default_data_dir)
        parser.add_argument("--files", nargs="*")
        parser.add_argument("--reps", default=5, type=int)
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

    cluster = CPUAgnosticCUDACluster(
        local_directory=Path(args.data_dir) / "tmp", shared_filesystem=True,
        threads_per_worker=int(os.environ.get("SLURM_CPUS_PER_TASK", 1)) // len(numba.cuda.gpus),
        protocol=args.protocol, enable_infiniband=args.enable_infiniband, enable_nvlink=args.enable_nvlink,
        rmm_pool_size=args.rmm_pool_size, pre_import=["cudf", "metajsonparser"], jit_unspill=args.jit_unspill
        # Test czy nie bedzie OOM
    )
    client = Client(cluster)

    import metajsonparser as mp
    from linetimer import CodeTimer


    def read_ddf(path):
        input_ddf = mp.read_json_ddf(
            path, blocksize=args.mp_blocksize, force_host_read=args.mp_force_host_read, pinned_read=args.mp_pinned_read,
            force_gpu_preprocess=args.mp_force_gpu_preprocess
        )
        if len(input_ddf.columns) > 3:
            input_ddf = input_ddf.rename(
                columns=dict(
                    zip(input_ddf.columns, ["user_id", "gmap_id", "rating", "category", "latitude", "longitude"])
                )
            )
            input_ddf = input_ddf[["rating", "latitude", "longitude"]]
        else:
            input_ddf = input_ddf.rename(columns=dict(zip(input_ddf.columns, ["rating", "latitude", "longitude"])))
        return input_ddf


    for _ in range(args.reps):
        with CodeTimer("ddf-preprocessing"):
            if args.files:
                paths = [str(Path(args.data_dir) / f) for f in args.files]
            else:
                paths = [str(p) for p in Path(args.data_dir).glob("*.json")]
            ddf = read_ddf(paths)

    for _ in range(args.reps):
        with CodeTimer("ddf-shape"):
            num_rows = ddf.shape[0].compute()
        print(f"{num_rows=}")
