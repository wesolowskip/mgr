#!/bin/bash
#SBATCH --partition cudatest 
#SBATCH --mem 10G 
#SBATCH --gpus 1
#SBATCH --output=slurm-benchmark-%j.out
#SBATCH --time 0:3:0

set -xu

INTERVAL=5
export CUFILE_ENV_PATH_JSON=/home2/faculty/pwesolowski/mgr/benchmark-many-gpus-scratch-one-gpu/cufile.json # export is crucial!
# export CUFILE_LOGGING_LEVEL=TRACE
# export CUFILE_LOGFILE_PATH=/home2/faculty/pwesolowski/mgr/gdsio-test.log

RESULTS_DIR="benchmark-$X-$RW-$W-${ENABLE_NVLINKS}-${SLURM_JOB_ID}"
mkdir -p "${RESULTS_DIR}"
envsubst <job_config.template >${RESULTS_DIR}/job_config.gdsio


/usr/local/cuda/gds/tools/gdsio ${RESULTS_DIR}/job_config.gdsio &
PID=$!
sleep 1

while true ; do /usr/local/cuda/gds/tools/gds_stats -p "${PID}" -l3 &>> "${RESULTS_DIR}/gds_stats.out" ; sleep "$INTERVAL" ; done &
dcgmi dmon -e 1009,1010 -d "${INTERVAL}000" &> "${RESULTS_DIR}/dcgmi_dmon.out" &
nvidia-smi dmon -d "$INTERVAL" -s putcm &> "${RESULTS_DIR}/nvidia-smi.out" &
iostat -cxzm "$INTERVAL" &> "${RESULTS_DIR}/iostat.out" &

wait ${PID}
kill $(jobs -p)

