#!/usr/bin/env python
import sys
import time
import random
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import RemoteWebScraper
import weaver.enc as enc
from minerva import FFNFandom, FFNCategory

def plog(msg: str, fname: str = "./sffnc.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def processCategory(db: 'psycopg2.connection', scraper: RemoteWebScraper,
		category: FFNCategory) -> None:
	assert(category.id is not None)
	url = category.getCrossoverUrl()
	print(url)
	w = scraper.softScrape(url)
	dec = enc.decode(w.response, url)
	if dec is None:
		plog("  {category.id} has unknown encoding")
		return
	html = dec[1]
	if len(html) < 1:
		plog(f"  {category.id} is freshly dead: 1")
		return

	baseUrl = 'https://www.fanfiction.net'
	soup = BeautifulSoup(html, 'html5lib')
	for a in soup.findAll('a'):
		if not a.has_attr('href'):
			continue
		href = str(a.get('href'))
		if not href.startswith('/crossovers/'):
			continue
		parts = href.split('/')
		if len(parts) != 5:
			continue

		stub = parts[2]
		fandomId = int(parts[3])
		name = str(a.text)

		if len(stub) > 254:
			continue # TODO oh god why
			# https://www.fanfiction.net/anime/Do-You-Love-Your-Mom-and-Her-Two-Hit-Multi-Target-Attacks%3F-%E9%80%9A%E5%B8%B8%E6%94%BB%E6%92%83%E3%81%8C%E5%85%A8%E4%BD%93%E6%94%BB%E6%92%83%E3%81%A7%E4%BA%8C%E5%9B%9E%E6%94%BB%E6%92%83%E3%81%AE%E3%81%8A%E6%AF%8D%E3%81%95%E3%82%93%E3%81%AF%E5%A5%BD%E3%81%8D%E3%81%A7%E3%81%99%E3%81%8B%EF%BC%9F/?&srt=1&r=10

		print(baseUrl + href)
		print(f"{fandomId} {stub} => {name}")

		ffnFandom = FFNFandom.lookup(db, category.id, stub, remoteId=fandomId)
		print(f"{ffnFandom.remoteId} {ffnFandom.stub} => {ffnFandom.name}")

		ffnFandom.markHasCrossovers(db)
		print(ffnFandom.getAllCrossoversUrl())

		#def lookup(categoryId, stub, name = None, remoteId = None):
		#if name.endswith('...'):
		#	break

with oil.open() as db:
	scraper = RemoteWebScraper(db)
	scraper.mustyThreshold = 60 * 60 * 24 * 30 * 1
	plog('==========')
	#plog(f"source: {scraper.source.__dict__}")

	#FFNFandom.resetHasCrossovers(db)

	categories = FFNCategory.getAll(db)
	for category in categories:
		processCategory(db, scraper, category)

