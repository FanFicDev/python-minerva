#!/usr/bin/env python
import sys
import traceback
from typing import Set, Dict, Optional, Any
from bs4 import BeautifulSoup # type: ignore
import urllib.parse
from oil import oil
from weaver import RemoteWebScraper, WebQueue
import weaver.enc as enc
from minerva import FFNLanguage, FFNCategory, FFNGenre, FFNFandom, FFNCharacter

db = oil.open()
scraper = RemoteWebScraper(db)
#scraper.baseDelay = 30
scraper.requestTimeout = 300
scraper.mustyThreshold = 60 * 60 * 24 * 30 * 1

def stripAfter(s: str, needle: str) -> str:
	idx = s.find(needle)
	if idx < 0:
		return s
	return s[:idx]

baseUrl = 'https://www.fanfiction.net'
baseCrossoverUrl = 'https://www.fanfiction.net/crossovers'

def getCategories(scraper: RemoteWebScraper) -> Set[str]:
	categoryBlacklist = ['support', 'cookies', 'privacy', 'tos',
			'betareaders', 'forums', 'communities', 'j', '',
			'u', 's', 'crossovers']
	categories: Set[str] = set()

	root = scraper.softScrape(baseUrl)
	assert(root.url is not None)

	dec = enc.decode(root.response, root.url)
	assert(dec is not None)
	html = dec[1]
	soup = BeautifulSoup(html, 'html5lib')
	#print(len(html))

	for a in soup.findAll('a'):
		href = urllib.parse.urljoin(baseUrl, a.get('href'))
		href = stripAfter(href, '#')
		href = stripAfter(href, '?')
		if not href.startswith(baseUrl):
			continue

		end = href[len(baseUrl):]
		if end.find('/') < 0:
			continue

		category = end.split('/')[1]
		if category in categoryBlacklist:
			continue

		ffnCategory = FFNCategory.lookup(db, category, a.getText().strip())
		#print(f"{category}: {ffnCategory.id} {ffnCategory.name}")

		categories |= { category }

		#print(category)
		#print(f"{a.get('href')} {href}")

	return categories

categories = getCategories(scraper)
#print(categories)

fandomNameMap: Dict[str, Optional[int]] = {}
fandomIdMap: Dict[int, str] = {}
fandomStubMap: Dict[str, str] = {}

for category in categories:
	url = f"{baseUrl}/{category}/"
	w = scraper.softScrape(url)
	assert(w.url is not None)

	dec = enc.decode(w.response, w.url)
	assert(dec is not None)
	html = dec[1]
	soup = BeautifulSoup(html, 'html5lib')
	for a in soup.findAll('a'):
		href = urllib.parse.urljoin(w.url, a.get('href'))
		href = stripAfter(href, '#')
		href = stripAfter(href, '?')
		if not href.startswith(url):
			continue
		if href == url:
			continue
		fandomName = stripAfter(href[len(url):], '/')
		fandomName = urllib.parse.unquote(fandomName)
		fandomName = f"{category}/{fandomName}"

		if fandomName in fandomNameMap:
			e = fandomNameMap[fandomName]
			if e is not None:
				raise Exception(f"conflicting fandom ids: {fandomName} {e}")
		fandomNameMap[fandomName] = None
		fandomStubMap[fandomName] = a.getText().strip()

	curl = f"{baseUrl}/crossovers/{category}/"
	cw = scraper.softScrape(curl)
	assert(cw.url is not None)

	dec = enc.decode(cw.response, cw.url)
	assert(dec is not None)
	html = dec[1]
	soup = BeautifulSoup(html, 'html5lib')
	for a in soup.findAll('a'):
		#print(a.get('href'))
		href = urllib.parse.urljoin(cw.url, a.get('href'))
		#print(href)
		href = stripAfter(href, '#')
		href = stripAfter(href, '?')
		if not href.startswith(baseCrossoverUrl + '/'):
			continue
		parts = href[len(baseCrossoverUrl):].split('/')
		if len(parts) == 3 and parts[1] in categories:
			continue # category base
		if len(parts) != 4:
			raise Exception(f"unknown crossover parts: {parts}")
		fandomName = urllib.parse.unquote(parts[1])
		fandomName = f"{category}/{fandomName}"
		fandomId = int(parts[2])

		if fandomName in fandomNameMap:
			en = fandomNameMap[fandomName]
			if en is not None and en != fandomId:
				raise Exception(f"conflicting fandom ids: {fandomName} {fandomId} {en}")
		fandomNameMap[fandomName] = fandomId
		fandomStubMap[fandomName] = a.getText().strip()

		if fandomId in fandomIdMap:
			ei = fandomIdMap[fandomId]
			if ei != fandomName:
				raise Exception(f"conflicting fandom names: {fandomId} {fandomName} {ei}")
		fandomIdMap[fandomId] = fandomName


