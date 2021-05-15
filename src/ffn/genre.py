from typing import TYPE_CHECKING
if TYPE_CHECKING:
	import psycopg2

class FFNGenre:
	def __init__(self, id_: int = None, name_: str = None) -> None:
		self.id = id_
		self.name = name_

	@staticmethod
	def lookup(db: 'psycopg2.connection', rid: int, name: str) -> 'FFNGenre':
		with db, db.cursor() as curs:
			curs.execute('''
				insert into FFNGenre(id, name) values(%s, %s)
				on conflict(id) do update set name = excluded.name
					where excluded.name is not null
						and octet_length(FFNGenre.name) < octet_length(excluded.name)
			''', (rid, name))
			curs.execute('select * from FFNGenre where id = %s', (rid,))
			row = curs.fetchone()
			if row is None:
				raise Exception(f"unable to lookup FFNGenre {rid} {name}")
			return FFNGenre(
					id_ = int(row[0]),
					name_ = str(row[1]),
				)

