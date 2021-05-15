#!/usr/bin/bash

beg="${1-0}"

for s in {0..5}; do
	./reindex_story_content.py ${beg} 6 ${s} &
done

wait

