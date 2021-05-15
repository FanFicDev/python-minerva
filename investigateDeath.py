#!/usr/bin/env python
import sys
import psycopg2
from bs4 import BeautifulSoup # type: ignore
from oil import oil
from weaver import Web, WebBase
import weaver.enc as enc
from minerva import FFNParser, FFNFic, extractFFNDeathCode

def plog(msg: str, fname: str = "./mortician.log") -> None:
	with open(fname, 'a') as f:
		f.write(msg + '\n')
		print(msg)

def main(db: 'psycopg2.connection') -> None:
	if len(sys.argv) != 2:
		raise Exception("expected wid")

	wid = int(sys.argv[1])

	some = Web.fetchIdRange(db, wid, wid + 1)
	if len(some) != 1:
		raise Exception("TODO")
	w = some[0]
	assert(w.url is not None and w.created is not None)

	if not w.url.startswith('https://www.fanfiction.net/s/'):
		raise Exception("not a ffn url")

	fid = int(w.url.split('/')[4])
	print(f"fid: {fid}")

	response = w.response
	if response is None and w.wbaseId is not None:
		wbase = WebBase.lookup(db, w.wbaseId)
		if wbase is None:
			raise Exception("has null web_base")
		response = wbase.response

	if response is None or len(response) < 1:
		print("response is null")
		return

	dec = enc.decode(response, w.url)
	if dec is None:
		raise Exception("unknown encoding")
	html = dec[1]

	code = extractFFNDeathCode(html)
	if code != 0:
		plog(f"  dead: {code}")
		c = FFNFic.bury(db, fid, code, w.created, True)
		print(c)
		#print(html)
	else:
		plog(f"  {fid} healthy?")
		print(html)
		try:
			ffnParser = FFNParser()
			ts = int(w.created / 1000)
			fic = ffnParser.get(db, fid, ts, BeautifulSoup(html, 'html5lib'))
			plog(f"{fic.__dict__}")
		except:
			plog(f"{w.url} is broken")
			#with open(f"./edump_{fid}_{cid}.html", 'w') as f:
			#	f.write(html)
			raise

if __name__ == '__main__':
	with oil.open() as db:
		main(db)
	sys.exit(0)

