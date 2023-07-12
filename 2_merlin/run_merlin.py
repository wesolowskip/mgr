import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser()
# Workflow settings
parser.add_argument("--workflow-dir", type=str, required=True)
# JSON reader settings
parser.add_argument("--blocksize", default=None, type=str)
parser.add_argument("--force-host-read", action="store_true")
parser.add_argument("--data-path", type=str, required=True)
parser.add_argument("--cufile-thread-count", type=str, required=False)
# TF pipeline settings
parser.add_argument("--parts-per-chunk", type=int, required=True)
parser.add_argument("--batch-size", type=int, default=16384)
parser.add_argument("--epochs", type=int, required=True)
args = parser.parse_args()

os.environ["TF_MEMORY_ALLOCATION"] = "0.5"
if args.cufile_thread_count:
    os.environ["LIBCUDF_CUFILE_THREAD_COUNT"] = args.cufile_thread_count

import cupy
from linetimer import CodeTimer
import merlin.models.tf as mm
import metajsonparser as mp
import nvtabular as nvt
from nvtabular.loader.tensorflow import KerasSequenceLoader

import merlin

import tensorflow as tf
import horovod.tensorflow as hvd

hvd.init()
cupy.random.seed(None)


def seed_fn():
    min_int, max_int = tf.int32.limits
    max_rand = max_int // hvd.size()

    # Generate a seed fragment on each worker
    seed_fragment = cupy.random.randint(0, max_rand).get()

    # Aggregate seed fragments from all Horovod workers
    seed_tensor = tf.constant(seed_fragment)
    reduced_seed = hvd.allreduce(seed_tensor, name="shuffle_seed", op=hvd.mpi_ops.Sum)

    return reduced_seed % max_rand


workflow = nvt.Workflow.load(str(Path(args.workflow_dir) / "workflow"))
print(f"{nvt.ops.get_embedding_sizes(workflow)=}")


def get_merlin_dataset(suffix: str, args: argparse.Namespace) -> merlin.io.Dataset:
    def _read_ddf(files):
        return mp.read_json_ddf(
            files, blocksize=args.blocksize, force_host_read=args.force_host_read, pinned_read=False
        ).rename(
            columns={f"Column {i}": x for i, x in enumerate(
                ["user_id", "gmap_id", "rating", "category", 'latitude', 'longitude'], start=1
            )}
        )

    ddf = _read_ddf(Path(args.data_path) / f"*_{suffix}.json")
    ddf["category"] = ddf["category"].str.split("|")
    ddf = ddf.explode("category")

    return merlin.io.Dataset(ddf)


train_merlin_ds = get_merlin_dataset("train", args)
val_merlin_ds = get_merlin_dataset("val", args)

train_merlin_ds = workflow.transform(train_merlin_ds)
val_merlin_ds = workflow.transform(val_merlin_ds)


def get_tf_dataset(ds: merlin.io.Dataset, shuffle: bool, args: argparse.Namespace):
    categorical_columns = ["user_id", "gmap_id", "category"]  # Single-hot
    # categorical_mh_columns = ["category"]  # Multi-hot
    categorical_mh_columns = []
    # numeric_columns = ["latitude", "longitude", "user_id_c_count", "gmap_id_c_count"]
    numeric_columns = ["latitude", "longitude"]

    return KerasSequenceLoader(
        ds, batch_size=args.batch_size, label_names=["rating_binary"],
        cat_names=categorical_columns + categorical_mh_columns, cont_names=numeric_columns, shuffle=shuffle,
        parts_per_chunk=args.parts_per_chunk, global_size=hvd.size(), global_rank=hvd.rank(), seed_fn=seed_fn, )


train_tf_ds = get_tf_dataset(train_merlin_ds, True, args)
val_tf_ds = get_tf_dataset(val_merlin_ds, False, args)

num_train_batches = len(train_tf_ds)
num_val_batches = len(val_tf_ds)
print(f"{num_train_batches=}")
print(f"{num_val_batches=}")

schema = train_tf_ds.output_schema
model = mm.DLRMModel(
    schema, embedding_dim=64, bottom_block=mm.MLPBlock([128, 64]), top_block=mm.MLPBlock([128, 64, 32]),
    prediction_tasks=mm.OutputBlock(schema), )
loss = tf.losses.BinaryCrossentropy()
opt = tf.keras.optimizers.Adam(5e-3 * hvd.size())
opt = hvd.DistributedOptimizer(opt)


@tf.function(experimental_relax_shapes=True)
def training_step(examples, labels, first_batch):
    with tf.GradientTape() as tape:
        probs = model(examples, training=True)
        loss_value = loss(labels, probs)
    # Horovod: add Horovod Distributed GradientTape.
    tape = hvd.DistributedGradientTape(tape, sparse_as_dense=True)
    grads = tape.gradient(loss_value, model.trainable_variables)
    opt.apply_gradients(zip(grads, model.trainable_variables))
    # Horovod: broadcast initial variable states from rank 0 to all other processes.
    # This is necessary to ensure consistent initialization of all workers when
    # training is started with random weights or restored from a checkpoint.
    #
    # Note: broadcast should be done after the first gradient step to ensure optimizer
    # initialization.
    if first_batch:
        hvd.broadcast_variables(model.variables, root_rank=0)
        hvd.broadcast_variables(opt.variables(), root_rank=0)
    return loss_value


@tf.function(experimental_relax_shapes=True)
def validation_step(examples, labels):
    probs = model(examples, training=False)
    loss_value = loss(labels, probs)
    return loss_value


def print_average_loss(loss_sum, batch_count, which):
    loss_tensor = tf.convert_to_tensor([loss_sum, batch_count], dtype=tf.float32)
    reduced_loss = hvd.allreduce(loss_tensor, name="total train loss", op=hvd.mpi_ops.Sum)
    if hvd.local_rank() == 0:
        print(f"{which} validation loss {(reduced_loss[0] / reduced_loss[1]).numpy()}")


# Horovod: adjust number of steps based on number of GPUs.
for epoch in range(args.epochs):
    loss_sum = 0.
    batch_count = 0
    with CodeTimer(f"train {epoch=}"):
        for batch, (examples, labels) in enumerate(train_tf_ds):
            loss_value = training_step(examples, labels, batch == 0)
            loss_sum += loss_value
            batch_count += 1
            if batch % (num_train_batches // 5) == 0 and hvd.local_rank() == 0:
                print("Step #%d\tLoss: %.6f" % (batch, loss_value))
    print_average_loss(loss_sum, batch_count, "train")

    loss_sum = 0.
    batch_count = 0
    with CodeTimer(f"val {epoch=}"):
        for examples, labels in val_tf_ds:
            loss_value = validation_step(examples, labels)
            loss_sum += loss_value
            batch_count += 1
    print_average_loss(loss_sum, batch_count, "validation")

hvd.join()
print(model.summary())
