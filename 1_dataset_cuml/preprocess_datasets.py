import os
import re
import shutil
from pathlib import Path

import dask.dataframe as dd
import pandas as pd
from tqdm import tqdm
from unidecode import unidecode

DATA_DIR = Path(os.environ["DATA_DIR"])


def join_to_json(output_dir, columns_subset=None):
    (DATA_DIR / output_dir).mkdir(parents=True, exist_ok=True)

    states = [re.findall(r"review-(.*?).json", str(x))[0] for x in DATA_DIR.glob("review-*.json")]

    def read_json_user_id_str(*args, **kwargs):
        df = pd.read_json(*args, **kwargs, dtype={"user_id": str})
        return df

    for state in tqdm(states):
        #     for state in tqdm(["Other", "Vermont", "North Dakota", "Alaska", "Wyoming", "Delaware"]):
        try:
            state_reviews = dd.read_json(
                DATA_DIR / f"review-{state}.json", lines=True,
                engine=read_json_user_id_str, blocksize=None
            ).dropna(subset=["user_id", "rating"])
            state_reviews["rating"] = state_reviews["rating"].astype(int)

            state_meta = pd.read_json(DATA_DIR / f"meta-{state}.json", lines=True).drop_duplicates(
                "gmap_id").dropna(subset="category")
            # Removing unicode characters
            state_meta["category"] = (
                state_meta["category"].apply(lambda x: list(map(unidecode, x)))
            )

            joined = state_reviews.join(state_meta.set_index("gmap_id"), on=["gmap_id"], lsuffix="_review",
                                        rsuffix="_meta", how="inner")
            joined["category"] = joined["category"].str.join('|')

            if columns_subset:
                joined = joined[columns_subset]

            parts_path = DATA_DIR / output_dir / f"{state}.json.parts"
            dd.to_json(joined, parts_path)
            with open(DATA_DIR / output_dir / f"{state}.json", "w") as f:
                for fname in parts_path.glob("*.part"):
                    with open(fname) as src:
                        for line in src:
                            # for line in islice(src, 0, 5000):
                            f.write(line)
            shutil.rmtree(parts_path)
        except Exception as e:
            print("Exception", state, e)
            print("Going to the next state...")


if __name__ == "__main__":

    from dask.distributed import Client
    import logging

    num_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", 1))
    print(f"{num_cpus=}")
    client = Client(silence_logs=logging.ERROR, n_workers=num_cpus,
                    dashboard_address="0.0.0.0:8787")

    try:
        # join_to_json("joined_columns_all")
        join_to_json("joined-cuml",
                     ["user_id", "gmap_id", "rating", "category", "latitude", "longitude", "time"])
    finally:
        client.shutdown()
