import argparse
import os
from pathlib import Path
from timeit import default_timer as timer
from typing import Union

os.environ["TF_MEMORY_ALLOCATION"] = "0.3"

import dask_cudf
import merlin.models.tf as mm
import metajsonparser as mp
import nvtabular as nvt
import tensorflow as tf
from dask.distributed import Client
from dask_cuda import LocalCUDACluster
from nvtabular.loader.tensorflow import KerasSequenceLoader, KerasSequenceValidater
from nvtabular.ops import Categorify, JoinGroupby, Rename, AddTags, LambdaOp, FillMedian

import rmm
import merlin
from merlin.core.utils import device_mem_size


def get_dask_client(args: argparse.Namespace):
    def parse_memory(text: str) -> Union[int, float, str]:
        if text is None:
            return None
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    device_spill_frac = 0.5  # Spill GPU-Worker memory to host at this limit.
    capacity = device_mem_size(kind="total")
    # Reduce if spilling fails to prevent
    # device memory errors.
    cluster = LocalCUDACluster(
        protocol=args.protocol,
        threads_per_worker=args.threads_per_worker,
        enable_infiniband=args.enable_infiniband,
        enable_nvlink=args.enable_nvlink,
        rmm_pool_size=parse_memory(args.rmm_pool_size),
        device_memory_limit=capacity * device_spill_frac,
    )

    client = Client(cluster)

    def _rmm_pool():
        rmm.reinitialize(
            pool_allocator=True,
            initial_pool_size=None,  # Use default size
        )

    client.run(_rmm_pool)
    return client


def get_nvt_workflow() -> nvt.Workflow:
    id_features = ["user_id",
                   "gmap_id", ] >> Categorify()  # Categorify by default has na_sentinel=0. It works for user_id, gmap_id, category but not work count encoding
    category_feature = ["category"] >> Categorify()

    cont_features = ["latitude", "longitude"] >> AddTags("continuous")

    label_name = nvt.ColumnSelector(["rating"])
    label_feature = label_name >> AddTags(["regression", "target"])
    label_binary_feature = (label_name >> LambdaOp(lambda col: (col > 3).astype("int64")) >> AddTags(
        ["binary_classification", "target"]) >> Rename(name="rating_binary"))

    id_count_encode_features = (
            id_features >> Rename(postfix="_c") >> JoinGroupby(cont_cols=["rating"], stats=["count"],
                                                               on_host=False) >> FillMedian()  # necessary
            >> AddTags(["continuous"]))

    output = (id_features + cont_features + category_feature + id_count_encode_features + label_binary_feature)

    workflow = nvt.Workflow(output)
    return workflow


def get_merlin_dataset(suffix: str, args: argparse.Namespace) -> merlin.io.Dataset:
    if args.dask_parser:
        def _read_ddf(files):
            return dask_cudf.read_json(files, blocksize=args.blocksize, lines=True)
    else:
        def _read_ddf(files):
            return mp.read_json_ddf(files, blocksize=args.blocksize, force_host_read=args.force_host_read,
                                    pinned_read=args.pinned_read).rename(columns={f"Column {i}": x for i, x in
                                                                                  enumerate(
                                                                                      ["user_id", "gmap_id", "rating",
                                                                                       "category", 'latitude',
                                                                                       'longitude'], start=1)})

    ddf = _read_ddf(Path(args.data_path) / f"*_{suffix}.json")

    return merlin.io.Dataset(ddf)


def transform_dataset(ds: merlin.io.Dataset, workflow: nvt.Workflow) -> merlin.io.Dataset:
    return workflow.transform(ds)


def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    # Dask cluster settings
    parser.add_argument("--threads-per-worker", default=1, type=int)
    parser.add_argument("--protocol", default=None, type=str)
    parser.add_argument("--enable-infiniband", action="store_true")
    parser.add_argument("--enable-nvlink", action="store_true")
    parser.add_argument("--rmm-pool-size", default=None, type=str)
    # JSON reader settings
    parser.add_argument("--dask-parser", action="store_true")
    parser.add_argument("--blocksize", default=None, type=str)
    parser.add_argument("--force-host-read", action="store_true")
    parser.add_argument("--pinned-read", action="store_true")
    parser.add_argument("--data-path", type=str, required=True)
    # TF pipeline settings
    parser.add_argument("--parts-per-chunk", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, required=True)

    return parser


