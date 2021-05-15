from typing import TYPE_CHECKING, Any, Optional, List
if TYPE_CHECKING:
	import psycopg2

class FFNFicGraveyard:
	def __init__(self, id_: int = None, code_: int = None,
			updated_: int = None):
		self.id = id_
		self.code = code_
		self.updated = updated_

	@staticmethod
	def fromRow(row: Any) -> 'FFNFicGraveyard':
		return FFNFicGraveyard(
			id_ = int(row[0]),
			code_ = int(row[1]),
			updated_ = int(row[2]),
		)

	@staticmethod
	def lookup(db: 'psycopg2.connection', fid: int
			) -> Optional['FFNFicGraveyard']:
		with db, db.cursor() as curs:
			curs.execute('select * from FFNFicGraveyard g where g.id = %s', (fid,))
			row = curs.fetchone()
			return FFNFicGraveyard.fromRow(row) if row is not None else None

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

	def exhume(self, db: 'psycopg2.connection') -> None:
		with db, db.cursor() as curs:
			curs.execute('delete from FFNFicGraveyard g where g.id = %s', (self.id,))

