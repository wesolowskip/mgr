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


def benchmark_read_json(fname, count, force_host_read, pinned_read=None, cufile_params=None):
    for i in range(11):
        with CodeTimer(f"{i=}, {fname=}, {count=}, {force_host_read=}, {pinned_read=}, {cufile_params=}"):
            df = mp.read_json(fname, count, eol="unix", force_host_read=force_host_read, pinned_read=bool(pinned_read))
            shape = df.shape
        print(f"{shape=}")
        print(f"{df.memory_usage()=}")
        del df


for file, lines in files_lines.items():
    benchmark_read_json(file, lines, force_host_read=True, pinned_read=False)
    benchmark_read_json(file, lines, force_host_read=True, pinned_read=True)

    for cufile_thread_count in [4, 8, 16, 32, 64]:  # 64 for NY resulted in OOM
        for cufile_slice_size_mb in [1, 2, 4, 8, 16]:
            try:
                os.environ["LIBCUDF_CUFILE_THREAD_COUNT"] = str(cufile_thread_count)
                os.environ["LIBCUDF_CUFILE_SLICE_SIZE"] = str(cufile_slice_size_mb * 1024 * 1024)
                benchmark_read_json(file, lines, force_host_read=False,
                                    cufile_params=f"{cufile_thread_count=}, {cufile_slice_size_mb=}")
            except Exception:
                traceback.print_exc()
            gc.collect()
            time.sleep(1)
