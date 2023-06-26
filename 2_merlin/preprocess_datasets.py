import ast
import os
import re
import traceback
from pathlib import Path

import dask.dataframe as dd
import pandas as pd
from dask_ml.model_selection import train_test_split
from tqdm import tqdm
from unidecode import unidecode

DATA_DIR = Path(os.environ["DATA_DIR"])


def dump_to_file(df, fh):
    if df.shape[0]:
        df.to_json(fh, orient="records", lines=True)


def split_to_files(entries, train_f, val_f, train_frac=0.7):
    df = pd.DataFrame(entries)
    df.sort_values("time")
    which_train = df.index <= train_frac * df.shape[0]
    dump_to_file(df.loc[which_train, :], train_f)
    dump_to_file(df.loc[~which_train, :], val_f)


def join_to_json(output_dir, columns_subset=None, client=None, blocksize="1 GiB"):
    (DATA_DIR / output_dir).mkdir(parents=True, exist_ok=True)

    if "STATES" in os.environ:
        states = ast.literal_eval(os.environ["STATES"])
    else:
        states = [re.findall(r"review-(.*?).json", str(x))[0] for x in DATA_DIR.glob("review-*.json")]

    def read_json_user_id_str(*args, **kwargs):
        df = pd.read_json(*args, **kwargs, dtype={"user_id": str, "gmap_id": str})
        return df

    for state in tqdm(states):
        train_reviews_path = DATA_DIR / output_dir / "tmp" / state / "train_reviews.json"
        val_reviews_path = DATA_DIR / output_dir / "tmp" / state / "val_reviews.json"

        #     for state in tqdm(["Other", "Vermont", "North Dakota", "Alaska", "Wyoming", "Delaware"]):
        try:

            state_reviews = dd.read_json(
                DATA_DIR / f"review-{state}.json", lines=True,
                engine=read_json_user_id_str, blocksize=blocksize
            ).dropna(subset=["user_id", "rating"])
            state_reviews["rating"] = state_reviews["rating"].astype(int)

            if columns_subset:
                state_reviews = state_reviews[
                    [x for x in columns_subset if x in state_reviews.columns]]

            train_reviews, val_reviews = train_test_split(state_reviews, test_size=0.2, random_state=0, shuffle=True)
            print("Done split")

            state_meta = pd.read_json(
                DATA_DIR / f"meta-{state}.json", lines=True, dtype={"gmap_id": str}
            ).drop_duplicates("gmap_id").dropna(subset="category").set_index("gmap_id")
            # Removing unicode characters
            state_meta["category"] = (
                state_meta["category"].apply(lambda x: list(map(unidecode, x)))
            )
            print("Done reading state_meta")

            for reviews, which in zip([train_reviews, val_reviews], ["train", "val"]):
                save_path = DATA_DIR / output_dir / f"{state}_{which}.json"
                open(save_path, "w").close()

                with open(save_path, 'a') as f:
                    def save_joined_chunk(df):
                        joined = df.join(state_meta, on="gmap_id", rsuffix="_meta", how="inner")
                        joined["category"] = joined["category"].str.join('|')
                        if columns_subset:
                            joined = joined[columns_subset]
                        if joined.shape[0]:
                            joined.to_json(f, orient="records", lines=True)

                    for df in reviews.partitions:
                        save_joined_chunk(df.compute())
                print(f"Done {which} join")
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
        join_to_json("joined-recommender",
                     ["user_id", "gmap_id", "rating", "category", "latitude", "longitude", "time"],
                     client)
    finally:
        client.shutdown()
