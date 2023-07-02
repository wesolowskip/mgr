#!/bin/bash
#SBATCH -C dgx
#SBATCH --mem 32G
#SBATCH --cpus-per-gpu 2

CONTAINER="${HOME}/containers/cuml-prod.sif"
CONTAINER_RC_FILE="${HOME}/containers/singularity_rc"
SCRIPT="${HOME}/praca-mgr/pipelines-repo/1_dataset_cuml/run_no_gds.sh"

singularity run --nv -B /scratch/shared/pwesolowski "$CONTAINER" /bin/bash --rcfile "$CONTAINER_RC_FILE" -ci "$SCRIPT"
