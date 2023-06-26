import os
import re
import shutil
import traceback
from pathlib import Path

import dask.dataframe as dd
import pandas as pd
from tqdm import tqdm
from unidecode import unidecode

DATA_DIR = Path(os.environ["DATA_DIR"])


def join_to_json(output_dir, columns_subset=None, train_frac=0.8, client=None):
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
                engine=read_json_user_id_str, blocksize="1 GiB"
            ).dropna(subset=["user_id", "rating"])
            state_reviews["rating"] = state_reviews["rating"].astype(int)

            # Dividing into train and validation subsets
            # state_reviews["user_id_time"] = state_reviews[["user_id", "time"]].apply(tuple, axis=1)
            sorted_state_reviews = state_reviews.sort_values("time", ascending=True)
            sorted_state_reviews = sorted_state_reviews.set_index("user_id")
            print(f"{sorted_state_reviews.divisions=}")
            if columns_subset:
                sorted_state_reviews = sorted_state_reviews[
                    [x for x in columns_subset if x in sorted_state_reviews.columns]]

            # sorted_state_reviews_path = DATA_DIR / output_dir / "tmp" / state / "sorted-state-reviews"
            # sorted_state_reviews_path.mkdir(parents=True, exist_ok=True)
            # sorted_state_reviews.to_parquet(sorted_state_reviews_path)
            # sorted_state_reviews = dd.read_parquet(sorted_state_reviews_path).set_index("user_id", sorted=True)

            user_id_counts = state_reviews["user_id"].value_counts().compute()
            print("Done user_id_counts")
            enumerate_groups = sorted_state_reviews.groupby("user_id").cumcount().compute()
            print("Done enumerate_groups")
            train_offset = (
                    sorted_state_reviews.index.to_series().map(user_id_counts) * train_frac).compute()
            print("Done train_offset")
            flags = (enumerate_groups > train_offset)
            print("Done flags")
            del train_offset
            del enumerate_groups
            del user_id_counts

            train_reviews = sorted_state_reviews.loc[flags[~flags].index, :]
            val_reviews = sorted_state_reviews.loc[flags[flags].index, :]
            print("Done split")
            state_meta = pd.read_json(DATA_DIR / f"meta-{state}.json", lines=True).drop_duplicates(
                "gmap_id").dropna(subset="category")
            # Removing unicode characters
            state_meta["category"] = (
                state_meta["category"].apply(lambda x: list(map(unidecode, x)))
            )

            for reviews, which in zip([train_reviews, val_reviews], ["train", "val"]):

                joined = reviews.reset_index().join(state_meta.set_index("gmap_id"), on=["gmap_id"], lsuffix="_review",
                                                    rsuffix="_meta", how="inner")
                joined["category"] = joined["category"].str.join('|')

                if columns_subset:
                    joined = joined[columns_subset]
                print("Done join")

                parts_path = DATA_DIR / output_dir / f"{state}_{which}.json.parts"
                dd.to_json(joined, parts_path)
                with open(DATA_DIR / output_dir / f"{state}_{which}.json", "w") as f:
                    for fname in parts_path.glob("*.part"):
                        with open(fname) as src:
                            for line in src:
                                # for line in islice(src, 0, 5000):
                                f.write(line)
                shutil.rmtree(parts_path)
        except Exception as e:
            tb = traceback.format_exc()
            print("Exception", state, e, tb)
            if client is not None:
                print(f"{client.get_worker_logs()=}")
            print("Going to the next state...")


if __name__ == "__main__":

    from dask.distributed import Client
    import logging

    num_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", 1))
    print(f"{num_cpus=}")
    client = Client(silence_logs=logging.ERROR, n_workers=num_cpus,
                    dashboard_address="0.0.0.0:8797")

    try:
        # join_to_json("joined_columns_all")
        join_to_json("joined-merlin",
                     ["user_id", "gmap_id", "rating", "category", "latitude", "longitude", "time"],
                     client=client)
    finally:
        client.shutdown()
