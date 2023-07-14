#!/bin/bash

export WORKFLOW_DIR="/scratch/shared/pwesolowski/mgr-pipeline/merlin/"
export DATA_DIR="/scratch/shared/pwesolowski/mgr-pipeline/joined-recommender"

srun -l --time 6:0:0 -C dgx --nodes 1 --ntasks-per-node 2 --cpus-per-gpu 1 --cpu-bind=none --mpi=pmix --mem 32G --gpus-per-task 1 singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "cd ~/praca-mgr/pipelines-repo/2_merlin && export PMIX_MCA_gds=^ds12 && ./hvd_wrapper.sh python -u run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize 512MiB  --force-host-read --data-path ${DATA_DIR} --parts-per-chunk 1 --batch-size 16384 --epochs 5"
