#!/bin/bash
#SBATCH --cpus-per-task-8
#SBATCH --mem 16G
#SBATCH --time 6:0:0
#SBATCH --gpus 1
#SBATCH -C dgx

WORKFLOW_DIR="/scratch/shared/pwesolowski/mgr-pipeline/merlin/"
DATA_DIR="/scratch/shared/pwesolowski/mgr-pipeline/joined-recommender"

singularity run --nv  -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "pip install linetimer && cd ~/praca-mgr/pipelines-repo/2_merlin && horovodrun -np 1 sh hvd_wrapper.sh python run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize 1GiB --force-host-read --data-path ${DATA_DIR} --parts-per-chunk 3 --batch-size 16384 --epochs 5"
