#!/bin/bash

rm -R /mnt/workspace/dgx-4/shared/pwesolowski/gdsio.*
for X in 3 4 5 6
do
	for I in 1 0 2 3
	do
		for DEVICE in 0 1 2 3 4 5 6 7
		do
			for USE_NVLINK in true false
			do
				sbatch --dependency singleton --job-name gds-benchmark --export X=$X,I=$I,DEVICE=$DEVICE,USE_NVLINK=$USE_NVLINK start-benchmark.sh
			done
		done
	done
done
echo "Submitted"

