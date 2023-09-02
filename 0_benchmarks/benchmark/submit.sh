#!/bin/bash

for X in 0 1 2 3
do
	for I in 0 1 2 3
	do
		for DEVICE in 0 1 2 3 4 5 6 7
		do
			sbatch --export X=$X,I=$I,DEVICE=$DEVICE benchmark.sh
		done
	done
done
echo "Submitted"

