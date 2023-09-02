#!/bin/bash
#SBATCH --partition cudatest 
#SBATCH --mem 10G 
#SBATCH --gpus 8
#SBATCH --output=slurm-benchmark-%j.out
#SBATCH --time 0:0:30

set -xu

echo $X
echo $I
echo $DEVICE
INTERVAL=3
export CUFILE_ENV_PATH_JSON=/home2/faculty/pwesolowski/mgr/cufile.json # export is crucial!
# export CUFILE_LOGGING_LEVEL=TRACE
# export CUFILE_LOGFILE_PATH=/home2/faculty/pwesolowski/mgr/gdsio-test.log

RESULTS_DIR="benchmark-$X-$I-$DEVICE-${SLURM_JOB_ID}"
mkdir -p "${RESULTS_DIR}"

/usr/local/cuda/gds/tools/gdsio -D /raid/shared/pwesolowski -d "$DEVICE" -w 8 -s 500M -i 1M -x "$X" -I "$I" -T 20 &
PID=$!
sleep 1

while true ; do /usr/local/cuda/gds/tools/gds_stats -p "${PID}" -l3 &>> "${RESULTS_DIR}/gds_stats.out" ; sleep "$INTERVAL" ; done &
dcgmi dmon -e 1009,1010 -d "${INTERVAL}000" &> "${RESULTS_DIR}/dcgmi_dmon.out" &
nvidia-smi dmon -d "$INTERVAL" -s putcm &> "${RESULTS_DIR}/nvidia-smi.out" &
iostat -cxzm "$INTERVAL" &> "${RESULTS_DIR}/iostat.out" &

wait ${PID}
kill $(jobs -p)

