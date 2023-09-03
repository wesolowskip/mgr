#!/bin/bash

set -xu

for i in {1..6}
do
  LIBCUDF_CUFILE_POLICY="OFF" python -u cudf_dask_benchmark.py

  for LIBCUDF_CUFILE_THREAD_COUNT in 64 32 16 8 4; do
    LIBCUDF_CUFILE_POLICY="GDS" LIBCUDF_CUFILE_SLICE_SIZE=1048576 LIBCUDF_CUFILE_THREAD_COUNT=${LIBCUDF_CUFILE_THREAD_COUNT} python -u cudf_dask_benchmark.py
  done
done
