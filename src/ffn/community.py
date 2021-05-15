from typing import TYPE_CHECKING, Any, Optional, List
if TYPE_CHECKING:
	import psycopg2

class FFNCommunity:
	def __init__(self, id_: int = None, stub_: str = None, name_: str = None
			) -> None:
		self.id = id_
		self.stub = stub_
		self.name = name_

	@staticmethod
	def maxId(db: 'psycopg2.connection') -> int:
		with db, db.cursor() as curs:
			curs.execute('''
				select max(id) from FFNCommunity
			''')
			r = curs.fetchone()
			return int(r[0]) if r is not None else -1

	@staticmethod
	def fromRow(row: Any) -> 'FFNCommunity':
		return FFNCommunity(
				id_ = int(row[0]),
				stub_ = str(row[1]),
				name_ = str(row[2]),
			)

	@staticmethod
	def get(db: 'psycopg2.connection', id_: int) -> Optional['FFNCommunity']:
		with db, db.cursor() as curs:
			curs.execute('select * from FFNCommunity where id = %s', (id_,))
			r = curs.fetchone()
			return FFNCommunity.fromRow(r) if r is not None else None

	@staticmethod
	def getBlockStripe(db: 'psycopg2.connection', start: int, end: int,
			stripeCount: int = 1, stripe: int = 0) -> List['FFNCommunity']:
		with db, db.cursor() as curs:
			curs.execute('''
				select * from FFNCommunity c
				where id >= %s and id < %s
					and id %% %s = %s
				and not exists (
					select 1 from FFNCommunityGraveyard g
					where g.id = c.id
				)
			''', (start, end, stripeCount, stripe))
			return [FFNCommunity.fromRow(r) for r in curs.fetchall()]

	def getUrl(self, page: int = 1) -> str:
		return 'https://www.fanfiction.net/community/' \
				+ f'{self.stub}/{self.id}/99/0/{page}/0/0/0/0/'

	@staticmethod
	def bury(db: 'psycopg2.connection', cid: int, code: int, updated: int = None,
			force: bool = False) -> int:
		if updated is None:
			import time
			updated = int(time.time()) * 1000

		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNCommunityGraveyard(id, code, updated) values(%s, %s, %s)
			on conflict(id)
				do update set code = excluded.code, updated = excluded.updated
			''' + \
				('where FFNCommunityGraveyard.updated <= excluded.updated' if not force else '') + \
			'''
			returning code
			''', (cid, code, updated))

			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def isDead(db: 'psycopg2.connection', cid: int) -> int:
		with db, db.cursor() as curs:
			curs.execute('select code from FFNCommunityGraveyard where id = %s', (cid,))
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

