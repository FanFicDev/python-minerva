#!/usr/bin/env python
import sys
import time
import random
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import WebScraper
import weaver.enc as enc
from minerva import FFNCommunity

def plog(msg: str, fname: str = "./pffnc.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def getPageCount(comm: FFNCommunity, html: str) -> int:
	soup = BeautifulSoup(html, 'html5lib')
	maxSeen = 1
	for a in soup.findAll('a'):
		if a is None or a.getText() is None:
			continue
		href = a.get('href')
		if href is None:
			continue
		if not href.startswith('/community/'):
			continue
		ps = href.split('/')
		if len(ps) < 3:
			continue
		if int(ps[3]) != comm.id:
			continue
		if len(ps) != 12:
			continue
		maxSeen = max(maxSeen, int(ps[6]))
	return maxSeen

def prescrapeCommunity(db: 'psycopg2.connection', scraper: WebScraper,
		comm: FFNCommunity) -> None:
	assert(comm.id is not None)
	deathCode = FFNCommunity.isDead(db, comm.id)
	if deathCode != 0:
		plog(f"skipping community {comm.id} {comm.stub}, already dead: {deathCode}")
		return

	plog(f"prescraping community {comm.id} {comm.stub}")
	# grab the first page to get counts
	url = comm.getUrl()
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		plog("  {comm.id} has unknown encoding")
		return
	html = dec[1]
	if len(html) < 1:
		plog(f"  {comm.id} is freshly dead: 1")
		FFNCommunity.bury(db, comm.id, 1, w.created)

	pages = getPageCount(comm, html)
	if pages > 1:
		plog(f"  total pages: {pages}")
	for page in range(1, pages + 1):
		if pages > 1:
			plog(f"    grabbing page {page}/{pages}")
		scraper.softScrape(comm.getUrl(page))

def prescrapeCommunityBlock(db: 'psycopg2.connection', scraper: WebScraper,
		start: int, end: int, stripeCount: int, stripe: int) -> None:
	comms = FFNCommunity.getBlockStripe(db, start, end, stripeCount, stripe)
	random.shuffle(comms)

	plog(f"prescraping block [{start}, {end})")

	for comm in comms:
		prescrapeCommunity(db, scraper, comm)


blockSize = 1000
stripeCount = None
stripe = None

if len(sys.argv) > 1:
	stripeCount = int(sys.argv[1])
if len(sys.argv) > 2:
	stripe = int(sys.argv[2])

if stripe is None or stripeCount is None:
	raise Exception("expected stripeCount stripe")

stripe %= stripeCount
blockSize *= stripeCount

plog(f"stripeCount: {stripeCount}")
plog(f"stripe: {stripe}")

with oil.open() as db:
	scraper = WebScraper(db)
	plog('==========')
	plog(f"source: {scraper.source.__dict__}")

	minId = 1
	maxId = FFNCommunity.maxId(db)

	plog(f"max community id: {maxId}")

	blockIdxs = [idx for idx in range(max(int(minId / blockSize) - 20, 0), int(maxId / blockSize) + 1)]
	random.shuffle(blockIdxs)

	plog(f"block size: {blockSize}")
	plog(f"total blocks: {len(blockIdxs)}")
	for idx in blockIdxs:
		prescrapeCommunityBlock(db, scraper, idx * blockSize, (idx + 1) * blockSize,
				stripeCount, stripe)

plog("prescraped all of our blocks")
while True:
	time.sleep(600)

