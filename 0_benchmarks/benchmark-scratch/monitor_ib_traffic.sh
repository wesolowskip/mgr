#!/bin/bash

set -xu

date +%s.%N
cat /sys/class/infiniband/${1}/ports/1/counters/port_rcv_data
cat /sys/class/infiniband/${1}/ports/1/counters/port_xmit_data

