from typing import TYPE_CHECKING, List, Dict, Tuple, Any, Optional
if TYPE_CHECKING:
	import psycopg2
import re

# used to extract values from text given regex and types
class RegexMatcher:
	def __init__(self, text: str, patterns: Dict[str, Tuple[str, type]]) -> None:
		self.text = text
		self.patterns = patterns

	def matchAll(self, target: Any) -> None:
		for which in self.patterns:
			self.match(which, target)

	def match(self, which: str, target: Any) -> None:
		val = self.get(which)
		if val is None:
			return
		ttype = self.patterns[which][1]
		if ttype == int:
			int_val = int(val.replace(',', ''))
			target.__setattr__(which.rstrip('?'), int_val)
		elif ttype == str:
			target.__setattr__(which.rstrip('?'), val)
		elif ttype != str:
			raise Exception('unknown type: {}'.format(ttype.__name__))

	def get(self, which: str) -> Optional[str]:
		match = re.search(self.patterns[which][0], self.text)
		if match is not None:
			return match.group(1)

		if which.endswith('?'):
			return None
		else:
			raise Exception('error: cannot find {} ({}) in {}'.format(
				which, self.patterns[which], self.text))


import time
ficCache: Dict[int, 'Fic'] = {}

class Fic:
	def __init__(self) -> None:
		self.type = 1
		self.lid = -1
		self.fetched: Optional[int] = None
		self.title: Optional[str] = None
		self.ageRating: Optional[str] = None
		self.chapterCount: Optional[int] = None
		self.wordCount: Optional[int] = None
		self.reviews: Optional[int] = None
		self.favorites: Optional[int] = None
		self.follows: Optional[int] = None
		self.updated: Optional[int] = None
		self.published: Optional[int] = None
		self.description: Optional[str] = None
		self.fandomId1: Optional[int] = None
		self.fandomId2: Optional[int] = None
		self.author: Optional[str] = None
		self.authorId: Optional[int] = None
		self.writeStatus: Optional[Status] = None

	@staticmethod
	def new() -> 'Fic':
		return Fic()

	@staticmethod
	def select(localId: int) -> 'Fic':
		global ficCache
		if localId in ficCache:
			return ficCache[localId]
		fic = Fic.new()
		fic.type = 1
		fic.lid = localId
		#ficCache[localId] = fic
		return fic
		#return Fic.select(localId)



import oil.util as util
from minerva.status import Status
from minerva.ffn.user import FFNUser
from minerva.ffn.category import FFNCategory
from minerva.ffn.fandom import FFNFandom
from minerva.ffn.fic import FFNFic

