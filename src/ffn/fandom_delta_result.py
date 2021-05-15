from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
	import psycopg2
import time

class FFNFandomDeltaResult:
	def __init__(self, id_: int = None, fandomId_: int = None,
			crossover_: int = None, created_: int = None, updated_: int = None,
			completed_: int = None, pages_: int = None, totalPages_: int = None,
			minTimestamp_: int = None, maxTimestamp_: int = None) -> None:
		self.id = id_
		self.fandomId = fandomId_
		self.crossover = crossover_
		self.created = created_
		self.updated = updated_
		self.completed = completed_
		self.pages = pages_
		self.totalPages = totalPages_
		self.minTimestamp = minTimestamp_
		self.maxTimestamp = maxTimestamp_

	@staticmethod
	def lastCompleted(db: 'psycopg2.connection', fandomId: int,
			crossover: bool = False) -> Optional[int]:
		with db, db.cursor() as curs:
			curs.execute('''
				select completed from FFNFandomDeltaResult
				where fandomId = %s and crossover = %s
					and completed is not null
				order by completed desc
				''', (fandomId, (1 if crossover else 0)))
			row = curs.fetchone()
			return int(row[0]) if row is not None else None

	@staticmethod
	def create(db: 'psycopg2.connection', fandomId: int, crossover: bool = False
			) -> 'FFNFandomDeltaResult':
		deltaResult = FFNFandomDeltaResult(
				fandomId_ = fandomId,
				crossover_ = 1 if crossover else 0,
				created_ = int(time.time()) * 1000,
				updated_ = int(time.time()) * 1000,
			)
		with db, db.cursor() as curs:
			curs.execute('''
				insert into FFNFandomDeltaResult
					(fandomId, crossover, created, updated)
				values(%s, %s, %s, %s)
				returning id''', (deltaResult.fandomId, deltaResult.crossover,
					deltaResult.created, deltaResult.updated))
			row = curs.fetchone()
			if row is not None:
				deltaResult.id = int(row[0])
				return deltaResult
			raise Exception(f"unable to create create FFNFandomDeltaResult")

	def save(self, db: 'psycopg2.connection') -> None:
		with db, db.cursor() as curs:
			curs.execute('''
				update FFNFandomDeltaResult
				set updated = %s, completed = %s, pages = %s, totalPages = %s,
					minTimestamp = %s, maxTimestamp = %s
				where id = %s
			''', (self.updated, self.completed, self.pages, self.totalPages,
				self.minTimestamp, self.maxTimestamp, self.id))

	def update(self, db: 'psycopg2.connection', pages: int, totalPages: int,
			minTimestamp: Optional[int], maxTimestamp: Optional[int]) -> None:
		self.updated = int(time.time()) * 1000
		self.pages = pages
		self.totalPages = totalPages
		self.minTimestamp = minTimestamp
		self.maxTimestamp = maxTimestamp
		self.save(db)

	def finish(self, db: 'psycopg2.connection', pages: int, totalPages: int,
			minTimestamp: Optional[int], maxTimestamp: Optional[int]) -> None:
		self.updated = int(time.time()) * 1000
		self.completed = int(time.time()) * 1000
		self.pages = pages
		self.totalPages = totalPages
		self.minTimestamp = minTimestamp
		self.maxTimestamp = maxTimestamp
		self.save(db)

