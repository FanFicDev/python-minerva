from typing import TYPE_CHECKING, Any, Optional, List
if TYPE_CHECKING:
	import psycopg2
from minerva.ffn.category import FFNCategory

class FFNFandom:
	def __init__(self, id_: int = None, categoryId_: int = None,
			stub_: str = None, name_: str = None, remoteId_: int = None,
			hasCrossovers_: int = None) -> None:
		self.id = id_
		self.categoryId = categoryId_
		self.stub = stub_
		self.name = name_
		self.remoteId = remoteId_
		self.hasCrossovers = hasCrossovers_

	@staticmethod
	def fromRow(row: Any) -> 'FFNFandom':
		return FFNFandom(
				id_ = int(row[0]),
				categoryId_ = int(row[1]),
				stub_ = str(row[2]),
				name_ = None if row[3] is None else str(row[3]),
				remoteId_ = None if row[4] is None else int(row[4]),
				hasCrossovers_ = None if row[5] is None else int(row[5]),
			)

	@staticmethod
	def resetHasCrossovers(db: 'psycopg2.connection') -> None:
		with db, db.cursor() as curs:
			curs.execute('update FFNFandom set hasCrossovers = 0')

	@staticmethod
	def maxId(db: 'psycopg2.connection') -> int:
		with db, db.cursor() as curs:
			curs.execute('''
				select max(ff.id) from FFNFandom ff
			''')
			r = curs.fetchone()
			return int(r[0]) if r is not None else -1

	@staticmethod
	def lookupRemoteId(db: 'psycopg2.connection', remoteId: int
			) -> Optional['FFNFandom']:
		with db, db.cursor() as curs:
			curs.execute('''
				select * from FFNFandom
				where remoteId = %s
			''', (remoteId,))
			row = curs.fetchone()
			return FFNFandom.fromRow(row) if row is not None else None

	@staticmethod
	def lookup(db: 'psycopg2.connection', categoryId: int, stub: str,
			name: str = None, remoteId: int = None) -> 'FFNFandom':
		with db, db.cursor() as curs:
			curs.execute('''
				insert into FFNFandom(categoryId, stub) values(%s, %s)
				on conflict(categoryId, stub) do nothing
			''', (categoryId, stub))

			if name is not None:
				curs.execute('''
					update FFNFandom
					set name = %s
					where categoryId = %s and stub = %s
				''', (name, categoryId, stub))

			if remoteId is not None:
				curs.execute('''
					update FFNFandom
					set remoteId = %s
					where categoryId = %s and stub = %s
				''', (remoteId, categoryId, stub))

			curs.execute('''
				select * from FFNFandom
				where categoryId = %s and stub = %s
			''', (categoryId, stub))
			row = curs.fetchone()
			if row is None:
				raise Exception(f"unable to lookup FFNFandom {categoryId} {stub}")
			return FFNFandom.fromRow(row)

	@staticmethod
	def getBlockStripe(db: 'psycopg2.connection', start: int, end: int,
			stripeCount: int = 1, stripe: int = 0) -> List['FFNFandom']:
		with db, db.cursor() as curs:
			# TODO do we need a fandom graveyard?
			curs.execute('''
				select * from FFNFandom ff
				where id >= %s and id < %s
					and id %% %s = %s
			''', (start, end, stripeCount, stripe))
			return [FFNFandom.fromRow(r) for r in curs.fetchall()]

	def markHasCrossovers(self, db: 'psycopg2.connection') -> None:
		with db, db.cursor() as curs:
			# TODO do we need a fandom graveyard?
			curs.execute('update FFNFandom set hasCrossovers = 1 where id = %s',
					(self.id,))

	def getUrl(self, db: 'psycopg2.connection', page: int = 1) -> str:
		if page < 1:
			raise Exception(f"unable to get FFNFandom url for page: {page}")
		assert(self.categoryId is not None)
		category = FFNCategory.get(db, self.categoryId)
		if category is None:
			raise Exception(f"unable to find FFNFandom category: {self.categoryId}")
		return f'https://www.fanfiction.net/{category.stub}/' \
				+ f'{self.stub}/?&srt=1&r=10' \
				+ (f'&p={page}' if page > 1 else '')

	def getCatFanStub(self, db: 'psycopg2.connection') -> str:
		assert(self.categoryId is not None)
		category = FFNCategory.get(db, self.categoryId)
		if category is None:
			raise Exception(f"unable to find FFNFandom category: {self.categoryId}")
		return f'/{category.stub}/{self.stub}/'

	def getAllCrossoversUrl(self, page: int = 1) -> str:
		if self.remoteId is None:
			raise Exception(f"unable to get all crossover url: {self.id}")
		return f'https://www.fanfiction.net/{self.stub}_Crossovers/' \
				+ f'{self.remoteId}/0/?&srt=1&r=10' \
				+ (f'&p={page}' if page > 1 else '')

	def getAllCrossoversStub(self) -> str:
		if self.remoteId is None:
			raise Exception(f"unable to get all crossover url: {self.id}")
		return f'/{self.stub}_Crossovers/{self.remoteId}/0/'

