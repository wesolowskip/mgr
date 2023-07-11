# This workflow fitting was not possible in cudf due to max character limit reached
import argparse
from pathlib import Path

import dask.dataframe as dd
import merlin
import nvtabular as nvt
from nvtabular.ops import AddTags, Categorify, LambdaOp, Rename, JoinGroupby, FillMedian


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-dir", type=str, required=True)
    parser.add_argument("--data-dir", type=str, required=True)
    parser.add_argument("--blocksize", type=str, default=None)

    return parser


def get_nvt_workflow() -> nvt.Workflow:
    id_features = ["user_id",
                   "gmap_id", ] >> Categorify()  # Categorify by default has na_sentinel=0. It works for user_id, gmap_id, category but not work count encoding
    # multi hot are not currently supported https://nvidia-merlin.github.io/NVTabular/main/api/tensorflow_dataloader.html
    category_feature = ["category"] >> Categorify()

    cont_features = ["latitude", "longitude"] >> AddTags("continuous")

    label_name = nvt.ColumnSelector(["rating"])
    label_feature = label_name >> AddTags(["regression", "target"])
    label_binary_feature = (label_name >> LambdaOp(lambda col: (col > 3).astype("int64")) >> AddTags(
        ["binary_classification", "target"]
    ) >> Rename(name="rating_binary"))

    # DIDNT WORK
    # DUE TO non numeric values
    # id_count_encode_features = (id_features >> Rename(postfix="_c") >> JoinGroupby(
    #     cont_cols=["rating"], stats=["count"], on_host=True
    # ) >> FillMedian() >> AddTags(["continuous"]))

    output = (id_features + cont_features + category_feature + label_binary_feature)

    workflow = nvt.Workflow(output)
    return workflow


def get_merlin_dataset(suffix: str, args: argparse.Namespace) -> merlin.io.Dataset:
    ddf = dd.read_json(
        Path(args.data_dir) / f"*_{suffix}.json",
        dtype={
            "user_id": str, "gmap_id": str, "rating": int, "category": str, "latitude": float, "longitude": float,
            "time": int
        },
        blocksize=args.blocksize,
        lines=True
    )
    ddf["category"] = ddf["category"].str.split("|")
    ddf = ddf.explode("category")

    return merlin.io.Dataset(ddf, cpu=True)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    print(f"{args=}")
    workflow = get_nvt_workflow()

    train_merlin_ds = get_merlin_dataset("train", args)
    val_merlin_ds = get_merlin_dataset("val", args)

    workflow = get_nvt_workflow()
    workflow.fit(train_merlin_ds)
    workflow.save(str(Path(args.workflow_dir) / "workflow"))

    print(f"{nvt.ops.get_embedding_sizes(workflow)=}")

    train_merlin_ds = workflow.transform(train_merlin_ds)
    val_merlin_ds = workflow.transform(val_merlin_ds)

    print(f"{train_merlin_ds.head()=}")
    print(f"{train_merlin_ds.tail()=}")
    print(f"{val_merlin_ds.head()=}")
    print(f"{val_merlin_ds.tail()=}")
