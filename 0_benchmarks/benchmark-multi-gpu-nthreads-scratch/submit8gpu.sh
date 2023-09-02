#!/bin/bash


for ENABLE_NVLINKS in 1
do
	for X in 0 1 2
	do
		for RW in write read randread randwrite
		do
			for W in 4 8 16 32
			do
				for NUM_GPUS in 8
				do
					if [ -d benchmark-${X}-8-${RW}-${W}-${ENABLE_NVLINKS}-* ] 2>/dev/null; then echo "Ignore" ; else  sbatch --gpus ${NUM_GPUS} --cpus-per-task 8 --dependency singleton --job-name gds-benchmark --export X=$X,NUM_GPUS=${NUM_GPUS},RW=$RW,W=$W,ENABLE_NVLINKS=${ENABLE_NVLINKS} start-benchmark.sh ; fi
					       #	sbatch --gpus ${NUM_GPUS} --cpus-per-task 8 --dependency singleton --job-name gds-benchmark --export X=$X,NUM_GPUS=${NUM_GPUS},RW=$RW,W=$W,ENABLE_NVLINKS=${ENABLE_NVLINKS} start-benchmark.sh ; fi
				done
			done
	
		done
	done
done
echo "Submitted"

