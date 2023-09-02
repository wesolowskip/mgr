#!/bin/bash

rm -R /mnt/workspace/dgx-4/shared/pwesolowski/gdsio.*
for X in 4 5 6
do
	for SIZE in 120M 500M 2G 8G 32G
	do
		for W in 4 8 16 32 64
		do
			for I in 1 0 2 3
			do
				sbatch --dependency singleton --job-name gds-benchmark --export X=$X,I=$I,W=$W,SIZE=$SIZE start-benchmark.sh
			done
		done
	done
done
echo "Submitted"

