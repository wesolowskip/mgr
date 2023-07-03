#!/bin/bash

set -xu

# This script is intended to be run inside singularity container with GPUs already allocated
# It is assumend that 2 CPUs are allocated per single GPU
#/build.sh

#cd ${METAJSONPARSER_PATH}/build
#cmake -DCMAKE_BUILD_TYPE=Release -DUSE_LIBCUDF=1 -DLOCAL_LIB=1 ..
#make -j meta-cudf-parser-1
#cd ${METAJSONPARSER_PATH}/python_binding
#make

cd ~/praca-mgr/pipelines-repo/1_dataset_cuml/
python -u cuml_single_node.py --files $FILES --reps 5 --protocol $PROTOCOL $ENABLE_IB $ENABLE_NVLINK $RMM_POOL_SIZE --jit-unspill --mp-blocksize $MP_BLOCKSIZE $MP_FORCE_HOST_READ $MP_PINNED_READ
