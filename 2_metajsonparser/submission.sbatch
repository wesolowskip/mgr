#!/bin/bash
#SBATCH --gpus 1
#SBATCH --mem 16G
#SBATCH --cpus-per-gpu 8
#SBATCH --time 1:0:0


CONTAINER="${HOME}/containers/rapids-prod.sif"
CONTAINER_RC_FILE="${HOME}/containers/singularity_rc"
SCRIPT="python -u benchmark.py"

singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro "$CONTAINER" /bin/bash --rcfile "$CONTAINER_RC_FILE" -ci "$SCRIPT"
