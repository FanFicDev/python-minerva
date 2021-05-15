#!/usr/bin/env python
import os
import sys
import math
import gzip
import psycopg2
from typing import IO, cast
from bs4 import BeautifulSoup # type: ignore
from oil import oil
import oil.util as util
from weaver import Web
import weaver.enc as enc

urlPrefix = 'https://www.fanfiction.net/s/'
logFileName = './dmpt2fs.log'

def plog(msg: str) -> None:
	global logFileName
	print(msg)
	util.logMessage(msg, fname = logFileName, logDir = './')

def dumpRequest(w: Web, f: IO) -> None:
	assert(w.url is not None and w.created is not None)
	#plog(f"{w.url} {len(w.response)}")
	url = w.url
	ts = int(w.created / 1000)

	dec = enc.decode(w.response, w.url)
	if dec is None:
		raise Exception("unknown encoding")
	html = dec[1]

	# try to abbreviate down to just the meta info
	realStartIdx = html.find('id=pre_story_links')
	if realStartIdx > -1:
		realStartIdx = html.rfind('<div', 0, realStartIdx)
	startIdx = -2
	if realStartIdx > -1:
		startIdx = html.find('<div id=profile_top', realStartIdx)
	endIdx = -3
	if startIdx > -1:
		endIdx = html.find("class='lc-wrapper'", startIdx)
		if endIdx < 0:
			endIdx = html.find("id='storytextp'", startIdx)
		if endIdx > startIdx and startIdx > realStartIdx:
			html = html[realStartIdx:endIdx] + '>'

	soup = BeautifulSoup(html, 'html5lib')
	profile_top = soup.find(id='profile_top')
	if profile_top is None:
		return

	for t in ['script']:
		for e in soup.findAll(t):
			e.decompose()

	fid = url[len(urlPrefix):].split('/')[0]
	cid = url[len(urlPrefix):].split('/')[1]

	profile_top['id'] = f"profile_top_{fid}_{cid}"
	profile_top['data-fetched'] = ts
	profile_top_str = str(profile_top)


	f.write(f"<!-- start wid {w.id} -->\n".encode('utf-8'))
	#f.write(profile_top_str.encode('utf-8'))
	f.write(soup.find('body').encode_contents())
	f.write(f"<!-- {w.id} end wid -->\n".encode('utf-8'))

	return

	#print(profile_top_str)
	#sys.exit(0)

	#writeSingleFidProfileTop(fid, cid, profile_top_str)

def writeSingleFidProfileTop(baseDir: str, fid: str, cid: str, ts: int,
		profile_top_str: str) -> None:
	fidz = fid.zfill(9)
	spath = '/'.join([fidz[i * 3:i * 3 + 3] for i in range(3)] + [cid])
	#plog(f"{url} => {fid} => {fidz} => {spath}")
	fpath = baseDir + spath + f"/{ts}.html"
	#plog(fpath)
	os.makedirs(baseDir + spath, exist_ok=True)
	with open(fpath, 'wb') as f:
		f.write(profile_top_str.encode('utf-8'))

def main(db: 'psycopg2.connection') -> None:
	fileName = f"./meta.gz"
	if len(sys.argv) == 3:
		global logFileName
		logFileName = f"./dmpt2fs_{sys.argv[2]}.log"
		fileName = f"./meta_{sys.argv[2]}.gz"

	plog(f"using log {logFileName}")
	plog(f"writing to {fileName}")

	maxId = Web.maxId(db)
	plog(f"maxId: {maxId}")

	roundTo = 100
	overshoot = 20
	start = 0
	end = maxId
	end = int((end + roundTo -1) / roundTo) * roundTo

	if len(sys.argv) == 2:
		start = int(sys.argv[1])
	if len(sys.argv) == 3:
		partCount = int(sys.argv[1])
		partIdx = int(sys.argv[2])
		per = int(math.floor(end / partCount))
		start = per * partIdx - overshoot
		if partIdx == partCount - 1:
			end += overshoot
		else:
			end = per * partIdx + per + overshoot

	plog(f"from {start} to {end}")
	blockSize = 1000

	fidx = start - blockSize
	dumpedBlockCount = 0
	with gzip.open(fileName, "wb") as fgz:
		while fidx < end:
			fidx += blockSize
			eidx = min(fidx + blockSize, end)
			plog(f"  doing ids [{fidx}, {eidx})")

			some = Web.fetchIdRange(db, fidx, eidx, ulike='https://www.fanfiction.net/s/%/%')
			for s in some:
				if s.response is None or len(s.response) < 1:
					continue
				try:
					dumpRequest(s, cast(IO, fgz))
				except SystemExit as e:
					raise
				except:
					plog(f"{s.id}|problem with {s.id} {s.url}")
					with open(f"./{s.id}.html", "wb") as f:
						f.write(s.response)

			if len(some) > 0:
				dumpedBlockCount += 1

if __name__ == '__main__':
	with oil.open() as db:
		main(db)
	sys.exit(0)

