import gc
import os
import time
import traceback
from pathlib import Path

os.environ["CUFILE_ENV_PATH_JSON"] = str(Path(__file__).parent.resolve() / "cufile.json")
os.environ["LIBCUDF_CUFILE_POLICY"] = "GDS"

from linetimer import CodeTimer

import cudf
import metajsonparser as mp


def benchmark_read_json(force_host_read, blocksize, cufile_params=None):
    ddf = mp.read_json_ddf(
        "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/*.json", meta=None, blocksize=blocksize,
        force_gpu_preprocess=False, force_host_read=force_host_read, pinned_read=False
    )
    for i in range(11):
        with CodeTimer(f"{i=}, {force_host_read=}, {blocksize=}, {cufile_params=}"):
            rows = ddf.shape[0].compute()
        print(f"{rows=}")


if __name__ == "__main__":

    for blocksize in ["512MiB", "1GiB", "2GiB", "4GiB", "8GiB"]:
        print("Working...")
        benchmark_read_json(
            force_host_read=True, blocksize=blocksize
        )

        for cufile_thread_count in [4, 8, 16, 32, 64]:  # 64 for NY resulted in OOM
            for cufile_slice_size_mb in [1]:

                try:
                    os.environ["LIBCUDF_CUFILE_THREAD_COUNT"] = str(cufile_thread_count)
                    os.environ["LIBCUDF_CUFILE_SLICE_SIZE"] = str(cufile_slice_size_mb * 1024 * 1024)
                    print("Working...")
                    benchmark_read_json(
                        force_host_read=False, blocksize=blocksize,
                        cufile_params=f"{cufile_thread_count=}, {cufile_slice_size_mb=}"
                    )
                except Exception:
                    traceback.print_exc()
                gc.collect()
                time.sleep(1)
