#!/bin/bash
#SBATCH --cpus-per-task 8
#SBATCH --mem 32G
#SBATCH --time 6:0:0
#SBATCH --gpus 1
#SBATCH -C dgx

WORKFLOW_DIR="/scratch/shared/pwesolowski/mgr-pipeline/merlin/"
DATA_DIR="/scratch/shared/pwesolowski/mgr-pipeline/joined-recommender"

singularity run --nv  -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "cd ~/praca-mgr/pipelines-repo/2_merlin && horovodrun -np 1 sh hvd_wrapper.sh python run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize 1GiB --cufile-thread-count 64 --data-path ${DATA_DIR} --parts-per-chunk 2 --batch-size 16384 --epochs 5"
