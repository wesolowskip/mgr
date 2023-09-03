import gc
import os
import time
import traceback
from pathlib import Path

from linetimer import CodeTimer

import dask_cudf


def benchmark_read_json(force_host_read, blocksize, cufile_params=None):
    ddf = dask_cudf.read_json(
        "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/*.json", blocksize=blocksize,
    )
    for i in range(2):
        with CodeTimer(f"{i=}, {force_host_read=}, {blocksize=}, {cufile_params=}"):
            rows = ddf.shape[0].compute()
        print(f"{rows=}")


if __name__ == "__main__":

    for blocksize in reversed(["512MiB", "1GiB", "2GiB", "4GiB"]):
        os.environ["CUFILE_ENV_PATH_JSON"] = str(Path(__file__).parent.parent.resolve() / "cufile.json")
        os.environ["LIBCUDF_CUFILE_POLICY"] = "GDS"

        for cufile_thread_count in [64, 32, 16, 8, 4]:  # 64 for NY resulted in OOM
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

        print("Working...")
        os.environ["LIBCUDF_CUFILE_POLICY"] = "OFF"
        benchmark_read_json(
            force_host_read=True, blocksize=blocksize
        )
