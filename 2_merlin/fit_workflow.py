import argparse
from pathlib import Path

import merlin
import metajsonparser as mp
import nvtabular as nvt
from nvtabular.ops import AddTags, Categorify, FillMedian, JoinGroupby, LambdaOp, Rename


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    # Where to store the workflow
    parser.add_argument("--workflow-dir", required=True, type=str)
    # JSON reader settings
    parser.add_argument("--blocksize", default=None, type=str)
    parser.add_argument("--force-host-read", action="store_true")
    parser.add_argument("--pinned-read", action="store_true")
    parser.add_argument("--data-dir", type=str, required=True)

    return parser


def get_nvt_workflow() -> nvt.Workflow:
    id_features = ["user_id",
                   "gmap_id", ] >> Categorify()  # Categorify by default has na_sentinel=0. It works for user_id, gmap_id, category but not work count encoding
    category_feature = ["category"] >> Categorify()

    cont_features = ["latitude", "longitude"] >> AddTags("continuous")

    label_name = nvt.ColumnSelector(["rating"])
    label_feature = label_name >> AddTags(["regression", "target"])
    label_binary_feature = (label_name >> LambdaOp(lambda col: (col > 3).astype("int64")) >> AddTags(
        ["binary_classification", "target"]
    ) >> Rename(name="rating_binary"))

    id_count_encode_features = (id_features >> Rename(postfix="_c") >> JoinGroupby(
        cont_cols=["rating"], stats=["count"], on_host=False
    ) >> FillMedian()  # necessary
                                >> AddTags(["continuous"]))

    output = (id_features + cont_features + category_feature + id_count_encode_features + label_binary_feature)

    workflow = nvt.Workflow(output)
    return workflow


def get_merlin_dataset(suffix: str, args: argparse.Namespace) -> merlin.io.Dataset:
    def _read_ddf(files):
        return mp.read_json_ddf(
            files, blocksize=args.blocksize, force_host_read=args.force_host_read, pinned_read=args.pinned_read
        ).rename(
            columns={f"Column {i}": x for i, x in enumerate(
                ["user_id", "gmap_id", "rating", "category", 'latitude', 'longitude'], start=1
            )}
        )

    ddf = _read_ddf(Path(args.data_path) / f"*_{suffix}.json")

    return merlin.io.Dataset(ddf)


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
