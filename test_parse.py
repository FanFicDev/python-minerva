#!/usr/bin/env python3
# just try to parse all ffn meta and see what breaks
import sys
from bs4 import BeautifulSoup # type: ignore
import minerva
from minerva import extractFFNDeathCode, FFNFic
from weaver import Web, RemoteWebScraper
import weaver.enc as enc
from oil import oil
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	import psycopg2

def plog(msg: str, fname: str = "./test_parse.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def testLid(db: 'psycopg2.connection', lid: int) -> None:
	url = f'https://www.fanfiction.net/s/{lid}/1'
	scraper = RemoteWebScraper(db)
	w = scraper.softScrape(url)
	assert(w.created is not None)

	dec = enc.decode(w.response, url)
	if dec is None:
		plog("  {url} has unknown encoding")
		sys.exit(1)
	html = dec[1]
	code = extractFFNDeathCode(html)
	if code != 0:
		plog(f"  {url} is freshly dead: {code}")
		return

	soup = BeautifulSoup(html, 'html5lib')
	parser = minerva.ffn.parser.FFNParser()
	fic = parser.get(db, lid, w.created // 1000, soup)
	print(fic.__dict__)

qlids = [11575324, 13865144]
with oil.open() as db:
	for lid in qlids:
		testLid(db, lid)

	start = 0
	start = 286387
	start = 5939060
	end = 15000000
	while start < end:
		ei = start + 10000
		for fid in FFNFic.getLiveFids(db, start, ei, 1):
			print(fid)
			testLid(db, fid)
		start = ei

