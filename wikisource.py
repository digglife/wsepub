#-*- encoding: utf8 -*-

import sys
import uuid
import requests
import logging
import time
import re
from ebooklib import epub
from bs4 import BeautifulSoup, Tag, NavigableString

home = 'https://zh.wikisource.org'
headers = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/51.0.2704.106 Safari/537.36'),
}


def trans_quote(text):
    return text.replace('“', '「').replace('”', '」')


def get_cover_image(title):
    params = {
        'act': 'input',
        'category_path': '01.00.00.00.00.00',
        'type': '01.00.00.00.00.00',
        'key': title
    }
    search_doc = bs(requests.get('http://search.dangdang.com/',
                                 params,
                                 headers=headers).text, 'html.parser'
                    )

    result_num = search_doc.find('span', class_='total').em.text
    if result_num == '0':
        return None
    book_url = search_doc.find('a', attrs={'name': 'itemlist-title'})['href']
    book_details = bs(requests.get(book_url).text, 'html.parser')
    image_url = book_details.find('img', id='largePic')['src']
    image_content = requests.get(image_url).content
    return image_content


def get_book_title(doc):
    return doc.h1.text


def get_author(doc):
    author_a = doc.find(lambda tag: tag.name == 'a'
                        and tag.has_attr('title')
                        and 'Author' in tag['title']
                        )

    if author_a:
        author = author_a.text
    else:
        author = 'Anonymity'
    return author


def remove_junk_elements(doc):
    editor_span = doc.find_all('span', class_='mw-editsection')
    if editor_span:
        for e in editor_span:
            e.extract()
    return doc


def get_charpters(doc):
    div = doc.find(id='mw-content-text')
    links = div.find_all(lambda tag: tag.name == 'li'
                         and not tag.has_attr('class')
                         )
    return [[home + l.a['href'], l.text] for l in links]


def generate_chapter_contents(doc):
    div = doc.find(id='mw-content-text')
    # The metadata of a chapter is in the center td of the table, of which the
    # css style is not certain.
    metadata = doc.find('td', width='50%') or doc.find(
        'td', style='width:50%;')
    if metadata:
        title_element = [m for m in metadata.contents if m != '\n'][2]
        if isinstance(title_element, Tag):
            title = title_element.text.strip()
        else:
            title = title_element.strip()
    else:
        title = doc.h1.text
    #paragraphs = [p.text for p in doc.select('div p')]
    # Only get headers and paragraphs.
    div = remove_junk_elements(div)
    main_text = div.find_all(re.compile('^p|h\d$'))
    contents = ''.join([str(c) for c in main_text])
    return [title, contents]


def make_epub_html(filename, title, contents):
    html = epub.EpubHtml(title=title, file_name=filename, lang='zh')
    html.content = '<h2>{}</h2>'.format(title)
    html.content += trans_quote(contents)

    return html


def main(book_link):
    index = BeautifulSoup(
        requests.get(book_link, headers=headers).text, 'html.parser')
    title = get_book_title(index)
    author = get_author(index)
    chapters = get_charpters(index)
    cover_image = get_cover_image(title)

    book = epub.EpubBook()
    book.set_identifier(uuid.uuid4().urn)
    book.set_title(title)
    book.add_author(author)
    book.add_metadata(
        'DC', 'contributor', 'http://www.digglife.net', {'id': 'contributor'})
    book.add_metadata('DC', 'publisher', home, {'id': 'publisher'})
    book.add_metadata('DC', 'source', book_link, {'id': 'url'})
    book.set_language('zh')
    if cover_image:
        book.set_cover('cover.jpg', cover_image, create_page=False)

    items = []
    for i, c in enumerate(chapters):
        time.sleep(5)
        link, text = c
        chapter_html = BeautifulSoup(requests.get(link).text, 'html.parser')
        chapter_title, chapter_contents = generate_chapter_contents(
            chapter_html)
        chapter_epub = make_epub_html(
            'chapter_{}.xhtml'.format(i), chapter_title, chapter_contents)
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
        format='[%(asctime)s] [%(name)s] [%(levelname)s] : %(message)s',
        level=logging.DEBUG
    )
    main(sys.argv[1])