def lookupAbbreviatedFandoms() -> None:
	global fandomStubMap
	ks = [k for k in dict.keys(fandomStubMap)]
	ks.sort()
	ks.reverse()
	cnt=0
	for k in ks:
		if not fandomStubMap[k].endswith('...'):
			continue
		#print(f"{k}: {fandomStubMap[k]}")
		purl = f"{baseUrl}/{k}"
		#print(purl)
		cnt+=1

		w = scraper.softScrape(purl)
		assert(w.url is not None)
		dec = enc.decode(w.response, w.url)
		assert(dec is not None)
		html = dec[1]
		soup = BeautifulSoup(html, 'html5lib')
		title = soup.find('title').getText().strip()
		sufs = [' | FanFiction', 'FanFiction Archive']
		hasSuf = True
		while hasSuf:
			hasSuf = False
			for suf in sufs:
				if title.endswith(suf):
					hasSuf = True
					title = title[:-len(suf)].strip()
					break
		#print(f"{k} => {title}")
		fandomStubMap[k] = title

	#print(cnt)

#print(fandomNameMap)
#print(len(fandomNameMap))


#lookupAbbreviatedFandoms()

def toUrl(s: str) -> str:
	s = s.replace(' ', '-')
	s = s.replace('.', '-')
	s = s.replace(',', '-')
	s = s.replace('/', '-')
	s = s.replace(':', '-')
	s = s.replace('+', '-')
	s = s.replace("'", '-')
	s = s.replace("・", '-')
	while s.find('--') >= 0:
		s = s.replace('--', '-')
	return s.strip('-')

#ks = [k for k in dict.keys(fandomStubMap)]
#ks.sort()
#ks.reverse()
#cnt=0
#for k in ks:
#	ksub = k[k.find('/')+1:]
#	if toUrl(fandomStubMap[k]) != ksub:
#		print(f"{fandomStubMap[k]} => {ksub} != {toUrl(fandomStubMap[k])}")

nm: Dict[str, Any] = {}
ks = [k for k in dict.keys(fandomStubMap)]
ks.sort()
for k in ks:
	nm[k] = { 'name': fandomStubMap[k] }
	if k in fandomNameMap and fandomNameMap[k] is not None:
		nm[k]['id'] = fandomNameMap[k]

#import json
#print(json.dumps(nm))
#sys.exit(0)

categoryMap = {}
for category in categories:
	ffnCategory = FFNCategory.lookup(db, category)
	categoryMap[category] = ffnCategory

print(categoryMap)

languageIdMap: Dict[int, FFNLanguage] = {}
genreIdMap: Dict[int, FFNGenre] = {}
characterIdMap: Dict[int, FFNCharacter] = {}

def extractLanguages(soup: Any, html: str, url: str) -> None:
	global languageIdMap
	try:
		ls = soup.find('select', { 'name': 'languageid' })
		for o in ls.findAll('option'):
			rid = int(o.get('value'))
			name = o.getText().strip()
			if rid == 0:
				continue
			if rid < 0:
				raise Exception(f"found negative language id: {rid}")

			ffnLanguage = FFNLanguage.lookup(db, rid, name)
			if rid not in languageIdMap:
				print(f"language {rid} {name}")
				languageIdMap[rid] = ffnLanguage
	except:
		print(f"{purl} failed to process languages")
		fn = url.replace('/', '_').replace(':', '_')
		with open(f"./tmp_language_{fn}.html", "w") as f:
			f.write(html)

def saveGenres(soup: Any) -> None:
	global genreIdMap
	for o in soup.findAll('option'):
		rid = int(o.get('value'))
		name = o.getText().strip()
		if rid == 0:
			continue
		if rid < 0:
			raise Exception(f"found negative genre id: {rid}")

		if rid not in genreIdMap:
			print(f"genre {rid} {name}")
			ffnGenre = FFNGenre.lookup(db, rid, name)
			genreIdMap[rid] = ffnGenre

