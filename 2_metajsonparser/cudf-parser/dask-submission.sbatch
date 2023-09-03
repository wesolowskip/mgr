#!/bin/bash
#SBATCH --gpus 1
#SBATCH --mem 160G
#SBATCH --cpus-per-gpu 8
#SBATCH --time 18:0:0
#SBATCH --partition short


CONTAINER="${HOME}/containers/rapids-prod.sif"
CONTAINER_RC_FILE="${HOME}/containers/singularity_rc"
SCRIPT="python -u cudf_benchmark.py"

singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro "$CONTAINER" /bin/bash --rcfile "$CONTAINER_RC_FILE" -ci "$SCRIPT"
