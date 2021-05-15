from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
	import psycopg2

class FFNUser:
	def __init__(self, id_: int = None, name_: str = None, fetched_: int = None
			) -> None:
		self.id = id_
		self.name = name_
		self.fetched = fetched_

	@staticmethod
	def fromRow(row: Any) -> 'FFNUser':
		return FFNUser(
				id_ = int(row[0]),
				name_ = str(row[1]),
				fetched_ = int(row[2]),
			)

	@staticmethod
	def lookup(db: 'psycopg2.connection', fid: int) -> Optional['FFNUser']:
		with db, db.cursor() as curs:
			curs.execute('select * from ffnuser where id = %s', (fid,))
			row = curs.fetchone()
			return FFNUser.fromRow(row) if row is not None else None

	def ficCount(self, db: 'psycopg2.connection') -> int:
		with db, db.cursor() as curs:
			curs.execute('select count(1) from ffnfic where authorId = %s', (self.id,))
			row = curs.fetchone()
			return int(row[0]) if row is not None else 0

	@staticmethod
	def getFetched(db: 'psycopg2.connection', uid: int) -> int:
		with db, db.cursor() as curs:
			curs.execute('select fetched from FFNUser where id = %s', (uid,))
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	def upsert(self, db: 'psycopg2.connection') -> bool:
		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNUser(id, name, fetched) values(%s, %s, %s)
			on conflict(id) 
				do update set name = excluded.name, fetched = excluded.fetched
				where FFNUser.fetched < excluded.fetched
			returning fetched
			''', (self.id, self.name, self.fetched))
			r = curs.fetchone()
			return False if r is None else int(r[0]) == self.fetched

	@staticmethod
	def isDead(db: 'psycopg2.connection', uid: int) -> int:
		with db, db.cursor() as curs:
			curs.execute('select code from FFNUserGraveyard where id = %s', (uid,))
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def bury(db: 'psycopg2.connection', uid: int, code: int, updated: int = None,
			force: bool = False) -> int:
		if updated is None:
			import time
			updated = int(time.time()) * 1000

		with db, db.cursor() as curs:
			curs.execute('''
			insert into FFNUserGraveyard(id, code, updated) values(%s, %s, %s)
			on conflict(id)
				do update set code = excluded.code, updated = excluded.updated
			''' + \
				('where FFNUserGraveyard.updated <= excluded.updated' if not force else '') + \
			'''
			returning code
			''', (uid, code, updated))

			r = curs.fetchone()
			return 0 if r is None else int(r[0])

