#-*- encoding: utf8 -*-

import sys
import uuid
import requests
import logging
import time
from ebooklib import epub
from bs4 import BeautifulSoup as bs

home = 'https://zh.wikisource.org'
headers = {
	'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) '
		'AppleWebKit/537.36 (KHTML, like Gecko) '
		'Chrome/51.0.2704.106 Safari/537.36'),
}

def trans_quote(text):
	return text.replace('“', '「').replace('”', '」')

def get_book_title(doc):
	return doc.h1.text

def get_author(doc):
	author_a = doc.find(lambda tag:tag.name == 'a' 
		and tag.has_attr('titl') 
		and 'Author' in tag['title']
	)

	if author_a:
		author = author_a.text
	else:
		author = 'Anonymity'
	return author

def get_charpters(doc):
	div = doc.find(id='mw-content-text')
	links = div.find_all(lambda tag: tag.name=='li' 
		and not tag.has_attr('class')
	)
	return [[home + l['href'], l.text] for l in links]

def generate_chapter_contents(doc):
	title_element = doc.select('td b')
	if title_element:
		title = title_element[1].text
	else:
		title = doc.h1.text
	paragraphs = [p.text for p in doc.select('div p')]
	return [title, paragraphs]

def make_epub_html(filename, title, contents):
	html = epub.EpubHtml(title=title, file_name=filename, lang='zh')
	html.content = '<h2>{}</h2>'.format(title)
	for c in contents:
		html.content += '<p>{}</p>'.format(trans_quote(c))

	return html

def main(book_link):
	index = bs(requests.get(book_link, headers=headers).text, 'html.parser')
	title = get_book_title(index)
	author = get_author(index)
	chapters = get_charpters(index)


	book = epub.EpubBook()
	book.set_identifier(uuid.uuid4().urn)
	book.set_title(title)
	book.add_author(author)
	book.add_metadata('DC', 'contributor', 'http://www.digglife.net', {'id': 'contributor'})
	book.add_metadata('DC', 'publisher', home, {'id': 'publisher'})
	book.add_metadata('DC', 'source', book_link, {'id': 'url'})
	book.set_language('zh')

	items = []
	for i, c in enumerate(chapters):
		time.sleep(5)
		link, text = c
		chapter_html = bs(requests.get(link).text, 'html.parser')
		chapter_title, chapter_contents = generate_chapter_contents(chapter_html)
		chapter_epub = make_epub_html('chapter_{}.xhtml'.format(i), chapter_title, chapter_contents)
		book.add_item(chapter_epub)
		items.append(chapter_epub)
	
	book.add_item(epub.EpubNcx())
	nav = epub.EpubNav()
	book.add_item(nav)

	book.toc = items
	book.spine = [nav] + items

	epub.write_epub('{}.epub'.format(title), book)

if __name__ == "__main__":
	logging.basicConfig(
		format = '[%(asctime)s] [%(name)s] [%(levelname)s] : %(message)s', 
		level=logging.DEBUG
	)
	main(sys.argv[1])