def get_tf_dataset(ds: merlin.io.Dataset, shuffle: bool, args: argparse.Namespace):
    categorical_columns = ["user_id", "gmap_id"]  # Single-hot
    categorical_mh_columns = ["category"]  # Multi-hot
    numeric_columns = ["latitude", "longitude", "user_id_c_count", "gmap_id_c_count"]

    return KerasSequenceLoader(ds, batch_size=args.batch_size, label_names=["rating_binary"],
                               cat_names=categorical_columns + categorical_mh_columns, cont_names=numeric_columns,
                               shuffle=shuffle, parts_per_chunk=args.parts_per_chunk, )


def get_class_weights(ds: merlin.io.Dataset) -> dict:
    neg, pos = (1 - ds.to_ddf()["rating_binary"]).sum().compute(), ds.to_ddf()["rating_binary"].sum().compute()
    total = neg + pos

    weight_for_0 = (1 / neg) * (total / 2.0)
    weight_for_1 = (1 / pos) * (total / 2.0)

    return {0: weight_for_0, 1: weight_for_1}


def get_model(schema) -> tf.keras.Model:  # merlin models subclass tf.keras.Model
    metrics = [tf.keras.metrics.TruePositives(name="tp"), tf.keras.metrics.FalsePositives(name="fp"),
               tf.keras.metrics.TrueNegatives(name="tn"), tf.keras.metrics.FalseNegatives(name="fn"),
               tf.keras.metrics.BinaryAccuracy(name="binary_accuracy"), tf.keras.metrics.Precision(name="precision"),
               tf.keras.metrics.Recall(name="recall"), tf.keras.metrics.AUC(name="auc"), ]

    model = mm.DLRMModel(schema, embedding_dim=64, bottom_block=mm.MLPBlock([128, 64]),
                         top_block=mm.MLPBlock([128, 64, 32]), prediction_tasks=mm.OutputBlock(schema), )

    model.compile(optimizer="adam", metrics=metrics)
    return model


def measure_tf_ds_throughput(tf_ds) -> tuple[int, list]:
    times = []
    for _ in range(10):
        batches = 0
        start = timer()
        for X, y in tf_ds:
            batches += 1
        end = timer()
        times.append(end - start)
    return batches, times


class EpochTimeCallback(tf.keras.callbacks.Callback):
    def __init__(self):
        self.times = []
        self.time = None

    def on_epoch_begin(self, epoch, logs={}):
        self.time = timer()

    def on_epoch_end(self, epoch, logs={}):
        self.times.append(timer() - self.time)
        self.time = None


class PredictionTimeCallback(tf.keras.callbacks.Callback):
    def __init__(self):
        self.times = []
        self.time = None

    def on_predict_begin(self, logs={}):
        self.time = timer()

    def on_predict_end(self, logs={}):
        self.times.append(timer() - self.time)
        self.time = None


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()

    client = get_dask_client(args)
    print(f"{client=}")

    workflow = get_nvt_workflow()

    train_merlin_ds = get_merlin_dataset("train", args)
    val_merlin_ds = get_merlin_dataset("val", args)

    workflow.fit(train_merlin_ds)

    print(f"{nvt.ops.get_embedding_sizes(workflow)=}")

    train_merlin_ds = transform_dataset(train_merlin_ds, workflow)
    val_merlin_ds = transform_dataset(val_merlin_ds, workflow)

    print(f"{train_merlin_ds.head()=}")
    print(f"{train_merlin_ds.tail()=}")
    print(f"{val_merlin_ds.head()=}")
    print(f"{val_merlin_ds.tail()=}")

    train_tf_ds = get_tf_dataset(train_merlin_ds, True, args)
    val_tf_ds = get_tf_dataset(val_merlin_ds, False, args)

    model = get_model(train_tf_ds.output_schema)
    class_weights = get_class_weights(train_merlin_ds)

    validation_callback = KerasSequenceValidater(val_tf_ds)
    epoch_time_callback = EpochTimeCallback()
    prediction_time_callback = PredictionTimeCallback()

    # Order of callbacks matter!!!
    model.fit(train_tf_ds, callbacks=[epoch_time_callback, validation_callback], epochs=args.epochs,
              class_weight=class_weights, )

    for _ in range(10):
        model.predict(val_tf_ds, callbacks=[prediction_time_callback])

    print("Done")
    print(f"{epoch_time_callback.times=}")
    print(f"{prediction_time_callback.times=}")

    batches_train, times_train = measure_tf_ds_throughput(train_tf_ds)
    print("Done")
    print(f"Processed {batches_train} batches in {times_train} seconds")

    batches_val, times_val = measure_tf_ds_throughput(val_tf_ds)
    print("Done")
    print(f"Processed {batches_val} batches in {times_val} seconds")
