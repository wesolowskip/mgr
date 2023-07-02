#!/bin/bash

set -x

MP_FORCE_HOST_READ="--mp-force-host-read"

# This script is intended to be run inside singularity container with GPUs already allocated
# It is assumend that 2 CPUs are allocated per single GPU
/build.sh
cd ~/praca-mgr/pipelines-repo/1_dataset_cuml/
for FILES in "Illinois.json" "California.json" "California.json Texas.json" "California.json Texas.json Florida.json" ""; do
  for PROTOCOL in tcp ucx; do
    for ENABLE_IB in "--enable-infiniband" ""; do
      for ENABLE_NVLINK in "--enable-nvlink" ""; do
        for RMM_POOL_SIZE in "" "--rmm-pool-size 0.7"; do
          for MP_BLOCKSIZE in "256MiB" "1GiB" "4GiB"; do
            for MP_PINNED_READ in "" "--mp-pinned-read"; do
              if [ $PROTOCOL = "ucx" ] || [ $ENABLE_NVLINK = "" ]; then
                python cuml_single_node.py --files $FILES --reps 5 --protocol $PROTOCOL $ENABLE_IB $ENABLE_NVLINK $RMM_POOL_SIZE --jit-unspill --mp-blocksize $MP_BLOCKSIZE $MP_FORCE_HOST_READ $MP_PINNED_READ
              fi
            done
          done
        done
      done
    done
  done
done
