#!/bin/bash

rm /mnt/workspace/dgx-4/shared/pwesolowski/gds_job_[0-7]/*
for NUM_GPUS in 1 2 4 8
do
	for X in 0 1 2
	do
		for RW in write read randread randwrite
		do
			for W in 2 4 8 16 32
			do
				for ENABLE_NVLINKS in 0 1
				do
					sbatch --gpus ${NUM_GPUS} --dependency singleton --job-name gds-benchmark --export X=$X,NUM_GPUS=${NUM_GPUS},RW=$RW,W=$W,ENABLE_NVLINKS=${ENABLE_NVLINKS} start-benchmark.sh
				done
			done
	
		done
	done
done
echo "Submitted"

