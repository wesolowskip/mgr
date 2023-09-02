#!/bin/bash

rm /scratch/shared/pwesolowski/gds_job_[0-7]/*
for ENABLE_NVLINKS in 1 0
do
	for X in 0 1 2
	do
		for RW in write read randread randwrite
		do
			for W in 4 8 16 32
			do
				for NUM_GPUS in 8 4 2 1
				do
					sbatch --gpus ${NUM_GPUS} --cpus-per-task 8 --dependency singleton --job-name gds-benchmark --export X=$X,NUM_GPUS=${NUM_GPUS},RW=$RW,W=$W,ENABLE_NVLINKS=${ENABLE_NVLINKS} start-benchmark.sh
				done
			done
	
		done
	done
done
echo "Submitted"

