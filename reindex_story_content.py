#!/usr/bin/env python3
import os
import sys
import math
import time
import signal
import traceback
import psycopg2
import elasticsearch.helpers # type: ignore
from elasticsearch import Elasticsearch
from typing import Any, List, Dict, Optional, Iterator
from oil import oil
import oil.util as util
import weaver.enc as enc
from minerva import FFNFicContent
from htmlView import HtmlView

logFileName = f'./reindex_story_content.log'

def plog(msg: str) -> None:
	global logFileName
	print(f'{int(time.time())}|{msg}')
	util.logMessage(msg, fname = logFileName, logDir = './')

def dropIndex(es: Any) -> None:
	try:
		es.indices.delete(index='ffn')
	except:
		pass

def createIndex(es: Any) -> None:
	try:
		es.indices.create(index='ffn', body={
				'mappings': {
					'properties': {
						'content': { 'type':'text' },
					},
				},
			})
	except:
		pass

class timeout:
	def __init__(self, seconds: int = 1, error_message: str = 'Timeout'):
		self.seconds = seconds
		self.error_message = error_message
	def handle_timeout(self, signum: int, frame: Any) -> None:
		raise TimeoutError(self.error_message)
	def __enter__(self) -> None:
		signal.signal(signal.SIGALRM, self.handle_timeout)
		signal.alarm(self.seconds)
	def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
		signal.alarm(0)

def htmlToMd(html: str) -> str:
	with timeout(seconds=3):
		v = HtmlView(html)
		return  '\n'.join(v.text)

def handleContent(db: 'psycopg2.connection', c: FFNFicContent
		) -> Optional[Dict[str, Any]]:
	#if fid % stripeCount != stripe: return
	id_ = f'{c.fid}/{c.cid}'
	dec = enc.decode(c.content, id_)
	if dec is None:
		raise Exception("unknown encoding")
	html = dec[1]

	try:
		# try to grab just the story content
		md = htmlToMd(html)

		return { '_id': id_, 'fid': c.fid, 'cid': c.cid, 'content': md, }
		#res = es.index(index="ffn", id=id_, body=doc)
		#print(res['result'])
	except:
		plog(f"{c.wid} is broken")
		with open(f"./edump/edump_wid_{c.wid}.html", 'w') as f:
			f.write(html)
		plog(traceback.format_exc())
	return None

def handleBlock(db: 'psycopg2.connection', fidx: int, eidx: int,
		stripeCount: int, stripe: int) -> Iterator[Dict[str, Any]]:
	for c in FFNFicContent.fetchWidRange(db, fidx, eidx, stripeCount, stripe):
		if c.content is None or len(c.content) < 1:
			continue
		d = handleContent(db, c)
		if d is None:
			continue
		yield d

def main(db: 'psycopg2.connection', es: Any) -> None:
	if len(sys.argv) not in {1, 2, 4}:
		print(f"usage: {sys.argv[0]} [start [stripeCount stripe]]")
		sys.exit(1)
	
	if len(sys.argv) == 4:
		global logFileName
		logFileName = f"./reindex_story_content_{sys.argv[2]}_{sys.argv[3]}.log"

	plog(f"using log {logFileName}")

	maxId = FFNFicContent.maxWid(db)
	plog(f"maxId: {maxId}")

	roundTo = 100
	overshoot = 20
	start = 0
	end = maxId
	end = int((end + roundTo -1) / roundTo) * roundTo

	stripeCount = 1
	stripe = 0

	if len(sys.argv) >= 2:
		start = int(sys.argv[1])
	if len(sys.argv) >= 4:
		stripeCount = int(sys.argv[2])
		stripe = int(sys.argv[3])

	plog(f"stripe: {stripe}")
	plog(f"stripeCount: {stripeCount}")

	plog(f"from {start} to {end}")
	blockSize = 5000 * stripeCount

	fidx = start - blockSize
	cnt = 0
	while fidx < end:
		fidx += blockSize
		eidx = min(fidx + blockSize, end)
		plog(f"  doing ids [{fidx}, {eidx})")

		success = False
		for t in range(10):
			if success:
				break
			if t > 0:
				time.sleep(5)
			try:
				elasticsearch.helpers.bulk(client=es, index='ffn',
						actions=handleBlock(db, fidx, eidx, stripeCount, stripe))
				cnt += 1
				success = True
			except SystemExit as e:
				raise
			except:
				plog(f"  trouble in ids [{fidx}, {eidx})")
				plog(traceback.format_exc())
		if not success:
			plog(f"  permanent trouble in ids [{fidx}, {eidx})")
			raise Exception('block failed')

if __name__ == '__main__':
	if not os.path.exists('./edump/'):
		os.makedirs('./edump/')
	es = Elasticsearch(hosts=["localhost"])
	#dropIndex(es)
	#createIndex(es)
	#sys.exit(0)
	with oil.open() as db:
		main(db, es)
	sys.exit(0)

sys.exit(0)

#res = es.get(index="test-index", id=1)
#print(res['_source'])

#es.indices.refresh(index="test-index")

#res = es.search(index="test-index", body={"query": {"match_all": {}}})
#print("Got %d Hits:" % res['hits']['total']['value'])
#for hit in res['hits']['hits']:
	#print(hit)

