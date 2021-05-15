#!/usr/bin/env python
import sys
import time
import random
import psycopg2
from typing import List, Set
from oil import oil
from weaver import RemoteWebScraper, Web
import weaver.enc as enc
from minerva import FFNFic, extractFFNDeathCode

def plog(msg: str, fname: str = "./pffn.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def getUrl(fid: int, cid: int = 1) -> str:
	return f"https://www.fanfiction.net/s/{fid}/{cid}"

def prescrapeFid(db: 'psycopg2.connection', scraper: RemoteWebScraper, fid: int,
		cid: int) -> None:
	plog(f"prescraping fid {fid} cid {cid}")
	code = FFNFic.isDead(db, fid)
	if code != 0:
		plog(f"  {fid} is dead: {code}")
		return
	url = getUrl(fid, cid)
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		plog("  {fid}/{cid} has unknown encoding")
		return
	html = dec[1]
	code = extractFFNDeathCode(html)
	if code != 0:
		plog(f"  {fid} is freshly dead: {code}")
		FFNFic.bury(db, fid, code)

def prescrapeFids(db: 'psycopg2.connection', scraper: RemoteWebScraper,
		fids: List[int], cid: int, maxId: int, wcache: Set[str] = set()) -> None:
	if len(fids) < 1:
		return

	plog(f"prescraping fids block #{len(fids)} cid:{cid}")
	random.shuffle(fids)

	for fid in fids:
		if fid > maxId:
			continue
		if getUrl(fid, cid) in wcache:
			continue
		prescrapeFid(db, scraper, fid, cid)

def prescrapeBlock(db: 'psycopg2.connection', scraper: RemoteWebScraper,
		start: int, end: int, cid: int, stripeCount: int, stripe: int, maxId: int
		) -> None:
	end = min(maxId, end)
	needsCachedCount = Web.countFFNNeedsCached(db, start, end, cid, stripeCount, stripe)
	if needsCachedCount == 0:
		return

	fids = [fid for fid in range(start, end) if fid % stripeCount == stripe]
	if cid != 1:
		fids = FFNFic.getLiveFids(db, start, end, cid)
		if len(fids) < 1:
			return
	random.shuffle(fids)

	urls = [getUrl(fid, cid) for fid in fids]
	wcache = Web.wcache(db, urls)

	needsScraped = False
	for url in urls:
		if url not in wcache:
			needsScraped = True
			break
	if not needsScraped:
		plog(f"skipping block [{start}, {end}) cid:{cid}")
		return

	plog(f"prescraping block [{start}, {end}) cid:{cid}")

	for fid in fids:
		if fid > maxId:
			continue
		if getUrl(fid, cid) in wcache:
			continue
		prescrapeFid(db, scraper, fid, cid)
		#try:
		#	prescrapeFid(fid)
		#except:
		#	print(f"  {fid} threw an exception")

oldMaxId = 13320106
maxId = 13334623

# 2019-08-23
oldMaxId = 13334623
maxId = 13370941

# 2019-12-08
oldMaxId = 13370941
maxId = 13448887

# 2020-02-11
oldMaxId = 13448887
maxId = 13498300

# 2020-04-12
oldMaxId = 13498300
maxId = 13550196

# 2020-09-20
oldMaxId = 13498300
maxId = 13701447

# 2021-02-08
oldMaxId = 13701447
maxId = 13814276

# 2021-02-13
oldMaxId = 13814276
maxId = 13817908

# 2021-03-29
oldMaxId = 13817908
maxId = 13850475
oldMaxId = 0

# in [oldMaxId, maxId] for chapter >= 2
# exapands range before oldMaxId in chapter 1

with oil.open() as db:
	scraper = RemoteWebScraper(db)
	plog('==========')
	#plog(f"source: {scraper.source.__dict__}")

	maxChapterCount = FFNFic.maxChapterCount(db)
	plog(f"maxChapterCount: {maxChapterCount}")

	blockSize = 5000

	startChapter = 2
	if len(sys.argv) > 1:
		startChapter = int(sys.argv[1])
	plog(f"startChapter: {startChapter}")

	method = 'stripe'
	methods = {'stripe', 'stripe1'}
	if len(sys.argv) > 2:
		method = sys.argv[2]
		if method not in methods:
			raise Exception(f"method must be in {methods} not {method}")

	plog(f"method: {method}")

	scrapeTail = False
	longTail = False

	stripeCount = None
	stripe = None

	if len(sys.argv) > 3:
		stripeCount = int(sys.argv[3])
	if len(sys.argv) > 4:
		stripe = int(sys.argv[4])
	assert(stripe is not None and stripeCount is not None)

	plog(f"stripeCount: {stripeCount}")
	plog(f"stripe: {stripe}")

	if method == 'stripe1':
		#startChapter = 1
		maxChapterCount = startChapter
	plog(f"doing chaps [{startChapter}, {maxChapterCount}]")

	for cid in range(startChapter, maxChapterCount + 1):
		plog(f"scraping cid {cid}")
		if cid <= 1:
			blockIdxs = [idx for idx in range(max(int(oldMaxId / blockSize) - 20, 0), int(maxId / blockSize) + 1)]
			random.shuffle(blockIdxs)

			plog(f"total blocks: {len(blockIdxs)}")
			for idx in blockIdxs:
				prescrapeBlock(db, scraper, idx * blockSize, (idx + 1) * blockSize, cid,
						stripeCount, stripe, maxId)
		else: #elif method == 'stripe':
			hugeBlockSize = 10000
			# TODO check live fid count (all poss, not need scraped), if < 0, break
			fids = FFNFic.getLiveFidsNeedingScraped(db, oldMaxId, maxId, cid,
					limit=hugeBlockSize, stripeCount=stripeCount, stripe=stripe)
			while len(fids) > 0:
				prescrapeFids(db, scraper, fids, cid, maxId)
				time.sleep(1)
				if len(fids) < hugeBlockSize*0.80:
					break
				fids = FFNFic.getLiveFidsNeedingScraped(db, oldMaxId, maxId, cid,
						limit=hugeBlockSize, stripeCount=stripeCount, stripe=stripe)

		#blockSize *= 1.5
		#blockSize = min(blockSize, 10000)

plog("prescraped all of our blocks")
while True:
	time.sleep(600)

