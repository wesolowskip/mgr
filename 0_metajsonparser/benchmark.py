import os
from pathlib import Path
from string import Template

from linetimer import CodeTimer

# 484M	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/West Virginia.json
# 1.1G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Iowa.json
# 2.0G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Alabama.json
# 4.0G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Arizona.json
# 7.1G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/New York.json
# 15G	/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/California.json


files_lines = {"/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/West Virginia.json": 2187197,
               "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Iowa.json": 4799312,
               "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Alabama.json": 8900582,
               "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/Arizona.json": 18264679,
               "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/New York.json": 33271516,
               "/scratch/shared/pwesolowski/mgr-pipeline/joined-cuml/California.json": 70064610, }


def benchmark_read_json(fname, count, force_host_read, pinned_read=None, cufile_json_params=None):
    for i in range(11):
        with CodeTimer(f"{i=}, {fname=}, {count=}, {force_host_read=}, {pinned_read=}, {cufile_json_params=}"):
            df = mp.read_json(fname, count, eol="unix", force_host_read=force_host_read, pinned_read=bool(pinned_read))


if __name__ == "__main__":
    for file, lines in files_lines.items():
        benchmark_read_json(file, lines, force_host_read=True, pinned_read=False)
        benchmark_read_json(file, lines, force_host_read=True, pinned_read=True)

        this_dir = Path(__file__).parent.resolve()
        cufile_template_path = this_dir / "cufile_template.json"
        cufile_path = this_dir / "cufile.json"

        os.environ["CUFILE_ENV_PATH_JSON"] = str(cufile_path)

        import cudf
        import metajsonparser as mp

        with open(cufile_template_path) as f:
            cufile_template = Template(f.read())

        for parallel_io in ["false", "true"]:
            for max_io_threads in [0] if parallel_io == "false" else [4, 8, 16, 32, 64]:
                for use_poll_mode in ["false", "true"]:
                    for poll_mode_max_size_kb in [4] if use_poll_mode == "false" else [4, 512, 1024, 2048]:
                        cufile_params = {"parallel_io": parallel_io, "max_io_threads": max_io_threads,
                                         "use_poll_mode": use_poll_mode, "poll_mode_max_size_kb": poll_mode_max_size_kb}
                        with open(cufile_path, "w") as f:
                            f.write(cufile_template.substitute(**cufile_params))
                        benchmark_read_json(file, lines, force_host_read=False, cufile_json_params=cufile_params)
