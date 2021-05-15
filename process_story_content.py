#!/usr/bin/env python3
import sys
import math
import traceback
import psycopg2
from typing import Any, List
from bs4 import BeautifulSoup # type: ignore
from oil import oil
import oil.util as util
from weaver import Web
import weaver.enc as enc
from minerva import FFNFicContent, extractFFNDeathCode

processType = 'content'
storyUrlPrefix = 'https://www.fanfiction.net/s/'

logFileName = f'./process_story_{processType}.log'

def plog(msg: str) -> None:
	global logFileName
	print(msg)
	util.logMessage(msg, fname = logFileName, logDir = './')

def extractContent(html: str) -> str:
	if html.lower().find('chapter not found.') != -1 \
			and html.lower().find("id='storytext") < 0:
		raise Exception('unable to find chapter content')
	lines = html.replace('\r', '\n').replace('>', '>\n').split('\n')
	parts: List[str] = []
	inStory = False
	for line in lines:
		if line.find("id='storytext'") != -1 \
				or line.find('id="storytext"') != -1:
			inStory = True
		if inStory:
			if line.find("SELECT id=chap_select") != -1 \
					or line.lower().find('<script') != -1:
				inStory = False
				break
			parts += [line]
	while len(parts) > 0 and (parts[-1].startswith('&lt; Prev</button') \
			or parts[-1].startswith('<button class=btn TYPE=BUTTON')):
		parts = parts[:-1]
	return ' '.join(parts)

def handleStoryPage(db: 'psycopg2.connection', w: Web, stripeCount: int,
		stripe: int) -> None:
	assert(w.url is not None and w.created is not None and w.id is not None)
	global storyUrlPrefix
	if not w.url.startswith(storyUrlPrefix):
		return

	url = w.url
	ts = int(w.created / 1000)

	fid = int(url[len(storyUrlPrefix):].split('/')[0])
	cid = int(url[len(storyUrlPrefix):].split('/')[1])

	if fid % stripeCount != stripe:
		return

	dec = enc.decode(w.response, w.url)
	if dec is None:
		raise Exception("unknown encoding")
	html = dec[1]

	deathCode = extractFFNDeathCode(html)
	if deathCode != 0:
		#print(f"  {fid} is dead: {deathCode}")
		return

	#plog(f"{w.url} {len(w.response)}: {fid}/{cid}")

	try:
		# try to grab just the story content
		content = extractContent(html)
		FFNFicContent.upsert(db, fid, cid, w.id, content, stripe)
		#plog(f"{w.url} has content len: {len(content)}")
	except:
		plog(f"{w.url} is broken")
		with open(f"./edump_{fid}_{cid}.html", 'w') as f:
			f.write(html)
		plog(traceback.format_exc())
		raise

def handlePage(db: 'psycopg2.connection', w: Web, stripeCount: int,
		stripe: int) -> None:
	global storyUrlPrefix
	assert(w.url is not None)
	if w.url.startswith(storyUrlPrefix):
		handleStoryPage(db, w, stripeCount, stripe)
		return

def main(db: 'psycopg2.connection') -> None:
	if len(sys.argv) not in {1, 2, 4}:
		print(f"usage: {sys.argv[0]} [start [stripeCount stripe]]")
		sys.exit(1)
	
	if len(sys.argv) == 4:
		global logFileName
		logFileName = f"./process_story_{processType}_{sys.argv[2]}_{sys.argv[3]}.log"

	plog(f"using log {logFileName}")

	maxId = Web.maxId(db)
	plog(f"maxId: {maxId}")

	roundTo = 100
	overshoot = 20
	start = 0
	end = maxId
	end = int((end + roundTo -1) / roundTo) * roundTo

	stripeCount = 1
	stripe = 0

	if len(sys.argv) >= 2:
		start = int(sys.argv[1])
	if len(sys.argv) >= 4:
		stripeCount = int(sys.argv[2])
		stripe = int(sys.argv[3])

	plog(f"stripe: {stripe}")
	plog(f"stripeCount: {stripeCount}")

	plog(f"from {start} to {end}")
	blockSize = 1000 * stripeCount

	FFNFicContent.createStripeTable(db, stripe)

	fidx = start - blockSize
	while fidx < end:
		fidx += blockSize
		eidx = min(fidx + blockSize, end)
		plog(f"  doing ids [{fidx}, {eidx})")

		try:
			with db:
				for s in Web.fetchIdRange_g(db, fidx, eidx,
						ulike='https://www.fanfiction.net/s/%/%'):
					if s.response is None or len(s.response) < 1:
						continue
					handlePage(db, s, stripeCount, stripe)
		except SystemExit as e:
			raise
		except:
			plog(f"  trouble in ids [{fidx}, {eidx})")
			raise

if __name__ == '__main__':
	with oil.open() as db:
		main(db)
	sys.exit(0)

