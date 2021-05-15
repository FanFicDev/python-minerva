#!/usr/bin/env python
import sys
import time
import random
import psycopg2
from typing import List, Set
from oil import oil
from weaver import WebScraper, Web
import weaver.enc as enc
from minerva import FFNUser

def plog(msg: str, fname: str = "./pffnu.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def extractFFNUserDeathCode(html: str) -> int:
	if html.find('id=content_wrapper') >= 0:
		return 0
	deletedCodes = [
			# probably never created
			('User does not exist or is no longer an active member.', 0),
			# probably deleted
			('User is no longer an active member.', 1),
		]

	from bs4 import BeautifulSoup # type: ignore
	soup = BeautifulSoup(html, 'html5lib')
	content_wrapper = soup.find(id='content_wrapper')
	if content_wrapper is not None:
		return 0

	# story might've been deleted
	gui_warnings = soup.find_all('span', { 'class': 'gui_warning' })
	for gui_warning in gui_warnings:
		for dc in deletedCodes:
			if gui_warning.get_text() == dc[0]:
				return dc[1]

	# might be in the abbreviated page message box
	gui_normal = soup.find_all('span', { 'class': 'gui_normal' })
	for msg in gui_normal:
		for dc in deletedCodes:
			if msg.get_text().find(dc[0]) >= 0:
				return dc[1]

	return -1 # retry later

def getUrl(uid: int) -> str:
	return f"https://www.fanfiction.net/u/{uid}"

def prescrapeUid(db: 'psycopg2.connection', scraper: WebScraper, uid: int
		) -> None:
	plog(f"prescraping uid {uid}")
	url = getUrl(uid)
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		plog("  {uid} has unknown encoding")
		return
	html = dec[1]
	code = extractFFNUserDeathCode(html)
	if code != 0:
		plog(f"  {uid} is freshly dead: {code}")
		FFNUser.bury(db, uid, code, w.created)

def prescrapeUidBlock(db: 'psycopg2.connection', scraper: WebScraper,
		start: int, end: int, stripeCount: int, stripe: int,
		minId: int, maxId: int) -> None:
	uids = [uid for uid in range(start, end) if uid % stripeCount == stripe]
	urls = [getUrl(uid) for uid in uids]
	wcache = Web.wcache(db, urls)

	random.shuffle(uids)

	needsScraped = False
	for url in urls:
		if url not in wcache:
			needsScraped = True
			break
	if not needsScraped:
		plog(f"skipping block [{start}, {end})")
		return

	plog(f"prescraping block [{start}, {end})")

	for uid in uids:
		if uid < minId or uid > maxId:
			continue
		if getUrl(uid) in wcache:
			continue
		prescrapeUid(db, scraper, uid)

# 2019-08-27
minId = 1
maxId = 12677500 # roughly

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


blockIdxs = [idx for idx in range(max(int(minId / blockSize) - 20, 0), int(maxId / blockSize) + 1)]
random.shuffle(blockIdxs)

plog(f"block size: {blockSize}")
plog(f"total blocks: {len(blockIdxs)}")

with oil.open() as db:
	scraper = WebScraper(db)
	plog('==========')
	plog(f"source: {scraper.source.__dict__}")

	for idx in blockIdxs:
		prescrapeUidBlock(db, scraper, idx * blockSize, (idx + 1) * blockSize,
				stripeCount, stripe, minId, maxId)

plog("prescraped all of our blocks")
while True:
	time.sleep(600)