def extractGenres(soup: Any, html: str, url: str) -> None:
	try:
		saveGenres(soup.find('select', { 'name': 'genreid1' }))
		saveGenres(soup.find('select', { 'name': 'genreid2' }))
		saveGenres(soup.find('select', { 'name': '_genreid1' }))
	except:
		print(f"{purl} failed to process genres")
		fn = url.replace('/', '_').replace(':', '_')
		with open(f"./tmp_genre_{fn}.html", "w") as f:
			f.write(html)
		traceback.print_exc()

def saveCharacters(soup: Any, ffnFandom: FFNFandom) -> None:
	if soup is None:
		return
	global characterIdMap
	for o in soup.findAll('option'):
		rid = int(o.get('value'))
		name = o.getText().strip()
		if rid == 0:
			continue
		if rid < 0:
			raise Exception(f"found negative character id: {rid}")

		if rid not in characterIdMap:
			print(f"character {rid} {name}")
			ffnCharacter = FFNCharacter.lookup(db, rid, name, ffnFandom.id)
			characterIdMap[rid] = ffnCharacter
		elif characterIdMap[rid].fandomId != ffnFandom.id:
			print(f"character fandom mismatch {characterIdMap[rid].fandomId} {ffnFandom.id}")

def extractCharacters(soup: Any, html: str, url: str, ffnFandom: FFNFandom
		) -> None:
	try:
		saveCharacters(soup.find('select', { 'name': 'characterid1' }), ffnFandom)
		saveCharacters(soup.find('select', { 'name': 'characterid2' }), ffnFandom)
		saveCharacters(soup.find('select', { 'name': 'characterid3' }), ffnFandom)
		saveCharacters(soup.find('select', { 'name': 'characterid4' }), ffnFandom)
		saveCharacters(soup.find('select', { 'name': '_characterid1' }), ffnFandom)
		saveCharacters(soup.find('select', { 'name': '_characterid2' }), ffnFandom)
	except:
		print(f"{purl} failed to process characters")
		fn = url.replace('/', '_').replace(':', '_')
		with open(f"./tmp_characters_{fn}.html", "w") as f:
			f.write(html)
		traceback.print_exc()

def processSearchPage(ts: int, url: str, html: str, ffnFandom: FFNFandom
		) -> None:
	soup = BeautifulSoup(html, 'html5lib')
	extractLanguages(soup, html, url)
	extractGenres(soup, html, url)
	extractCharacters(soup, html, url, ffnFandom)

ks = [k for k in dict.keys(fandomNameMap)]
ks.sort()
ks.reverse()

kt = 0
for k in ks:
	name = None # unknown
	remoteId = fandomNameMap[k]
	category = k.split('/')[0]
	stub = k[k.find('/')+1:]
	ffnCategory = categoryMap[category]
	print(f"{category} {ffnCategory.id} {stub} {remoteId}")
	assert(ffnCategory.id is not None)
	ffnFandom = FFNFandom.lookup(db, ffnCategory.id, stub, name, remoteId)

	purl = f"{baseUrl}/{ffnCategory.stub}/{ffnFandom.stub}"
	print(purl)
	try:
		scraper.softScrape(purl)
	except:
		pass

	kt += 1
	if kt > 10:
		break

print(f"len(fandomNameMap): {len(fandomNameMap)}")
print(f"len(fandomIdMap): {len(fandomIdMap)}")

kt = 0
print("extracting languages")
for k in ks:
	name = None # unknown
	remoteId = fandomNameMap[k]
	category = k.split('/')[0]
	stub = k[k.find('/')+1:]
	ffnCategory = categoryMap[category]
	assert(ffnCategory.id is not None)
	ffnFandom = FFNFandom.lookup(db, ffnCategory.id, stub, name, remoteId)

	purl = f"{baseUrl}/{ffnCategory.stub}/{ffnFandom.stub}"

	w = scraper.softScrape(purl)
	assert(w.url is not None and w.created is not None)
	dec = enc.decode(w.response, w.url)
	assert(dec is not None)
	html = dec[1]

	try:
		processSearchPage(w.created, w.url, html, ffnFandom)
	except:
		print(f"{purl} failed to process")

print(f"len(languageIdMap): {len(languageIdMap)}")
print(f"len(genreIdMap): {len(genreIdMap)}")
print(f"len(characterIdMap): {len(characterIdMap)}")

# TODO: these can be found on any "search" page

