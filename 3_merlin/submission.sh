#!/bin/bash
#SBATCH --time 10-0:0:0
#SBATCH --partition long
#SBATCH -C dgx
#SBATCH --gpus 1
#SBATCH --mem 40G
#SBATCH --cpus-per-gpu 8

set -xu

export WORKFLOW_DIR="/scratch/shared/pwesolowski/mgr-pipeline/merlin/"
export DATA_DIR="/scratch/shared/pwesolowski/mgr-pipeline/joined-recommender"

for BATCH_SIZE in 8192 16384 32768;  do
  for BLOCKSIZE in "512MiB" "1GiB" "2GiB"; do
    for PARTS_PER_CHUNK in  1 2 3; do
      singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "cd ~/praca-mgr/pipelines-repo/2_merlin && export PMIX_MCA_gds=^ds12 && ./hvd_wrapper.sh python -u run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize ${BLOCKSIZE} --data-path ${DATA_DIR} --parts-per-chunk ${PARTS_PER_CHUNK} --force-host-read --batch-size ${BATCH_SIZE} --epochs 5"
    done
  done
done

for BATCH_SIZE in 8192 16384 32768;  do
  for CUFILE_THREAD_COUNT in 4 8 16 32 64; do
    for BLOCKSIZE in "512MiB" "1GiB" "2GiB"; do
      for PARTS_PER_CHUNK in  1 2 3; do
        singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "cd ~/praca-mgr/pipelines-repo/2_merlin && export PMIX_MCA_gds=^ds12 && ./hvd_wrapper.sh python -u run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize ${BLOCKSIZE} --data-path ${DATA_DIR} --parts-per-chunk ${PARTS_PER_CHUNK} --cufile-thread-count ${CUFILE_THREAD_COUNT} --batch-size ${BATCH_SIZE} --epochs 5"
      done
    done
  done
done


#srun -l --time 6:0:0 -C dgx --nodes 1 --ntasks-per-node 2 --cpus-per-gpu 1 --cpu-bind=none --mpi=pmix --mem 32G --gpus-per-task 1 singularity run --nv -B /scratch/shared/pwesolowski,/run/udev:/run/udev:ro ~/containers/merlin-prod.sif /bin/bash --rcfile ~/containers/singularity_rc -ci "cd ~/praca-mgr/pipelines-repo/2_merlin && export PMIX_MCA_gds=^ds12 && ./hvd_wrapper.sh python -u run_merlin.py --workflow-dir ${WORKFLOW_DIR} --blocksize 512MiB  --force-host-read --data-path ${DATA_DIR} --parts-per-chunk 1 --batch-size 16384 --epochs 5"
