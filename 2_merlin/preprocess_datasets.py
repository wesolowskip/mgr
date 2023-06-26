import ast
import json
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
        df = pd.read_json(*args, **kwargs, dtype={"user_id": str})
        return df

    for state in tqdm(states):
        train_reviews_path = DATA_DIR / output_dir / "tmp" / state / "train_reviews.json"
        val_reviews_path = DATA_DIR / output_dir / "tmp" / state / "val_reviews.json"

        #     for state in tqdm(["Other", "Vermont", "North Dakota", "Alaska", "Wyoming", "Delaware"]):
        try:

            if not train_reviews_path.is_file() or not val_reviews_path.is_file():

                state_reviews = dd.read_json(
                    DATA_DIR / f"review-{state}.json", lines=True,
                    engine=read_json_user_id_str, blocksize=blocksize
                ).dropna(subset=["user_id", "rating"])
                state_reviews["rating"] = state_reviews["rating"].astype(int)

                sorted_state_reviews = state_reviews.set_index("user_id")
                if columns_subset:
                    sorted_state_reviews = sorted_state_reviews[
                        [x for x in columns_subset if x in sorted_state_reviews.columns]]

                # sorted_state_reviews_path = DATA_DIR / output_dir / "tmp" / state / "sorted-state-reviews"
                # sorted_state_reviews_path.mkdir(parents=True, exist_ok=True)
                # sorted_state_reviews.to_parquet(sorted_state_reviews_path)
                # sorted_state_reviews = dd.read_parquet(sorted_state_reviews_path).set_index("user_id", sorted=True)

                all_sorted_reviews_path = DATA_DIR / output_dir / "tmp" / state / "sorted-state-reviews.json.parts"
                shutil.rmtree(all_sorted_reviews_path, ignore_errors=True)
                all_sorted_reviews_path.mkdir(parents=True, exist_ok=True)
                all_reviews_files = sorted_state_reviews.reset_index().to_json(all_sorted_reviews_path, lines=True)
                print(all_reviews_files)

                open(train_reviews_path, "w").close()
                open(val_reviews_path, "w").close()

                with (
                    open(train_reviews_path, "a") as train_f,
                    open(val_reviews_path, "a") as val_f
                ):
                    entries = []
                    user_id = None
                    for fname in all_reviews_files:
                        with open(fname) as f:
                            for line in f:
                                entry = json.loads(line)
                                if user_id is None:
                                    user_id = entry["user_id"]
                                if entry["user_id"] != user_id:
                                    split_to_files(entries, train_f, val_f)
                                    entries = []
                                    user_id = entry["user_id"]
                                entries.append(entry)
                    if entries:
                        split_to_files(entries, train_f, val_f)

            train_reviews = dd.read_json(train_reviews_path, lines=True,
                                         engine=read_json_user_id_str,
                                         blocksize=blocksize
                                         )
            val_reviews = dd.read_json(val_reviews_path, lines=True,
                                       engine=read_json_user_id_str,
                                       blocksize=blocksize
                                       )
            print("Done split")
            state_meta = pd.read_json(DATA_DIR / f"meta-{state}.json", lines=True).drop_duplicates(
                "gmap_id").dropna(subset="category")
            # Removing unicode characters
            state_meta["category"] = (
                state_meta["category"].apply(lambda x: list(map(unidecode, x)))
            )
            print("Start join")
            for reviews, which in zip([train_reviews, val_reviews], ["train", "val"]):
                save_path = DATA_DIR / output_dir / f"{state}_{which}.json"
                open(save_path, "w").close()

                def save_joined_chunk(df):
                    joined = df.join(state_meta, on="gmap_id", rsuffix="_meta", how="inner")
                    joined["category"] = joined["category"].str.join('|')
                    if columns_subset:
                        joined = joined[columns_subset]
                    if joined.shape[0]:
                        joined.to_json(save_path, orient="records", lines=True, mode='a')

                # NOTE THAT IT HAS TO BE DONE ON A SINGLE WORKER!!!!
                reviews.map_partitions(save_joined_chunk).compute()
                print(f"Finished {which} join")
            #     joined = reviews.join(state_meta.set_index("gmap_id"), on=["gmap_id"], lsuffix="_review",
            #                           rsuffix="_meta", how="inner")
            #     joined["category"] = joined["category"].str.join('|')
            #
            #     if columns_subset:
            #         joined = joined[columns_subset]
            #     print("Done join")
            #
            #     parts_path = DATA_DIR / output_dir / f"{state}_{which}.json.parts"
            #     dd.to_json(joined, parts_path)
            #     with open(DATA_DIR / output_dir / f"{state}_{which}.json", "w") as f:
            #         for fname in parts_path.glob("*.part"):
            #             with open(fname) as src:
            #                 for line in src:
            #                     # for line in islice(src, 0, 5000):
            #                     f.write(line)
            #     shutil.rmtree(parts_path)
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
                     client)
    finally:
        client.shutdown()
