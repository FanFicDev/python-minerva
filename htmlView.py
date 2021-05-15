from typing import TYPE_CHECKING, List, Set
import re
import html

spaceSqeeezeRe = None
ellipseSqueezeRe = None
ellipseSpaceRe = None

# convert unicode to ascii for display
def filterUnicode(line: str) -> str:
	global spaceSqeeezeRe, ellipseSqueezeRe, ellipseSpaceRe
	if spaceSqeeezeRe is None:
		spaceSqeeezeRe = re.compile('\s{2,}')
	if ellipseSqueezeRe is None:
		ellipseSqueezeRe = re.compile('(…\s*){2,}')
	if ellipseSpaceRe is None:
		punctuation = '"”?\\.\'\\)_*'
		ellipseSpaceRe = re.compile('…([^ {}])'.format(punctuation))

	# remove some unicode characters
	# ['“', '”'] ['‘', '’'] "…"
	for d in ['–', '—', '-', '­', '―']:
		line = line.replace(d, '-')
	for rm in ['■']:
		line = line.replace(rm, '')
	for apo in ['ʼ', 'ʻ']:
		line = line.replace(apo, "'")
	for dq in ['❝', '❞']:
		line = line.replace(dq, '"')

	# move bold/italic past dots for ellipses squeeze
	#line = re.sub('([_*]+)(\.+)', '\\2\\1')

	# convert ellipses to unicode ellipses
	line = line.replace('...', '…')
	line = line.replace('. . .', '…')

	# squeeze extra ellipses
	line = ellipseSqueezeRe.sub('…', line)

	# remove extra space before punctuation
	line = line.replace(' …', '…')
	line = line.replace(' ,', ',')

	# squeeze strings of repeat spaces
	line = spaceSqeeezeRe.sub(' ', line)

	# make sure ellipses are followed by a space or punctuation
	line = ellipseSpaceRe.sub('… \\1', line)

	return line

def filterEmptyTags(line: str) -> str:
	# remove empty open/close italics and bolds
	line = line.replace('_ _', ' ')
	line = line.replace('__', '')
	line = line.replace('* *', ' ')
	line = line.replace('**', '')
	line = line.replace('*"*', '"')

	return line

def sanitizeHtml(html: str) -> str:
	from bs4 import BeautifulSoup # type: ignore

	# extracted entirely
	blacklist = {'script', 'style'}
	# attrs stripped
	whitelist = {'em', 'i', 'strong', 'b', 'bold', 'hr', 'br', 's'}
	# turned into p
	blockWhitelist = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
	# turned into span
	spanWhitelist: Set[str] = set()

	soup = BeautifulSoup(html, 'html5lib')
	for tag in soup.find_all():
		if tag.name.lower() in blacklist:
			tag.extract() # strip tag and children
			continue
		tag.attrs.clear()
		if tag.name.lower() in whitelist:
			continue
		elif tag.name.lower() in spanWhitelist:
			tag.name = "span"
		elif tag.name.lower() in blockWhitelist:
			tag.name = "p"
		else:
			tag.name = "span"

	return str(soup)

