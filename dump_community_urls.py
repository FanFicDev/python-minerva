#!/usr/bin/env python
import sys
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import WebScraper
import weaver.enc as enc

def getLastPage(db: 'psycopg2.connection', scraper: WebScraper, url: str
		) -> int:
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		raise Exception(f"uhoh {w.url}")
	html = dec[1]
	soup = BeautifulSoup(html, 'html5lib')
	lcWrap = soup.find('div', { 'class': 'lc-wrapper' })
	if lcWrap is None:
		return 1
	maxSeen = 1
	stub = '/'.join([''] + url.split('/')[3:6] + [''])
	for a in lcWrap.findAll('a'):
		if a is None or a.getText() is None:
			continue
		href = a.get('href')
		if href is not None:
			if href.startswith(stub):
				maxSeen = max(maxSeen, int(href.split('/')[-2]))
		if a.getText().strip() != 'Last':
			continue
		ps = href.split('/')
		return int(ps[-2])
	return maxSeen
	#raise Exception(f"uhoh2 {w.url} {stub} {maxSeen}")

with oil.open() as db:
	scraper = WebScraper(db)
	scraper.baseDelay = 30

	for line in sys.stdin:
		url = line.strip()
		if not url.startswith('https://www.fanfiction.net/communities/'):
			continue
		if url.startswith('https://www.fanfiction.net/communities/general/'):
			continue
		cnt = getLastPage(db, scraper, url)
		ps = url.split('/')[:-2]
		for p in range(1, cnt + 1):
			print('/'.join(ps + [str(p), '']))

