#!/usr/bin/env python
import sys
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import Web, WebBase, RemoteWebScraper
import weaver.enc as enc
from minerva import FFNParser, FFNFic, FFNFicGraveyard, extractFFNDeathCode

def plog(msg: str, fname: str = "./quincy.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def getUrl(fid: int, cid: int = 1) -> str:
	return f"https://www.fanfiction.net/s/{fid}/{cid}"

def scrapeFid(db: 'psycopg2.connection', scraper: RemoteWebScraper, fid: int,
		cid: int) -> int:
	code = FFNFic.isDead(db, fid)
	if code > 0:
		plog(f"  {fid} is dead: {code}")
		return code
	plog(f"  scraping fid {fid} cid {cid}")
	url = getUrl(fid, cid)
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		plog("    {fid}/{cid} has unknown encoding")
		return -1
	html = dec[1]
	code = extractFFNDeathCode(html)
	if code > 0:
		plog(f"    {fid} is freshly dead: {code}")
		FFNFic.bury(db, fid, code)
	elif code < 0:
		plog(f"    {fid} may be freshly dead: {code}")
	return code

def scrapeFidR(db: 'psycopg2.connection', scraper: RemoteWebScraper, fid: int,
		cid: int, tries: int = 1) -> int:
	while tries >= 0:
		r = scrapeFid(db, scraper, fid, cid)
		if r >= 0:
			return r

		if tries == 0:
			return r
		tries -= 1

		plog(f"  rescraping fid {fid} cid {cid}")
		url = getUrl(fid, cid)
		w = scraper.scrape(url)

	return -1

def refreshMeta(db: 'psycopg2.connection', scraper: RemoteWebScraper, fid: int
		) -> int:
	plog(f"  refreshing fid {fid} meta")

	fic = FFNFic.lookup(db, fid)
	if fic is not None and fic.chapterCount is not None:
		plog(f"    old chapterCount: {fic.chapterCount}")

	url = getUrl(fid, 1)
	w = scraper.scrape(url)

	assert(w.url is not None and w.created is not None)

	response = w.response
	if response is None and w.wbaseId is not None:
		wbase = WebBase.lookup(db, w.wbaseId)
		if wbase is None:
			raise Exception("has null web_base")
		response = wbase.response

	if response is None or len(response) < 1:
		raise Exception(f'refreshMeta: unable to find response for {fid}')

	dec = enc.decode(response, w.url)
	if dec is None:
		raise Exception("unknown encoding")
	html = dec[1]

	code = extractFFNDeathCode(html)
	if code != 0:
		plog(f"  dead: {code}")
		c = FFNFic.bury(db, fid, code, w.created, True)
		return code

	try:
		ffnParser = FFNParser()
		ts = int(w.created / 1000)
		pfic = ffnParser.get(db, fid, ts, BeautifulSoup(html, 'html5lib'))
	except:
		raise

	return 0

def main(db: 'psycopg2.connection') -> None:
	if len(sys.argv) != 2:
		raise Exception("expected fid")

	fid = int(sys.argv[1])
	plog(f"quincy: investigating {fid}")

	tomb = FFNFicGraveyard.lookup(db, fid)
	if tomb is None or tomb.code == 0:
		plog(f"  {fid} healthy?")
		return

	assert(tomb.code is not None)
	if tomb.code > 0:
		plog(f"  dead: {tomb.code}")
		return

	scraper = RemoteWebScraper(db)
	r = refreshMeta(db, scraper, fid)
	if r > 0:
		plog(f"  dead: {r}")
		return

	scid = 1
	ecid = 1

	fic = FFNFic.lookup(db, fid)
	if fic is not None and fic.chapterCount is not None:
		ecid = fic.chapterCount

	plog(f"  from {scid} to {ecid}")
	resurrected = True

	for cid in range(scid, ecid + 1):
		tries = 1 if cid != 1 else 0
		r = scrapeFidR(db, scraper, fid, cid, tries)

		if r != 0:
			resurrected = False
			break
	
	if resurrected:
		plog(f"  {fid} resurrected")
		tomb.exhume(db)

	return


if __name__ == '__main__':
	with oil.open() as db:
		main(db)
	sys.exit(0)

