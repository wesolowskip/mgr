#!/bin/bash
#SBATCH -C dgx
#SBATCH --mem 40G
#SBATCH --cpus-per-gpu 2
#SBATCH --time 3-0:0:0
#SBATCH --partition long

set -x

CONTAINER="${HOME}/containers/cuml-prod.sif"
CONTAINER_RC_FILE="${HOME}/containers/singularity_rc"
SCRIPT="${HOME}/praca-mgr/pipelines-repo/1_dataset_cuml/run_no_gds.sh"

MP_FORCE_HOST_READ="--mp-force-host-read"

for FILES in "California.json" ""; do
  for PROTOCOL in tcp ucx; do
    for ENABLE_IB in "--enable-infiniband" ""; do
      for ENABLE_NVLINK in "--enable-nvlink" ""; do
#        for RMM_POOL_SIZE in "" "--rmm-pool-size 0.7"; do
        for RMM_POOL_SIZE in ""; do
          for MP_BLOCKSIZE in "256MiB" "1GiB" "4GiB"; do
            for MP_PINNED_READ in "" "--mp-pinned-read"; do
              if [[ $PROTOCOL == ucx || ($ENABLE_IB == "" && $ENABLE_NVLINK == "") ]]; then
                FILES="$FILES" PROTOCOL="$PROTOCOL" ENABLE_IB="$ENABLE_IB" ENABLE_NVLINK="$ENABLE_NVLINK" RMM_POOL_SIZE="$RMM_POOL_SIZE" MP_BLOCKSIZE="$MP_BLOCKSIZE" MP_PINNED_READ="$MP_PINNED_READ" MP_FORCE_HOST_READ="$MP_FORCE_HOST_READ" singularity run --nv -B /scratch/shared/pwesolowski "$CONTAINER" /bin/bash --rcfile "$CONTAINER_RC_FILE" -ci "$SCRIPT"
                sleep 1
              fi
            done
          done
        done
      done
    done
  done
done
