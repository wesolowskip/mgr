#!/bin/bash
#SBATCH --partition cudatest 
#SBATCH --mem 10G 
#SBATCH --gpus 1
#SBATCH --output=slurm-benchmark-%j.out
#SBATCH --time 0:5:0

set -xu

INTERVAL=6
export CUFILE_ENV_PATH_JSON=/home2/faculty/pwesolowski/mgr/benchmark-scratch/cufile.json # export is crucial!
# export CUFILE_LOGGING_LEVEL=TRACE
# export CUFILE_LOGFILE_PATH=/home2/faculty/pwesolowski/mgr/gdsio-test.log

RESULTS_DIR="benchmark-$X-$I-$W-$SIZE-${SLURM_JOB_ID}"
mkdir -p "${RESULTS_DIR}"

/usr/local/cuda/gds/tools/gdsio -D /scratch/shared/pwesolowski -d 0 -w "$W" -s "$SIZE" -i 1M -x "$X" -I "$I" -T 60 &
PID=$!
sleep 1

# while true ; do for i in 0 1 2 3 4 5 6 7 8 9 10 11 ; do ./monitor_ib_traffic.sh "mlx5_${i}" &>> "${RESULTS_DIR}/ib_traffic_${i}.out" ; done ; sleep "$INTERVAL" ; done &
while true ; do /usr/local/cuda/gds/tools/gds_stats -p "${PID}" -l3 &>> "${RESULTS_DIR}/gds_stats.out" ; sleep "$INTERVAL" ; done &
dcgmi dmon -e 1009,1010 -d "${INTERVAL}000" &> "${RESULTS_DIR}/dcgmi_dmon.out" &
nvidia-smi dmon -d "$INTERVAL" -s putcm &> "${RESULTS_DIR}/nvidia-smi.out" &
iostat -cxzm "$INTERVAL" &> "${RESULTS_DIR}/iostat.out" &

wait ${PID}
kill $(jobs -p)