class HtmlView:
	def __init__(self, html: str, markdown: bool = True,
			extraTitles: List[str] = None) -> None:
		hrRes = [
				'[!/\\\\&#~*_XxIiOoHhPpsVv80°¤ :.…=><12)(+\[\]-]{3,}',
				'[~0-9]{3,}', '[ua-]{5,}',
				'(.)\\1{10,}', '(.)(.)(\\1\\2){5,}\\1?\\2?',
				'(.)(.)(.)(\\1\\2\\3){5,}\\1?\\2?\\3?',
				'(.{2,}) ?(\\1 ?){3,}', '(.{5,}) ?(\\1 ?){2,}',
				'[\'~`^,._-]{4,}',
			]
		self.gamerRe = re.compile('^[HhMmXx][Pp]:? [0-9]+')
		self.hrRes = [re.compile('^' + r + '$') for r in hrRes]
		self.extraTitles: List[str] = [] if extraTitles is None else extraTitles
		self.spaceRe = re.compile('\s+')
		self.text: List[str] = []
		self.markdown = markdown
		self.__processHTML(html)

	def __addLines(self, lines: List[str]) -> None:
		for line in lines:
			self.__addLine(line)

	def __addLine(self, line: str) -> None:
		line = html.unescape(line)
		line = filterUnicode(line)

		line = line.replace('Sony', 'Sonny') # TODO: hack...
		line = line.strip()

		if line == 'Work Text:' or line == 'Chapter Text' \
				or line == 'Next Chapter' or line == 'Last Chapter Next Chapter':
			return

		# filter out blank/all-space lines
		if line.isspace() or len(line) == 0:
			return

		if line.strip() == '_‗_' or line.strip() == '___' \
				or line.strip() == 'Prev Main Next':
			return

		hrTitles = ["~~bonds of blood~~", "~~bonds of bloods~~",
				"- dp & sw: ribsr -", "- dp & sw: tfop -",
				"hp & ha - safh",
				"_‗_", "-==(oio)==-", '\\""/', 'ˇ',
				'#', '##', '###', '* *', ' ', '.',
				'-.-fh-.-', '-break-', 'oracle2phoenix', '/', '(break)',
				'dghpdghpdghp', 'my', 'hp*the aftermath*hp',
				'~~~core threads~~~',
				'-saving her saving himself-',
				'{1}', '{2}', '{3}',
				'scene break', 'scenebreak', 'xxscenebreakxx',
				'[-]', '{-}',
				'x', '_x_', '%', '[{o}]', 'section break', '- break -',
				'-- story --', '(line break)', '-()-', '<>', '~<>~', '~',
				'(⊙_⊙) ', '(∞)', '!', "','", '!ditg!', '-{}-',
				'┐(￣ヘ￣)┌┐(￣ヘ￣)┌┐(￣ヘ￣)┌',
				"'OvO'", 'www', '-|-|-', '~•~', '::', 'scene break>', '-l-l-l-',
				'-line break-', ':)', ';)', ':', '-= LP =-', 'f/klpt',
				'~*~*~*~*~ harry&pansy ~*~*~*~*~', '....', '….', '%%%',
				'˄', '˅', '-----===ͽ ˂ O ˃ ͼ===-----', '-----===ͽ Δ ͼ===-----',
				'xxxxxxx story xxxxxxx', 'line break', 'titanfall'] + self.extraTitles

		squiggleBreaks = ['flashback', 'end flashback', 'time skip']

		# strip markdown tags
		mhr = line.strip('*_').lower()

		# strip non-markdown tags
		while (mhr.startswith('<strong>') and mhr.endswith('</strong>')) \
				or (mhr.startswith('<em>') and mhr.endswith('</em>')):
			if (mhr.startswith('<strong>') and mhr.endswith('</strong>')):
				mhr = mhr[len('<strong>'):-len('</strong>')]
			if (mhr.startswith('<em>') and mhr.endswith('</em>')):
				mhr = mhr[len('<em>'):-len('</em>')]

		matchesHrRe = False
		for hrRe in self.hrRes:
			if hrRe.match(mhr) is not None:
				matchesHrRe = True
				break
		if mhr == '"yes." "yes." "yes."' or mhr.startswith('hp: '):
			matchesHrRe = False
		if matchesHrRe and self.gamerRe.match(mhr):
			matchesHrRe = False
		# normalize weird h-rules
		if line == '***' or mhr == '<hr />' or mhr == '-' or mhr == '--' \
				or (len(line) > 0 and len(mhr) == 0) or matchesHrRe:
			line = '<hr />'
		else:
			for hrTitle in hrTitles:
				if mhr == hrTitle.lower():
					line = '<hr />'
					break
			sq = mhr.strip('~')
			for squiggleBreak in squiggleBreaks:
				if sq == squiggleBreak:
					line = '<hr />'
					break
		if (len(line) - len(line.strip('=')) > 8) \
				and (line.strip('=') == 'HG/MM' or line.strip('=') == 'MM/HG'):
			line = '<hr />'
		if (mhr.strip('~') == 'avengers tower'):
			line = '*Avengers Tower*' # TODO
		if (mhr.find('oo--oo--') >= 0 and mhr.find('FLASHBACK')):
			line = '<hr />'
		if mhr.find('hp - 260 g o 16 - hp - 260 g o 16 - hp - 260 g o 16') != -1:
			line = '<hr />'
		if len(mhr) > 10 and mhr.count('x') > len(mhr) * 0.7:
			line = '<hr />'

		if len(self.text) > 0 and line == '<hr />' and self.text[-1] == '<hr />':
			return

		line = filterEmptyTags(line)

		# blow up on very long lines (TODO: graceful)
		if len(line) > (80 * 60 * 1000000): # TODO
			raise Exception('error: extremely long line: {}\n{}'.format(
				len(line), line))

		self.text += [line]

	def __processHTML(self, htmlText: str) -> None:
		# strip simple scripts TODO needs to be much better...
		try:
			htmlText = re.sub('<script>.*?</script>', '', htmlText, flags=re.DOTALL)
			htmlText = re.sub('<noscript>.*?</noscript>', '', htmlText, flags=re.DOTALL)
			htmlText = re.sub('<!--\[if lt IE 8\]>.*?<!\[endif\]-->', '', htmlText, flags=re.DOTALL)
			htmlText = htmlText.replace(
					'Buy our stuff, go here to find out more: <a href="https://forums.spacebattles.com/threads/spacebattles-merchandise.398032/">https://forums.spacebattles.com/threads/spacebattles-merchandise.398032/</A>',
					'')
		except:
			pass

		# bleh, remove badly encoded newlines and extra backslashes
		htmlText = htmlText.replace('\\n', '\n') # bleh
		htmlText = htmlText.replace('\\r', '\n') # bleh
		htmlText = htmlText.replace('\\\\', '\\') # bleh

		# remove redundant open/close tags; prevents extra space from next step
		for t in ['strong', 'b', 'bold', 'em', 'i']:
			htmlText = htmlText.replace(f'</{t}><{t}>', '')

		for t in ['span']:
			htmlText = htmlText.replace(f'<{t}/>', '')

		# add an extra space after em close, it'll get squashed later if it's a
		# duplicate, otherwise it keeps words from running together
		htmlText = htmlText.replace('</em>', '</em> ')

		# decode nbsp into regular space
		htmlText = htmlText.replace("&nbsp;", ' ').replace('&#8203;', ' ')

		# squash two single quotes into double quotes
		htmlText = htmlText.replace("‘’", '"').replace("’’", '"').replace("''", '"')

		# strip pointless tags around spaces
		for t in ['strong', 'b', 'bold', 'em', 'i']:
			htmlText = htmlText.replace(f'<{t}> </{t}>', ' ')

		emptyThreshold = 0.35
		# if more than emptyThreshold% of all paragraphs are empty, then the text
		# is probably double spaced and we can just remove the empty ones
		emptyP = '<p> </p>'
		if (htmlText.count(emptyP) > emptyThreshold * htmlText.count('<p>')):
			htmlText = htmlText.replace(emptyP, '')

		# otherwise double spacing is probably meant to be a scene break
		if htmlText.count('<p> </p>') <= 160:
			htmlText = htmlText.replace('<p> </p>', '<hr />')

		# squash multiple breaks embedded in paragraphs into a single scene break
		breakRe = re.compile('<p>([\s\n]*<br/?>[\s\n]*)+</p>', re.MULTILINE)
		htmlText = breakRe.sub('<hr />', htmlText)
		htmlText = htmlText.replace('<p><br/>\n<br/>\n</p>', '<hr />')
		htmlText = htmlText.replace('<p><br/>\n<br/>\n<br/>\n</p>', '<hr />')

		# replace unicode nbsp with regular space
		htmlText = htmlText.replace(' ', ' ').replace(u'\u200b', ' ')

		# replace centered stars with scene break
		htmlText = htmlText.replace('<div style="text-align: center">*** </div>', '<hr />')

		# fix annoying <<< >>> scene breaks...
		# looking at you stranger in an unholy land
		htmlText = htmlText.replace('<<< >>>', '<hr />')

		# normalize all spaces into actual spaces (newlines, tabs, etc)
		htmlText = self.spaceRe.sub(' ', htmlText)

		if htmlText.find('<') == -1:
			self.__addLine(htmlText)
			return

		htmlText = htmlText.replace('<xr>', '<br>').replace('<x2>', '<h2>')

		# skip all tags that start with... (case insensitive)
		ignoreTags = [
				'!doctype', '!--', 'html', '/html',
				'head', '/head', 'peta', '/peta', 'title', '/title',
				'body', '/body', 'pont', '/pont', 'font', '/font',
				'o:p', '/o:p', 'fido', '/fido',
				'o:documentproperties', '/o:documentproperties',
				'o:author', '/o:author',
				'o:company', '/o:company',
				'o:lastauthor', '/o:lastauthor',
				'o:revision', '/o:revision',
				'o:version', '/o:version',
				'o:totaltime', '/o:totaltime',
				'o:created', '/o:created',
				'o:lastsaved', '/o:lastsaved',
				'o:pages', '/o:pages',
				'o:words', '/o:words',
				'o:characters', '/o:characters',
				'o:characterswithspaces', '/o:characterswithspaces',
				'o:lines', '/o:lines',
				'o:paragraphs', '/o:paragraphs',
				'o:template', '/o:template',
				'div', '/div', 'span', '/span',
				'h2',
				'/hr', '/br',
				'select', '/select', 'option',
				'button', '/button',
				'center', '/center',
				'a', '/a', 'img', '/img', 'sup', '/sup',
				'h3', 'ul', '/ul', 'li', '/li',
				'iframe', '/iframe',
				'h1', 'u', '/u',
				'del', '/del', 'address', '/address',
				'big', '/big', 'ol', '/ol',
				'table', '/table', 'tbody', '/tbody', 'tr', '/tr', 'td', '/td',
				'time', '/time', 'footer', '/footer',
				'small', '/small',
				'xtml', '/xtml', 'xead', '/xead', 'dir', '/dir',
				'x1', 'xink',
				'strike', '/strike', # TODO don't ignore
				'h4', '/h4', 'h5', '/h5', 'h6', '/h6',
				'pre', '/pre', # TODO
				'article', '/article',
				'aside', '/aside', # TODO
				'noscript', '/noscript', # TODO
				'dl', '/dl', 'dt', '/dt', 'dd', '/dd', # TODO
				'script', '/script', # TODO: dump contents too
				'![cdata[', # TODO
				'ppan', '/ppan', # TODO
				'cite', '/cite', # TODO
				'abbr', '/abbr', # TODO
				'sub', '/sub', # TODO
				'code', '/code', # TODO
				'meta', # TODO
				'kbd', '/kbd', # TODO
				'link', # TODO
				'acronym', '/acronym', # TODO

				'xml', '/xml', 'style', '/style', 'form', '/form', 'object', '/object',
				'ptyle', '/ptyle',
				'al', '/al', 'blink', '/blink', 'blue', '/blue', 'doc', '/doc',
				'input', '/input', 'marquee', '/marquee', 'noembed', '/noembed',
				'option', '/option', 'o:smarttagtype', '/o:smarttagtype',
				'u1:p', '/u1:p', 'u2:p', '/u2:p',

				'th', '/th', 'tt', '/tt',
				'url', '/url', 'vr', '/vr', 'wbr', '/wbr',

				'fieldset', '/fieldset',
				'legend', '/legend',

				'nav', '/nav',

				'caption', '/caption', # TODO
				'section', '/section', # TODO
				'header', '/header', # TODO
				'base', '/base', # TODO
				'label', '/label', # TODO
				'![endif]--', # TODO
				'![endif]', # TODO
				'![if', # TODO

				'ruby', '/ruby', 'rb', '/rb', 'rp', '/rp', 'rt', '/rt', # TODO oogways owl
			]
		# FIXME nested tags: <!-- <p>thing</p> -->

		# st1: and st2: ?
		#	city, place, country-region, placename, platetype, postalcode, street,
		#	address, state, time, date, personname, givenname, sn,
		#	metricconverter, stockticker, numconv, middlename

		tagCount = 0
		cline = ""
		idx = 0
		textLen = len(htmlText)

		while idx < textLen:
			# find next tag
			nopen = htmlText.find('<', idx)

			# if there are no more tags, the rest is pure text
			if nopen == -1:
				cline += htmlText[idx:]
				break

			# if there's text before the tag, add it to the current line
			if nopen != 0:
				cline += htmlText[idx:nopen]
				idx = nopen

			tagCount += 1
			# there is another tag, find the end
			nclose = htmlText.find('>', nopen)

			if nclose < nopen:
				raise Exception('open tag with no close: {}'.format(nopen))

			# yank tag body
			inner = htmlText[nopen + 1:nclose].strip().lower()
			inner = inner.split()[0] # only look at the initial piece of the tag

			if inner.startswith('!--'):
				idx = nclose + 1
				continue

			# check if it's in our generic ignore list
			didIgnore = False
			for itag in ignoreTags:
				if inner == itag:
					idx = nclose + 1
					didIgnore = True
					break
			if inner[:4] == 'st1:' or inner[:4] == 'st2:' \
					or inner[:5] == '/st1:' or inner[:5] == '/st2:':
				idx = nclose + 1
				didIgnore = True
			if not didIgnore \
					and (inner.startswith('o:') or inner.startswith('w:') \
						or inner.startswith('/o:') or inner.startswith('/w:')):
				idx = nclose + 1
				didIgnore = True
			if didIgnore:
				continue

			# horizontal rules remain like html; translate blockquote into hr
			if inner == 'hr' or inner == 'hr/' \
					or inner == 'blockquote' or inner == '/blockquote':
				self.__addLines([cline, '<hr />'])
				cline = ''
				idx = nclose + 1
				continue

			# a few things advance to the next line
			if inner == 'br' or inner == 'br/':
				# if we've just got a start tag don't actually advance the line
				if not (len(cline.strip()) == 1 and len(cline.strip().strip('*_')) == 0):
					self.__addLine(cline)
					cline = ''
				idx = nclose + 1
				continue

			if inner == 'p' or inner == '/p' \
					or inner == '/h2' or inner == '/h3' or inner == '/h1':
				if len(cline) > 0:
					self.__addLine(cline)
				cline = ''
				idx = nclose + 1
				continue

			# if our target is not markdown, only standardize on strong and em
			if self.markdown == False:
				if (inner == 'strong' or inner == 'b' or inner == 'bold'):
					cline += '<strong>'
					idx = nclose + 1
					continue
				if (inner == '/strong' or inner == '/b' or inner == '/bold'):
					cline += '</strong>'
					idx = nclose + 1
					continue
				if (inner == 'em' or inner == 'i'):
					cline += '<em>'
					idx = nclose + 1
					continue
				if (inner == '/em' or inner == '/i'):
					cline += '</em>'
					idx = nclose + 1
					continue


			# convert bold into markdown bold
			if inner == 'strong' or inner == 'b' or inner == 'bold':
				if (nclose + 1) < textLen and htmlText[nclose + 1] == ' ':
					cline += ' *'
					idx = nclose + 2
				else:
					cline += "*"
					idx = nclose + 1
				continue
			if inner == '/strong' or inner == '/b' or inner == '/bold':
				if len(cline.strip()) == 0 and len(self.text) > 0 \
						and self.text[-1] != '<hr />':
					self.text[-1] += '*'
				elif cline.endswith(' '):
					cline = cline[:-1] + '* '
				else:
					cline += '*'
				idx = nclose + 1
				continue

			# convert italics into markdown italics
			if inner == 'em' or inner == 'i':
				if (nclose + 1) < textLen and htmlText[nclose + 1] == ' ':
					cline += ' _'
					idx = nclose + 2
				else:
					cline += '_'
					idx = nclose + 1
				continue
			if inner == '/em' or inner == '/i':
				if len(cline.strip()) == 0 and len(self.text) > 0 \
						and self.text[-1] != '<hr />':
					self.text[-1] += '_'
				elif cline.endswith(' '):
					cline = cline[:-1] + '_ '
				else:
					cline += '_'
				if len(cline.strip('_ \t\r\n')) == 0:
					cline = ''
				idx = nclose + 1
				continue

			# strikethrough
			if inner == 's' or inner == '/s':
				cline += '-'
				idx = nclose + 1
				continue

			# unable to categorize tag, dump debugging info
			raise Exception('unable to process tag "{}":\n{}'.format(
				inner, htmlText[idx - 90:nclose + 90]))

		self.__addLine(cline)

		while len(self.text) > 0 and self.text[-1] in ['< Prev', 'Next >']:
			self.text = self.text[:-1]

