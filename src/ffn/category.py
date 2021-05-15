from typing import TYPE_CHECKING, Any, Optional, List
if TYPE_CHECKING:
	import psycopg2

class FFNCategory:
	def __init__(self, id_: int = None, stub_: str = None, name_: str = None):
		self.id = id_
		self.stub = stub_
		self.name = name_

	@staticmethod
	def fromRow(row: Any) -> 'FFNCategory':
		return FFNCategory(
				id_ = int(row[0]),
				stub_ = str(row[1]),
				name_ = str(row[2]),
			)

	@staticmethod
	def lookup(db: 'psycopg2.connection', stub: str, name: str = None) -> 'FFNCategory':
		with db, db.cursor() as curs:
			curs.execute('''
				insert into FFNCategory(stub, name) values(%s, %s)
				on conflict(stub) do update set name = excluded.name
					where excluded.name is not null
						and octet_length(FFNCategory.name) < octet_length(excluded.name)
			''', (stub, name))
			curs.execute('select * from FFNCategory where stub = %s', (stub,))
			row = curs.fetchone()
			if row is None:
				raise Exception(f"unable to lookup FFNCategory {stub} {name}")
			return FFNCategory.fromRow(row)

	@staticmethod
	def get(db: 'psycopg2.connection', id_: int) -> 'FFNCategory':
		with db, db.cursor() as curs:
			curs.execute('select * from FFNCategory where id = %s', (id_,))
			return FFNCategory.fromRow(curs.fetchone())

	@staticmethod
	def getAll(db: 'psycopg2.connection') -> List['FFNCategory']:
		with db, db.cursor() as curs:
			curs.execute('select * from FFNCategory order by id asc')
			return [FFNCategory.fromRow(r) for r in curs.fetchall()]

	def getCrossoverUrl(self) -> str:
		return f"https://www.fanfiction.net/crossovers/{self.stub}/"

