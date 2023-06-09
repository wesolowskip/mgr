#!/bin/bash
#SBATCH -C dgx
#SBATCH --mem 60G
#SBATCH --time 1-0:0:0
#SBATCH --gpus 1

singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "LIBCUDF_CUFILE_THREAD_COUNT=64 python -u fit_workflow.py --workflow-dir /scratch/shared/pwesolowski/mgr-pipeline/merlin --blocksize 1GiB --data-dir /scratch/shared/pwesolowski/mgr-pipeline/joined-recommender"
