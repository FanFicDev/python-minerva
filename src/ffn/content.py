from typing import TYPE_CHECKING, Any, Iterator
if TYPE_CHECKING:
	import psycopg2
from oil.util import compress, uncompress

class FFNFicContent:
	def __init__(self, fid_: int = None, cid_: int = None, wid_: int = None,
			content_: bytes = None):
		self.fid = fid_
		self.cid = cid_
		self.wid = wid_
		self.content = content_

	@staticmethod
	def fromRow(row: Any) -> 'FFNFicContent':
		return FFNFicContent(
				fid_ = row[0],
				cid_ = row[1],
				wid_ = row[2],
				content_ = None if row[3] is None else uncompress(row[3].tobytes()),
			)

	@staticmethod
	def fetch(db: 'psycopg2.connection', fid: int) -> Iterator['FFNFicContent']:
		with db, db.cursor() as curs:
			curs.execute('''
				select * from FFNFicContent ffc
				where ffc.fid = %s
				order by ffc.cid asc
			''', (fid,))
			for r in curs:
				yield FFNFicContent.fromRow(r)

	@staticmethod
	def fetchWidRange(db: 'psycopg2.connection', beg: int, end: int,
			stripeCount: int = 1, stripe: int = 0) -> Iterator['FFNFicContent']:
		with db, db.cursor() as curs:
			curs.execute('''
				select * from FFNFicContent ffc
				where (ffc.wid between %s and %s)
					and (ffc.wid %% %s = %s)
				order by ffc.wid asc
			''', (beg, end, stripeCount, stripe))
			for r in curs:
				yield FFNFicContent.fromRow(r)

	@staticmethod
	def maxWid(db: 'psycopg2.connection') -> int:
		with db, db.cursor() as curs:
			curs.execute('select max(wid) from FFNFicContent')
			r = curs.fetchone()
			return 0 if r is None else int(r[0])

	@staticmethod
	def createStripeTable(db: 'psycopg2.connection', stripe: int) -> None:
		with db, db.cursor() as curs:
			curs.execute(f'''
				create table if not exists FFNFicContent_{stripe} (
					fid bigint not null,
					cid int4 not null,
					wid bigint,
					content bytea,

					primary key(fid, cid)
				) tablespace ffn_archive;''')

	@staticmethod
	def upsert(db: 'psycopg2.connection', fid: int, cid: int, wid: int,
			content: str, stripe: int = None) -> 'FFNFicContent':
		table = 'FFNFicContent' if stripe is None else f'FFNFicContent_{stripe}'
		with db.cursor() as curs:
			curs.execute(f'''
				insert into {table}(fid, cid, wid, content) values(%s, %s, %s, %s)
				on conflict(fid, cid) do update
					set wid = excluded.wid, content = excluded.content
				returning *
			''', (fid, cid, wid, compress(content.encode('utf-8'))))
			r = curs.fetchone()
			if r is None:
				raise Exception(f"failed to insert?")
			return FFNFicContent.fromRow(r)

