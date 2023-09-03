import gc
import os
import time
import traceback
from pathlib import Path

os.environ["CUFILE_ENV_PATH_JSON"] = str(Path(__file__).parent.parent.resolve() / "cufile.json")

from linetimer import CodeTimer
import cudf

# 484M	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/West Virginia.json
# 1.1G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Iowa.json
# 2.0G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Alabama.json
# 4.0G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Arizona.json
# 7.1G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/New York.json
# 15G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/California.json


files_lines = {
    "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/West Virginia.json": 2187197,
    "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Iowa.json": 4799312,
    "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Alabama.json": 8900582,
    "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Arizona.json": 18264679,
    "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/New York.json": 33271516,
    # Caifornia resulted in OOM
    # "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/California.json": 70064610,
}


def benchmark_read_json(fname):
    for i in range(11):
        with CodeTimer(
                f"{i=}, {fname=}, {os.environ['LIBCUDF_CUFILE_POLICY']=}, {os.environ['LIBCUDF_CUFILE_THREAD_COUNT']=}, {os.environ['LIBCUDF_CUFILE_SLICE_SIZE']=}"
        ):
            df = cudf.read_json(fname, lines=True, engine="cudf", compression=None)
            shape = df.shape
        print(f"{shape=}")
        print(f"{df.memory_usage()=}")
        del df


for file in files_lines:

    try:
        benchmark_read_json(file)
    except Exception:
        traceback.print_exc()
    gc.collect()
    time.sleep(1)
