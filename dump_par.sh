#!/usr/bin/bash

for sid in $(seq 54504887 100000 54751167); do
	while ((4 <= $(pgrep -f 'python.*dumpIdRange_xz' | wc -l) )); do
		sleep 30s;
	done
	echo $sid $((sid + 100000))
	time ~/dev/src/python-weaver/dumpIdRange_xz.py $sid $((sid + 100000)) &
	sleep 60s
done

wait

