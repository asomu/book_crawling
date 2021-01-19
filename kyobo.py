import os
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
from datetime import date
import xlsxwriter

KYOBO_URL = 'http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode='

def get_book_data(isbn_file):
    book_info = []
    if not os.path.isdir("./img"):
        os.mkdir("./img/")
    if not os.path.isfile(f"./{isbn_file}"):
        print("isbn.txt 파일이 없습니다. isbn.txt 파일을 만들고 ISBN을 입력하세요. ")
        return

    with open(f"./{isbn_file}", 'r') as r:
        lines = r.readlines()
        for line in lines:
            if line == "\n":
                continue    
            line = line.strip()
            url = KYOBO_URL + line
            html = urlopen(url)
            soup = bs(html, "html.parser")
            # get_category(soup)
            save_img(soup, line)
            save_info(book_info, soup, line)
    save_excel(book_info)

def save_excel(book_info):
    order = 1
    while(True):
        if not os.path.isfile(f"./교보책_정보_{date.today()}_{str(order)}.xlsx"):
            workbook = xlsxwriter.Workbook(f"./교보책_정보_{date.today()}_{str(order)}.xlsx")
            worksheet = workbook.add_worksheet('Book_info')
            break
        else:
            order += 1
    worksheet.write_row(0, 0, ["ISBN", "제목", "카테고리", "설명","저자", "옮긴이", "추가정보", "출판사", "정가","판매가","출간일","쪽수","크기","키워드"])
    cell_format = workbook.add_format({'num_format': '0'})
    worksheet.set_column('A:A',15, cell_format)
    worksheet.set_column('B:B',30)
    worksheet.set_column('C:C',10)
    worksheet.set_column('D:D',15)
    worksheet.set_column('E:E',10)
    worksheet.set_column('F:F',10)
    worksheet.set_column('G:G',10)
    worksheet.set_column('H:H',10)
    worksheet.set_column('I:I',10)
    worksheet.set_column('J:J',10)
    worksheet.set_column('K:K',10)
    worksheet.set_column('L:L',10)
    worksheet.set_column('M:M',10)
    worksheet.set_column('N:N',10)
    worksheet.set_column('O:O',20)
    row = 1
    for info in book_info:
        worksheet.write_row(row, 0, info)
        row += 1

    workbook.close()

def get_category(soup):
    category = soup.find_all('p', {'class':'location'})
    if category is None:
        category = "없습니다."
    else:
        category = category[len(category)-1].find('a').text
    return category

def get_keyword(soup):
    keywords = soup.find('meta',{'name':'keywords'})
    if keywords is None:
        keywords = "키워드가 없습니다."
    else:
        keywords = keywords['content']
    return keywords

def get_author(soup):
    author = soup.find('a', {"class":"detail_author"})
    return author.text
    
def get_publisher(soup):
    try:
        publisher = soup.find('input', {"name":"pubNm"})
    except:
        publisher = "알수없음"
    return publisher['value']

def get_translator(soup):
    try:
        translator = soup.find('a', {"class":"detail_translator"})
        if translator is None:
            translator = "없음"
        else:
            translator = translator.text
    except:
        translator = "없음"
    return translator

def get_painter(soup):
    detail = ""
    painter = soup.find_all("span", {"class":"name"})
    try:
        for p in painter:
            name  = p.find("a")
            if name is not None:
                detail = detail + name.text + " "
    except:
        detail = ""
    return detail


def get_back(soup):
    back = soup.find('span',{"class":"back"})
    if back is None:
        back = "없음"
    else:
        back = back.text.strip()
    return back


def save_info(book_info, soup, line):
    title = get_title(soup)
    category = get_category(soup)
    back = get_back(soup)
    price = get_price(soup)
    date = get_publish_date(soup)
    shape = get_shape(soup)
    author = get_author(soup)
    translator = get_translator(soup)
    painter = get_painter(soup)
    publisher = get_publisher(soup)
    keywords = get_keyword(soup)
    info = [int(line), title, category, back, author, translator, painter, publisher, price[0], price[1], date, shape[0], shape[1], keywords]
    book_info.append(info)
    return book_info

def get_title(soup):
    title = soup.select_one('head > title')
    title = title.text[:len(title.text) - 7]
    return title

def get_price(soup):
    try:
        org_price = soup.find('meta',{'property':'eg:originalPrice'})
        org_price = org_price['content']
        sell_price = soup.find('meta',{'property':'eg:salePrice'})
        sell_price = sell_price['content']
        price = [int(org_price), int(sell_price)]
    except:
        price = ["알수없음", "알수없음"]
    return price

def get_publish_date(soup):
    publish_date = soup.select_one('#container > div:nth-child(4) > form > div.box_detail_point > div.author > span.date')
    return publish_date.text.strip()

def get_shape(soup):
    page = soup.select_one('#container > div:nth-child(7) > div.content_left > div:nth-child(5) > table.table_simple2.table_opened.margin_top10')
    size = soup.select_one('#container > div:nth-child(7) > div.content_left > div:nth-child(5) > table.table_simple2.table_opened.margin_top10 > tbody > tr:nth-child(3) > td')
    if (page == None):
        page = soup.select_one('#container > div:nth-child(7) > div.content_left > div:nth-child(3) > table.table_simple2.table_opened.margin_top10')
    try:
        page = page.find_all('td')
        total_page = page[1].text.strip()
        size = page[2].text[:len(page[2].text) - 5]
    except:
        print("쪽수와 크기를 가져와지 못했습니다.")
        total_page = "확인필요"
        size = "확인필요"
    page_size = [total_page, size]
    return page_size

def author(soup):
    return

def save_img(soup, line):
    name = get_title(soup).replace('?', '').replace('!', '')
    print(name)
    if not os.path.isdir(f'./img/{name}/'):
        os.mkdir(f'./img/{name}/')
    my_titles = soup.find_all('img')
    for title in my_titles:
        src = title.get('src')
        idx = src.find('large/')
        if(idx > 0):
            if(src[idx+11:idx+24] == line):
                xlarge_src = src[:idx] + 'xlarge' + src[idx+5:idx+10] + 'x' + src[idx+11:]
#                print(xlarge_src)
                try:
                    with urlopen(xlarge_src) as f:
                        with open(f'./img/{name}/x{line}.jpg', 'wb') as h:
                            img = f.read()
                            h.write(img)
                            print(f"Save x{line}.jpg...")
                except:
                    print(f"ISBN: {line} have not X large image...skip save image.")
        if(src.find('i' + line) > 0):
#            print(src)
            with urlopen(src) as f:
                with open(f'./img/{name}/i{line}.jpg', 'wb') as h:
                    img = f.read()
                    h.write(img)
                    print(f"Save i{line}.jpg...")





