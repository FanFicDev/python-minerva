from typing import TYPE_CHECKING, Any, Optional, List
if TYPE_CHECKING:
	import psycopg2

def extractFFNDeathCode(html: str) -> int:
	if html.find('<div id=profile_top') >= 0:
		return 0
	deletedCodes = [
			# probably deleted by user
			('Story Not FoundUnable to locate story. Code 1.', 1),
			# probably deleted by admin
			('Story Not FoundUnable to locate story. Code 2.', 2),
			# unknown
			('Story Not FoundStory is unavailable for reading. (A)', 3),
			# unknown
			('Story Not FoundStory is unavailable for reading. (B)', 4),
			# category disabled
			('Category for this story has been disabled.', 5),
			# no chapters
			('Story does not have any chapters.', 6),
		]
	# Chapter not found.

	from bs4 import BeautifulSoup # type: ignore
	soup = BeautifulSoup(html, 'html5lib')
	profile_top = soup.find(id='profile_top')
	if profile_top is not None:
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

class FFNFic:
	def __init__(self, id_: int = None, authorId_: int = None,
			fetched_: int = None, title_: str = None, ageRating_: str = None,
			chapterCount_: int = None, wordCount_: int = None,
			reviewCount_: int = None, favoriteCount_: int = None,
			followCount_: int = None, updated_: int = None, published_: int = None,
			status_: str = None, description_: str = None,
			fandomId1_: int = None, fandomId2_: int = None):
		self.id = id_
		self.authorId = authorId_
		self.fetched = fetched_
		self.title = title_
		self.ageRating = ageRating_
		self.chapterCount = chapterCount_
		self.wordCount = wordCount_
		self.reviewCount = reviewCount_
		self.favoriteCount = favoriteCount_
		self.followCount = followCount_
		self.updated = updated_
		self.published = published_
		self.status = status_
		self.description = description_
		self.fandomId1 = fandomId1_
		self.fandomId2 = fandomId2_

	@staticmethod
	def maxChapterCount(db: 'psycopg2.connection') -> int:
		with db, db.cursor() as curs:
			curs.execute('select max(chapterCount) from FFNFic')
			r = curs.fetchone()
			return -1 if r is None else int(r[0])

	@staticmethod
	def getFetched(db: 'psycopg2.connection', fid: int) -> int:
		with db, db.cursor() as curs:
			curs.execute('select fetched from FFNFic where id = %s', (fid,))
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def fromRow(row: Any) -> 'FFNFic':
		return FFNFic(
			id_ = int(row[0]),
			authorId_ = int(row[1]),
			fetched_ = int(row[2]),
			title_ = str(row[3]),
			ageRating_ = str(row[4]),
			chapterCount_ = int(row[5]),
			wordCount_ = int(row[6]),
			reviewCount_ = int(row[7]),
			favoriteCount_ = int(row[8]),
			followCount_ = int(row[9]),
			updated_ = int(row[10]),
			published_ = int(row[11]),
			status_ = str(row[12]),
			description_ = str(row[13]),
			fandomId1_ = int(row[14]) if row[14] is not None else None,
			fandomId2_ = int(row[15]) if row[15] is not None else None,
		)

	@staticmethod
	def lookup(db: 'psycopg2.connection', fid: int) -> Optional['FFNFic']:
		with db, db.cursor() as curs:
			curs.execute('select * from ffnfic where id = %s', (fid,))
			row = curs.fetchone()
			return FFNFic.fromRow(row) if row is not None else None

	def upsert(self, db: 'psycopg2.connection') -> bool:
		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNFic(
				id, authorId, fetched, title, ageRating, chapterCount, wordCount,
				reviewCount, favoriteCount, followCount, updated, published,
				status, description, fandomId1, fandomId2)
			values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			on conflict(id)
				do update set id = excluded.id, authorId = excluded.authorId,
					fetched = excluded.fetched, title = excluded.title,
					ageRating = excluded.ageRating, chapterCount = excluded.chapterCount,
					wordCount = excluded.wordCount, reviewCount = excluded.reviewCount,
					favoriteCount = excluded.favoriteCount,
					followCount = excluded.followCount,
					updated = excluded.updated, published = excluded.published,
					status = excluded.status, description = excluded.description,
					fandomId1 = excluded.fandomId1, fandomId2 = excluded.fandomId2
				where FFNFic.fetched <= excluded.fetched
			returning fetched
			''', (self.id, self.authorId, self.fetched, self.title, self.ageRating,
				self.chapterCount, self.wordCount, self.reviewCount, self.favoriteCount,
				self.followCount, self.updated, self.published, self.status,
				self.description, self.fandomId1, self.fandomId2,))
			r = curs.fetchone()
			z = False if r is None else int(r[0]) == self.fetched

			if self.description is not None:
				curs.execute('''
				update FFNFic
				set description = %s
				where id = %s and description is null
				''', (self.description, self.id))
			return z

	@staticmethod
	def isDead(db: 'psycopg2.connection', fid: int) -> int:
		with db, db.cursor() as curs:
			curs.execute('select code from FFNFicGraveyard where id = %s', (fid,))
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def bury(db: 'psycopg2.connection', fid: int, code: int,
			updated: int = None, force: bool = False) -> int:
		if updated is None:
			import time
			updated = int(time.time()) * 1000

		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNFicGraveyard(id, code, updated) values(%s, %s, %s)
			on conflict(id) 
				do update set code = excluded.code, updated = excluded.updated
			''' + \
				('where FFNFicGraveyard.updated <= excluded.updated' if not force else '') + \
			'''
			returning code
			''', (fid, code, updated))

			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def setFandoms(db: 'psycopg2.connection', fid: int,
			fandomId1: int, fandomId2: int = None) -> None:
		with db, db.cursor() as curs:
			curs.execute('''
			update FFNFic
				set fandomId1 = %s, fandomId2 = %s
				where id = %s
			''', (fandomId1, fandomId2, fid))

	@staticmethod
	def saveCrossoverInfo(db: 'psycopg2.connection', fid: int, stub: str,
			name: str, fandomId1: int, fandomId2: int) -> None:
		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNFicCrossoverDelayed(fid, stub, name, fandomId1, fandomId2)
			values(%s, %s, %s, %s, %s)
			''', (fid, stub, name, fandomId1, fandomId2))

	@staticmethod
	def getLiveFids(db: 'psycopg2.connection', start: int, end: int, cid: int
			) -> List[int]:
		with db, db.cursor() as curs:
			curs.execute('''
			select id
			from FFNFic f
			where f.id >= %s and f.id <= %s and f.chapterCount >= %s
				and not exists (
					select id from FFNFicGraveyard g where g.id = f.id and g.code != 0
				)
			''', (start, end, cid))

			return [int(r[0]) for r in curs]

	@staticmethod
	def getLiveFidsNeedingScraped(db: 'psycopg2.connection', start: int, end: int,
			cid: int, limit: int = None, stripeCount: int = None, stripe: int = None
			) -> List[int]:
		if stripeCount is None or stripe is None:
			stripeCount = 1
			stripe = 0
		if stripe < 0:
			raise Exception(f"stripe must be >= 0 not {stripe}")
		stripe = stripe % stripeCount

		if cid <= 100:
			with db, db.cursor() as curs:
				curs.execute('''
					create temporary table potweb (url url not null)''')
				curs.execute('''
					create index idx_potweb_web_url on potweb (url)''')
				curs.execute('''
					insert into potweb
					select distinct w.url from web w
					where w.url like 'https://www.fanfiction.net/s/%%/' || %s
						and w.status = 200;
					''', (cid,))
				curs.execute('''
					select id
					from FFNFic f
					where f.id >= %s and f.id <= %s
						and f.id %% %s = %s
						and f.chapterCount >= %s
						and not exists (
							select id from FFNFicGraveyard g where g.id = f.id and g.code != 0
						)
						and not exists (
							select 1 from potweb w
							where w.url = 'https://www.fanfiction.net/s/' || f.id || '/' || %s
						)
					order by random()
					limit %s
				''', (start, end, stripeCount, stripe, cid, cid,
					limit if limit is not None else 99999999))

				r = [int(r[0]) for r in curs]
				curs.execute('drop table potweb')
				return r

		with db, db.cursor() as curs:
			curs.execute('''
			select id
			from FFNFic f
			where f.id >= %s and f.id <= %s
				and f.id %% %s = %s
				and f.chapterCount >= %s
				and not exists (
					select id from FFNFicGraveyard g where g.id = f.id and g.code != 0
				)
				and not exists (
					select 1 from web w
					where w.url = 'https://www.fanfiction.net/s/' || f.id || '/' || %s
						and w.status = 200
				)
			order by id desc
			limit %s
			''', (start, end, stripeCount, stripe, cid, cid,
				limit if limit is not None else 99999999))

			return [int(r[0]) for r in curs]

