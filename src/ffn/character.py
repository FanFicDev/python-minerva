from typing import TYPE_CHECKING
if TYPE_CHECKING:
	import psycopg2

class FFNCharacter:
	def __init__(self, id_: int = None, name_: str = None, fandomId_: int = None
			) -> None:
		self.id = id_
		self.name = name_
		self.fandomId = fandomId_

	@staticmethod
	def lookup(db: 'psycopg2.connection', rid: int, name: str,
			fandomId: int = None) -> 'FFNCharacter':
		with db, db.cursor() as curs:
			curs.execute('''
				insert into FFNCharacter(id, name) values(%s, %s)
				on conflict(id) do update set name = excluded.name
					where excluded.name is not null
			''', (rid, name))

			if fandomId is not None:
				curs.execute('''
					update FFNCharacter
					set fandomId = %s
					where id = %s
				''', (fandomId, rid))

			curs.execute('''
				select * from FFNCharacter
				where id = %s
			''', (rid,))
			row = curs.fetchone()
			if row is None:
				raise Exception(f"unable to lookup FFNCharacter {rid} {name}")

			return FFNCharacter(
					id_ = int(row[0]),
					name_ = str(row[1]),
					fandomId_ = None if row[2] is None else int(row[2]),
				)