class FFNParser:
	languages = ["Afrikaans", "Bahasa Indonesia", "Bahasa Melayu", "Català",
			"Dansk", "Deutsch", "Eesti", "English", "Español", "Esperanto",
			"Filipino", "Français", "Hrvatski jezik", "Italiano", "Język polski",
			"LINGUA LATINA", "Magyar", "Nederlands", "Norsk", "Português",
			"Română", "Shqip", "Slovenčina", "Suomi", "Svenska", "Tiếng Việt",
			"Türkçe", "Íslenska", "čeština", "Ελληνικά", "България", "Русский",
			"Українська", "српски", "עברית", "العربية", "فارسی", "देवनागरी", "हिंदी",
			"ภาษาไทย", "中文", "日本語", "한국어"]
	ratings = ['K', 'K+', 'T', 'M']
	genres = {"Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
			"Friendship", "General", "Horror", "Humor", "Hurt/Comfort", "Mystery",
			"Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual", "Supernatural",
			"Suspense", "Tragedy", "Western"}

	def __init__(self) -> None:
		self.ftype = 1
		self.baseUrl = 'https://www.fanfiction.net'

	def get(self, db: 'psycopg2.connection', localId: int, ts: int, soup: Any
			) -> Fic:
		fic = Fic.select(localId)
		return self.create(db, fic, ts, soup)

	def extractStoryAuthor(self, soup: Any) -> FFNUser:
		profile_top = soup.find(id='profile_top')
		if profile_top is None:
			raise Exception('unable to find author')
		for a in profile_top.find_all('a'):
			a_href = a.get('href')
			if a_href.startswith('/u/'):
				author = a.get_text()
				authorId = a_href.split('/')[2]
				return FFNUser(id_ = int(authorId), name_ = author)
		raise Exception('unable to find author')

	def create(self, db: 'psycopg2.connection', fic: Fic, ts: int, soup: Any
			) -> Fic:
		author = self.extractStoryAuthor(soup)
		fic.author = author.name
		fic.authorId = author.id

		fic = self.parseInfoInto(db, fic, ts, soup)
		return fic

	def extractZListLocalId(self, zl: Any) -> int:
		stitle = zl.find('a', { 'class': 'stitle' })
		if stitle is None or stitle.get('href') is None:
			raise Exception('unable to find stitle')
		stitle = stitle.get('href')
		if not stitle.startswith('/s/'):
			raise Exception('invalid stitle url')
		parts = stitle.split('/')
		if len(parts) != 5 or not parts[2].isnumeric():
			raise Exception('invalid stitle parts')
		ficId = int(parts[2])
		return ficId

	def extractZListAuthor(self, zl: Any) -> FFNUser:
		for a in zl.find_all('a'):
			a_href = a.get('href')
			if a_href.startswith('/u/'):
				author = a.get_text()
				authorId = a_href.split('/')[2]
				return FFNUser(id_ = int(authorId), name_ = author)
		raise Exception('unable to find author')

	def getFromZList(self, db: 'psycopg2.connection', localId: int, ts: int,
			zlSoup: Any, author: FFNUser) -> Fic:
		fic = Fic.select(localId)
		return self.createFromZList(db, fic, ts, zlSoup, author)

	def createFromZList(self, db: 'psycopg2.connection', fic: Fic, ts: int,
			zlSoup: Any, author: FFNUser) -> Fic:
		fic.author = author.name
		fic.authorId = author.id

		fic = self.parseZListInfoInto(db, fic, ts, zlSoup)
		return fic

	def handleFandom(self, db: 'psycopg2.connection', fic: Fic, cat: FFNCategory,
			stub: str, name: str) -> None:
		assert(cat.id is not None)
		fandom = FFNFandom.lookup(db, cat.id, stub, name)
		if fandom is None:
			raise Exception(f"unable to find fandom {stub}:{name} in {cat.stub}")
		fic.fandomId1 = fandom.id

	def handleCrossoverFandom(self, fic: Fic, fandom: str, fIds: List[int],
			href: str, text: str) -> None:
		pass

	def parseInfoInto(self, db: 'psycopg2.connection', fic: Fic, ts: int,
			soup: Any) -> Fic:
		FFNUser(id_=fic.authorId, name_=fic.author, fetched_=ts*1000).upsert(db)

		profile_top = soup.find(id='profile_top')
		if profile_top is None:
			raise Exception('unable to find author')

		text = profile_top.getText()
		pt_str = str(profile_top)

		fic.fetched = int(ts)

		# default optional fields
		fic.reviews = 0
		fic.favorites = 0
		fic.follows = 0

		titleFound = False
		for b in profile_top.find_all('b'):
			b_class = b.get('class')
			if len(b_class) == 1 and b_class[0] == 'xcontrast_txt':
				fic.title = b.getText().strip()
				titleFound = True
				break
		if titleFound == False:
			raise Exception('error: unable to find title:\n{}\n'.format(pt_str))

		descriptionFound = False
		for div in profile_top.find_all('div'):
			div_class = div.get('class')
			if div.get('style') == 'margin-top:2px' \
					and len(div_class) == 1 and div_class[0] == 'xcontrast_txt':
				fic.description = div.getText().strip()
				descriptionFound = True
				break
		if descriptionFound == False:
			raise Exception('error: unable to find description:\n{}\n'.format(pt_str))

		# category/fandom is in pre_story_links
		preStoryLinks = soup.find(id='pre_story_links')
		preStoryLinksLinks = [] if preStoryLinks is None else preStoryLinks.find_all('a')
		preStoryLinksLinks = []
		fcat = None # fic category
		for a in preStoryLinksLinks:
			text = a.getText().strip()
			href = a.get('href')
			hrefParts = href.split('/')

			# if it's a top level category
			if len(hrefParts) == 3 \
					and len(hrefParts[0]) == 0 and len(hrefParts[2]) == 0:
				cat = hrefParts[1]
				fcat = FFNCategory.lookup(cat, text)
				if fcat is None:
					raise Exception('unknown category: {}:{}'.format(cat, text))
				continue # skip categories

			# if it's a crossover /Fandom1_and_Fandm2_Crossovers/f1id/f2id/
			if len(hrefParts) == 5 and hrefParts[1].endswith("_Crossovers") \
					and len(hrefParts[0]) == 0 and len(hrefParts[4]) == 0:
				fIds = [int(hrefParts[2]), int(hrefParts[3])]
				self.handleCrossoverFandom(fic, hrefParts[1], fIds, href, text)
				continue

			# if it's a regular fandom in some category
			if len(hrefParts) == 4 \
					and len(hrefParts[0]) == 0 and len(hrefParts[3]) == 0:
				if fcat is None:
					raise Exception('unknown category: {}'.format(hrefParts[1]))

				self.handleFandom(db, fic, fcat, hrefParts[2], text)
				continue

			util.logMessage('unknown fandom {0}: {1}'.format(fic.lid, href))

		metaSpan = profile_top.find('span', { 'class': 'xgray' })
		if metaSpan is None:
			raise Exception('unable to find meta span')

		self.parseFicMetaSpan(metaSpan.decode_contents())

		text = metaSpan.getText()

		matcher = RegexMatcher(text, {
			'ageRating': ('Rated:\s+(?:Fiction)?\s*(K|K\+|T|M)\s', str),
			'chapterCount?': ('Chapters:\s+(\d+)', int),
			'wordCount': ('Words:\s+(\S+)', int),
			'reviews?': ('Reviews:\s+(\S+)', int),
			'favorites?': ('Favs:\s+(\S+)', int),
			'follows?': ('Follows:\s+(\S+)', int),
			'updated?': ('Updated:\s+(\S+)', str),
			'published': ('Published:\s+([^-]+)', str),
		})
		matcher.matchAll(fic)
		assert(fic.published is not None)

		if fic.published is not None:
			fic.published = util.parseDateAsUnix(fic.published, fic.fetched)

		if fic.updated is None:
			fic.updated = fic.published # default
		elif fic.updated is not None:
			fic.updated = util.parseDateAsUnix(fic.updated, fic.fetched)
		assert(fic.updated is not None)

		matcher = RegexMatcher(str(metaSpan), {
			'updated' + ('?' if text.find('Updated:') < 0 else ''): ("Updated: <span data-xutime=['\"](\d+)['\"]>", int),
			'published': ("Published: <span data-xutime=['\"](\d+)['\"]>", int),
		})
		matcher.matchAll(fic)

		if fic.chapterCount is None:
			fic.chapterCount = 1 # default

		match = re.search('(Rated|Chapters|Words|Updated|Published):.*Status:\s+(\S+)', text)
		if match is None:
			fic.writeStatus = Status.ongoing
		else:
			status = match.group(2)
			if status == 'Complete':
				fic.writeStatus = Status.complete
			else:
				raise Exception('unknown status: {}'.format(status))

		assert(fic.authorId is not None)
		ffnFic = FFNFic(fic.lid, fic.authorId, ts * 1000,
				fic.title, fic.ageRating, fic.chapterCount, fic.wordCount,
				fic.reviews, fic.favorites, fic.follows, fic.updated * 1000,
				fic.published * 1000, fic.writeStatus.name,
				fic.description, fic.fandomId1, fic.fandomId2)

		fb = ffnFic.upsert(db)
		return fic

	def parseFicMetaSpan(self, metaSpan: str) -> Dict[str, str]:
		res = self._parseFicMetaSpan(metaSpan)

		# reconstruct
		fields = [
				('rated', 'Rated: <>Fiction ZZZ</>'),
				('language', 'ZZZ'),
				('genres', 'ZZZ'),
				('characters', 'ZZZ'),
				('chapters', 'Chapters: ZZZ'),
				('words', 'Words: ZZZ'),
				('reviews', 'Reviews: <>ZZZ</>'),
				('favorites', 'Favs: ZZZ'),
				('follows', 'Follows: ZZZ'),
				('updated', 'Updated: <span data-xutime="ZZZ">TODO</span>'),
				('published', 'Published: <span data-xutime="ZZZ">TODO</span>'),
				('status', 'Status: ZZZ'),
				('id', 'id: ZZZ'),
			]
		rmeta = ' - '.join([
			f[1].replace('ZZZ', res[f[0]]) for f in fields if f[0] in res])

		# reparse
		res2 = self._parseFicMetaSpan(rmeta)

		# compare
		assert(res == res2)

		return res

	def _parseFicMetaSpan(self, metaSpan: str) -> Dict[str, str]:
		print(metaSpan)
		#   Rated: (ageRating)
		#   language
		#   optional genre(/genre)
		#   optional chars
		#   optional Chapters: (chapterCount)
		#   Words: (commaWords)
		#   optional Reviews: (commaReviews)
		#   optional Favs: (commaFavs)
		#   optional Follows: (commaFollows)
		#   optional Updated: (texty date)
		#   Published: (texty date)
		#   optional Status: Complete
		#   id: (fid)

		res: Dict[str, str] = {}

		text = metaSpan.strip()
		res = {}

		keys = [
				('rated', "Rated:\s+<[^>]*>Fiction\s*(K|K\+|T|M)<[^>]*>"),
			]

		for n, kre in keys:
			optional = n.endswith('?')
			n = n.rstrip('?')
			kre = f'^{kre}($| - )'
			#print(n, kre)

			match = re.search(kre, text)
			if match is not None:
				res[n] = match.group(1)
				text = text[len(match.group(0)):].strip()
			elif not optional:
				raise Exception(f'error: cannot find {n} in {text}')

		tend = text.find(' - ')
		language, text = text[:tend], text[tend + len(' - '):]
		res['language'] = language

		rkeys = [
				('id', "id:\s+(\d+)"),
				('status?', "Status:\s+(\S+)"),
				('published', "Published:\s+<span data-xutime=['\"](\d+)['\"]>(\S+)</span>"),
				('updated?', "Updated:\s+<span data-xutime=['\"](\d+)['\"]>(\S+)</span>"),
				('follows?', "Follows:\s+(\S+)"),
				('favorites?', "Favs:\s+(\S+)"),
				('reviews?', "Reviews:\s+<[^>]*>(\S+)<[^>]*>"),
				('words', "Words:\s+(\S+)"),
				('chapters?', "Chapters:\s+(\S+)"),
			]

		for n, kre in rkeys:
			optional = n.endswith('?')
			n = n.rstrip('?')
			kre = f'(^| - ){kre}$'
			#print(n, kre)

			match = re.search(kre, text)
			if match is not None:
				res[n] = match.group(2)
				text = text[:-len(match.group(0))].strip()
			elif not optional:
				raise Exception(f'error: cannot find {n} in {text}')

		if text.find(' - ') >= 0:
			tend = text.find(' - ')
			genres, chars = text[:tend], text[tend + len(' - '):]
			res['genres'] = genres.strip()
			res['characters'] = chars.strip()
			text = ''
		elif len(text) > 0 and text in FFNParser.genres:
			res['genres'] = text
			text = ''
		elif len(text) > 0:
			# we have either an option genre(/genre) OR an optional chars
			for g1 in FFNParser.genres:
				if len(text) < 1:
					break
				for g2 in FFNParser.genres:
					if text == f'{g1}/{g2}':
						res['genres'] = text
						text = ''
						break

		if len(text) > 0:
			res['characters'] = text

		return res

	def parseZListInfoInto(self, db: 'psycopg2.connection', fic: Fic, ts: int,
			zlSoup: Any) -> Fic:
		FFNUser(id_=fic.authorId, name_=fic.author, fetched_=ts*1000).upsert(db)
		text = zlSoup.find('div', {'class': 'xgray'}).getText()
		pt_str = str(zlSoup)

		fic.fetched = int(ts)

		# default optional fields
		fic.reviews = 0
		fic.favorites = 0
		fic.follows = 0

		titleFound = False
		for a in zlSoup.find_all('a', { 'class': 'stitle' }):
			fic.title = a.getText().strip()
			titleFound = True
			break
		if not titleFound:
			raise Exception('error: unable to find title:\n{}\n'.format(pt_str))

		# old fics may not have descriptions at all, but are they even required on
		# new fics? fics as recent as Published: May 20, 2005 (2402081) are
		# missing
		if fic.lid == 2126381: # TODO hmm?
			fic.description = ''
		else:
			descriptionFound = False
			for div in zlSoup.find_all('div', { 'class': 'z-padtop' }):
				if div.contents[0] is None or not isinstance(div.contents[0], str):
					continue
				fic.description = div.contents[0].strip()
				descriptionFound = True
				break
			if descriptionFound == False:
				pass # TODO hmm
				#raise Exception('error: unable to find description:\n{}\n'.format(pt_str))

		#data-category # fandom; will have & if crossover, text starts with Crossover
		#data-storyid # lid
		#data-title # title
		#data-wordcount # wordcount
		#data-datesubmit # published unix
		#data-dateupdate # updated unix
		#data-ratingtimes # reviews
		#data-chaptercount # chap count
		#data-statusid # 1 = incomplete, 2 = complete

		# rating: K, K+, T, M
		# language: FFNParser.languages

		#   optional Crossover
		# d category
		#   Rated: (ageRating)
		#   language
		#   genre
		# d optional Chapters: (chapterCount)
		# d Words: (commaWords)
		# d optional Reviews: (commaReviews)
		#   optional Follows: (follows)
		# d optional Update: (texty date)
		# d Published: (texty date)
		#   optional chars
		# d optional Complete

		matcher = RegexMatcher(text, {
			'ageRating': ('Rated:\s+(?:Fiction)?\s*(\S+)', str),
			'chapterCount?': ('Chapters:\s+(\d+)', int),
			'wordCount': ('Words:\s+(\S+)', int),
			'reviews?': ('Reviews:\s+(\S+)', int),
			'favorites?': ('Favs:\s+(\S+)', int),
			'follows?': ('Follows:\s+(\S+)', int),
			'updated?': ('Updated:\s+(\S+)', str),
			'published': ('Published:\s+([^-]+)', str),
		})
		matcher.matchAll(fic)
		assert(fic.published is not None)

		if fic.published is not None:
			fic.published = util.parseDateAsUnix(fic.published, fic.fetched)

		if fic.updated is None:
			fic.updated = fic.published # default
		elif fic.updated is not None:
			fic.updated = util.parseDateAsUnix(fic.updated, fic.fetched)
		assert(fic.updated is not None)

		if fic.chapterCount is None:
			fic.chapterCount = 1 # default

		if text.endswith(' - Complete'):
			fic.writeStatus = Status.complete
		else:
			fic.writeStatus = Status.ongoing

		zl = zlSoup.find('div', { 'class': 'z-list' })
		fan = None if zl is None else zl.get('data-category')
		if fan is not None:
			pass # self.handleFandom(fic, fan)
			# TODO: crossovers?

		assert(fic.authorId is not None)
		ffnFic = FFNFic(fic.lid, fic.authorId, ts * 1000,
				fic.title, fic.ageRating, fic.chapterCount, fic.wordCount,
				fic.reviews, fic.favorites, fic.follows, fic.updated * 1000,
				fic.published * 1000, fic.writeStatus.name,
				fic.description, fic.fandomId1, fic.fandomId2)

		fb = ffnFic.upsert(db)
		return fic

