import os
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
from datetime import date
import xlsxwriter
import ssl

context = ssl._create_unverified_context()
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
            html = urlopen(url, context=context)
            soup = bs(html, "html.parser")
            save_img(soup)
            save_detail_img(soup)
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
    worksheet.write_row(0, 0, ["ISBN", "제목", "카테고리", "설명","저자", "출판사", "정가","판매가","출간일","쪽수","크기"])
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
    category = soup.find('li', {'class':'category_list_item'})
    if not category:
        category = "없습니다."
    else:
        category = category.select_one('a:last-of-type').text
    return category

def get_author(soup):
    author = soup.find('meta',{'name':'title'})['content']
    author = author.split("|")[1].split('-')[0]
    return author
    
def get_publisher(soup):
    try:
        publisher = soup.select_one(".btn_publish_link")
    except:
        publisher = "알수없음"
    return publisher.text

def get_back(soup):
    back = soup.find('meta',{'name':'description'})
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
    publisher = get_publisher(soup)
    info = [int(line), title, category, back, author, publisher, price[0], price[1], date, shape[0], shape[1]]
    book_info.append(info)
    return book_info

def get_title(soup):
    title = soup.find("meta", property="og:title")['content']
    title = title.split("|")[0]
    return title

def get_price(soup):
    try:
        sell_price = soup.select_one("#contents > div.prod_detail_header > div > div.prod_detail_view_wrap > div.prod_detail_view_area > div:nth-child(3) > div.prod_price_wrap > div.prod_price_box > div > span.price > span")
        org_price = soup.select_one("#contents > div.prod_detail_header > div > div.prod_detail_view_wrap > div.prod_detail_view_area > div:nth-child(3) > div.prod_price_wrap > div.prod_price_box > div > span.sale_price > s")
        org_price = org_price.text[:-1]
        sell_price = sell_price.text[:-1]
        price = [org_price, sell_price]
    except:
        price = ["알수없음", "알수없음"]
    return price

def get_publish_date(soup):
    publish_tag = soup.select_one(".publish_date")
    publish_date = publish_tag.get_text().split('·')[1].strip()    
    return publish_date

def get_shape(soup):
    page = soup.select_one("#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(2) > td")
    size = soup.select_one('#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(3) > td > div > span')
    try:
        page = page.get_text()        
        size = size.get_text().strip().split('\n')[0]
    except:
        print("쪽수와 크기를 가져와지 못했습니다.")
        total_page = "확인필요"
        size = "확인필요"
    page_size = [page, size]
    return page_size

def save_img(soup):
    print(type(soup))
    name = get_title(soup).replace('?', '').replace('!', '').replace(':', '').strip()
    print(name)
    if not os.path.isdir(f'./img/'):
        os.mkdir(f'./img/')
    my_titles = soup.find_all("div", {"class":"prod_thumb_swiper_wrap"})
    for title in my_titles:
        src = title.find('img').get('src')                        
        with urlopen(src, context=context) as f:
            with open(f'./img/{name}_표지.jpg', 'wb') as h:
                img = f.read()
                h.write(img)
                print(f"Save {name}_표지.jpg...")

def save_detail_img(soup):
    name = get_title(soup).replace('?', '').replace('!', '').replace(':', '').strip()
    if not os.path.isdir(f'./img/'):
        os.mkdir(f'./img/')
    my_titles = soup.select_one("#scrollSpyProdInfo > div.product_detail_area.detail_img > div > img")
    if my_titles is None:
        print(f"Fail {name} - Reason: 상세 페이지 없음...")
    else:
        src = my_titles.get('src')                        
        with urlopen(src, context=context) as f:
            with open(f'./img/{name}_상세.jpg', 'wb') as h:
                img = f.read()
                h.write(img)
                print(f"Save {name}_상세.jpg...")




