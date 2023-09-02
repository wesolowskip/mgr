#!/bin/bash

rm /scratch/shared/pwesolowski/gds_job_[0-7]/*
for X in 0 1 2 3 4 5 6
do
	for RW in write read randread randwrite
	do
		for W in 16 32
		do
			for ENABLE_NVLINKS in 0 1
			do
				sbatch --dependency singleton --job-name gds-benchmark --export X=$X,RW=$RW,W=$W,ENABLE_NVLINKS=${ENABLE_NVLINKS} start-benchmark.sh
			done
		done
	done
done
echo "Submitted"

