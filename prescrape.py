#!/usr/bin/env python
import sys
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import WebScraper
import weaver.enc as enc

def plog(msg: str, fname: str = "./pffn.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def prescrape(scraper: WebScraper, url: str) -> None:
	print(f"url: {url}")
	w = scraper.softScrape(url)
	responseSize = len(w.response) if w.response is not None else 0
	print(f"\tresponse size: {responseSize}B")
	print(f"\trequest headers: {w.requestHeaders!r}")
	print(f"\tresponse headers: {w.responseHeaders!r}")

	dec = enc.decode(w.response, url)
	if dec is None:
		print("\tunknown encoding")
		return
	print(f"\tencoding: {dec[0]}")
	html = dec[1]
	soup = BeautifulSoup(html, 'html5lib')
	print(f"\tdecoded size: {len(html)}B")

def main(db: 'psycopg2.connection') -> int:
	scraper = WebScraper(db)
	plog('==========')
	plog(f"source: {scraper.source.__dict__}")

	if len(sys.argv) == 2:
		scraper.baseDelay = int(sys.argv[1])
	print(f"baseDelay: {scraper.baseDelay}")

	for line in sys.stdin:
		try:
			prescrape(scraper, line.strip())
		except SystemExit as e:
			raise
		except:
			pass
	return 0

if __name__ == '__main__':
	with oil.open() as db:
		res = main(db)
	sys.exit(res)

