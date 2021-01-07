
from os.path import isfile
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
import os
import sys
from openpyxl import Workbook

write_wb = Workbook()
write_ws = write_wb.create_sheet('북인포')
write_ws = write_wb.active
write_ws.append(["제목","정가","출간일","쪽수","크기","ISBN"])

if not os.path.isdir("./img"):
    os.mkdir("./img/")
if not os.path.isfile("./isbn.txt"):
    print("isbn.txt 파일이 없습니다. 파일을 만들고 ISBN을 입력하세요. ")
else:
    with open("./isbn.txt", 'r') as r:
        lines = r.readlines()
        for line in lines:
            line = line.strip()
            url = 'http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode=' + line
            html = urlopen(url)
            soup = bs(html, "html.parser")
            title = soup.select_one('head > title')
            org_price = soup.select_one('#container > div:nth-child(4) > form > div.box_detail_order > div.box_detail_price > ul > li:nth-child(1) > span.org_price')
            publish_data = soup.select_one('#container > div:nth-child(4) > form > div.box_detail_point > div.author > span.date')
            page = soup.select_one('#container > div:nth-child(7) > div.content_left > div:nth-child(5) > table.table_simple2.table_opened.margin_top10')
            size = soup.select_one('#container > div:nth-child(7) > div.content_left > div:nth-child(5) > table.table_simple2.table_opened.margin_top10 > tbody > tr:nth-child(3) > td')
            title = title.text[:len(title.text) - 7]
            org_price = org_price.text.strip()
            publish_data = publish_data.text.strip()[:len(publish_data) - 4]
            result_line = title + "," + org_price + "," + publish_data
            page = page.find_all('td')
            tatal_page = page[1].text
            size = page[2].text[:len(page[2].text) - 5]
            print(result_line)
            write_ws.append([title,org_price,publish_data,tatal_page,size,int(line)])
            my_titles = soup.find_all('img')
#            print(my_titles)
            for title in my_titles:
                src = title.get('src')
#                print(src)
                idx = src.find('large/')
                if(idx > 0):
                    if(src[idx+11:idx+24] == line):
                        xlarge_src = src[:idx] + 'xlarge' + src[idx+5:idx+10] + 'x' + src[idx+11:]
                        print(xlarge_src)
                        try:
                            with urlopen(xlarge_src) as f:
                                with open('./img/' + 'x' + line + '.jpg', 'wb') as h:
                                    img = f.read()
                                    h.write(img)      
                        except:
                            print("SKIP")
                if(src.find('i' + line) > 0):
                    print(src)
                    with urlopen(src) as f:
                        with open('./img/' + 'i' + line + '.jpg', 'wb') as h:
                            img = f.read()
                            h.write(img)
                            
for row in write_ws['F2':'F100']:
    for cell in row:
        cell.number_format = '0'
order = 1
while(True):
    if not os.path.isfile("./교보책_정보_" + str(order) + ".xlsx"):
        write_wb.save("./교보책_정보_" + str(order) + ".xlsx")
        break
    else:
        order += 1