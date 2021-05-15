#!/usr/bin/bash

echo -e "file_name\ttype\trange_start\trange_end\tsize\tmd5" > master_manifest.tsv

find ./ -name 'data_*.tar.xz' | sort | while read -r dataf; do
	dataf="$(echo "$dataf" | sed 's|^./||')"
	rbeg="$(echo "$dataf" | sed -r 's/data_([0-9]*)_.*/\1/')"
	rend="$(echo "$dataf" | sed -r 's/data_[0-9]+_([0-9]*).*/\1/')"
	dsize="$(cat "$dataf" | wc -c)"
	dhash="$(cat "$dataf" | md5sum | cut -c1-32)"
	echo -e "${dataf}\td\t${rbeg}\t${rend}\t${dsize}\t${dhash}"
done >> master_manifest.tsv

find ./ -name 'manifest_*.tsv.xz' | sort | while read -r manf; do
	manf="$(echo "$manf" | sed 's|^./||')"
	rbeg="$(echo "$manf" | sed -r 's/manifest_([0-9]*)_.*/\1/')"
	rend="$(echo "$manf" | sed -r 's/manifest_[0-9]+_([0-9]*).*/\1/')"
	msize="$(cat "$manf" | wc -c)"
	mhash="$(cat "$manf" | md5sum | cut -c1-32)"
	echo -e "${manf}\tm\t${rbeg}\t${rend}\t${msize}\t${mhash}"
done >> master_manifest.tsv

