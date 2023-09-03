import gc
import os
import time
import traceback
from pathlib import Path

os.environ["CUFILE_ENV_PATH_JSON"] = str(Path(__file__).parent.parent.resolve() / "cufile.json")

from linetimer import CodeTimer

import dask_cudf


def benchmark_read_json(blocksize):
    ddf = dask_cudf.read_json(
        "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/*.json", blocksize=blocksize, lines=True, engine="cudf",
        compression=None
    )
    ddf.head()
    time.sleep(1)
    with CodeTimer(
            f"{blocksize=}, {os.environ['LIBCUDF_CUFILE_POLICY']=}, {os.environ.get('LIBCUDF_CUFILE_THREAD_COUNT')=}, {os.environ.get('LIBCUDF_CUFILE_SLICE_SIZE')=}"
    ):
        rows = ddf.shape[0].compute()
    print(f"{rows=}")


if __name__ == "__main__":

    for blocksize in ["512MiB", "1GiB", "2GiB", "4GiB"]:

        try:

            print("Working...")
            benchmark_read_json(blocksize=blocksize)
        except Exception:
            traceback.print_exc()
            break
        finally:
            gc.collect()
            time.sleep(1)
