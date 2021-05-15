#!/usr/bin/env python
import sys
import time
import random
import psycopg2
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import RemoteWebScraper
import weaver.enc as enc
from minerva import FFNFandom, FFNFandomDeltaResult

def plog(msg: str, fname: str = "./pffnf.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def getPageCount(db: 'psycopg2.connection', fandom: FFNFandom, soup: Any,
		crossover: bool) -> int:
	catFanStub = fandom.getCatFanStub(db) if not crossover \
			else fandom.getAllCrossoversStub()
	maxSeen = 1
	for a in soup.findAll('a'):
		if a is None or a.getText() is None:
			continue
		href = a.get('href')
		if href is None:
			continue
		if not href.startswith(catFanStub):
			continue
		ps = href.split('&')
		for part in ps:
			if not part.startswith('p='):
				continue
			z = part.split('=')
			if len(z) != 2 or not z[1].isnumeric():
				continue
			maxSeen = max(maxSeen, int(z[1]))
	return maxSeen

def getFicTimestamps(soup: Any) -> Dict[int, int]:
	ficTs = {}
	for zl in soup.findAll('div', { 'class': 'z-list' }):
		stitle = zl.find('a', { 'class': 'stitle' })
		if stitle is None or stitle.get('href') is None:
			continue
		stitle = stitle.get('href')
		if not stitle.startswith('/s/'):
			continue
		parts = stitle.split('/')
		if len(parts) != 5 or not parts[2].isnumeric():
			continue
		ficId = int(parts[2])
		ficTs[ficId] = 0

		ts = None
		for span in zl.findAll('span'):
			if not span.has_attr('data-xutime'):
				continue
			xutime = span.get('data-xutime')
			if not xutime.isnumeric():
				continue
			xutime = int(xutime)
			if ts is None:
				ts = xutime
			ts = max(ts, xutime)

		if ts is None:
			continue
		ficTs[ficId] = ts

	return ficTs

def getMaxFicTs(ficTs: Dict[int, int]) -> Optional[int]:
	maxTs = None
	for ficId in ficTs:
		if maxTs is None:
			maxTs = ficTs[ficId]
		maxTs = max(maxTs, ficTs[ficId])
	return maxTs

def getMinFicTs(ficTs: Dict[int, int]) -> Optional[int]:
	minTs = None
	for ficId in ficTs:
		if minTs is None:
			minTs = ficTs[ficId]
		minTs = min(minTs, ficTs[ficId])
	return minTs

def prescrapeFandom(db: 'psycopg2.connection', scraper: RemoteWebScraper,
		fandom: FFNFandom, scrollDate: int, recentThreshold: int,
		crossover: bool = False) -> None:
	# TODO fandom graveyard? look at community scraper
	assert(fandom.id is not None)

	plog(f"prescraping fandom {fandom.id} {fandom.stub}, crossover: {crossover}")
	lastCompleted = FFNFandomDeltaResult.lastCompleted(db,
			fandom.id, crossover=crossover)
	if lastCompleted is not None and lastCompleted > recentThreshold:
		plog(f"  completed recently: {lastCompleted} > {recentThreshold}")
		return

	deltaResult = FFNFandomDeltaResult.create(
			db, fandom.id, crossover=crossover)

	page = 1
	pages = 1
	fanMinTs = None
	fanMaxTs = None
	while page <= pages:
		if pages > 1:
			plog(f"  grabbing page {page}/{pages}")
		url = fandom.getUrl(db, page) if not crossover \
				else fandom.getAllCrossoversUrl(page)
		w = scraper.softScrape(url)
		dec = enc.decode(w.response, url)
		if dec is None:
			plog("  {fandom.id} has unknown encoding")
			return
		html = dec[1]
		if len(html) < 1:
			plog(f"  {fandom.id} is freshly dead: 1")
			#minerva.buryCommunity(comm.id, 1, w.created)
			return

		soup = BeautifulSoup(html, 'html5lib')

		pages = getPageCount(db, fandom, soup, crossover)
		page += 1

		ficTs = getFicTimestamps(soup)
		if len(ficTs) == 0:
			break

		minTs = getMinFicTs(ficTs)
		maxTs = getMaxFicTs(ficTs)

		if fanMinTs is None:
			fanMinTs = minTs
		if fanMaxTs is None:
			fanMaxTs = maxTs
		if minTs is not None:
			assert(fanMinTs is not None)
			fanMinTs = min(fanMinTs, minTs)
		if maxTs is not None:
			assert(fanMaxTs is not None)
			fanMaxTs = max(fanMaxTs, maxTs)

		deltaResult.update(db, page - 1, pages, fanMinTs, fanMaxTs)

		if maxTs is not None and maxTs <= scrollDate:
			break

	deltaResult.finish(db, page - 1, pages, fanMinTs, fanMaxTs)

def prescrapeFandomBlock(db: 'psycopg2.connection', scraper: RemoteWebScraper,
		start: int, end: int, scrollDate: int, recentThreshold: int,
		stripeCount: int, stripe: int) -> None:
	fandoms = FFNFandom.getBlockStripe(db, start, end, stripeCount, stripe)
	random.shuffle(fandoms)

	plog(f"prescraping block [{start}, {end})")
	for fandom in fandoms:
		prescrapeFandom(db, scraper, fandom, scrollDate, recentThreshold, crossover=False)
		if fandom.hasCrossovers:
			prescrapeFandom(db, scraper, fandom, scrollDate, recentThreshold, crossover=True)


stripeCount = None
stripe = None

if len(sys.argv) > 1:
	stripeCount = int(sys.argv[1])
if len(sys.argv) > 2:
	stripe = int(sys.argv[2])

if stripe is None or stripeCount is None:
	raise Exception("expected stripeCount stripe")

blockSize = 1000

stripe %= stripeCount
blockSize *= stripeCount

scrollDate = 1546318800 # 2019-01-01, ran 2019-12-08
scrollDate = 1575176400 # 2019-12-01, ran 2020-02-10
scrollDate = 1580533200 # 2020-02-01, ran 2020-04-12
scrollDate = 1585713600 # 2020-04-01, ran 2020-09-20
scrollDate = 1598932800 # 2020-09-01, ran 2021-02-07
scrollDate = 1612155600 # 2021-02-01, ran 2021-03-28
recentThreshold = (int(time.time()) - (60 * 60 * 24 * 7)) * 1000
plog(f"stripeCount: {stripeCount}")
plog(f"stripe: {stripe}")

with oil.open() as db:
	scraper = RemoteWebScraper(db)
	scraper.mustyThreshold = 60 * 60 * 24 * 7 * 1
	plog('==========')
	#plog(f"source: {scraper.source.__dict__}")

	minId = 1
	maxId = FFNFandom.maxId(db)

	plog(f"max fandom id: {maxId}")

	blockIdxs = [idx for idx in range(max(int(minId / blockSize) - 20, 0), int(maxId / blockSize) + 1)]
	random.shuffle(blockIdxs)

	plog(f"block size: {blockSize}")
	plog(f"total blocks: {len(blockIdxs)}")

	for idx in blockIdxs:
		prescrapeFandomBlock(db, scraper, idx * blockSize, (idx + 1) * blockSize,
				scrollDate, recentThreshold, stripeCount, stripe)

plog("prescraped all of our blocks")
while True:
	time.sleep(600)

