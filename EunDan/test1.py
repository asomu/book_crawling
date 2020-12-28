
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus

with open("./eunDan/isbn.txt", 'r') as r:
    lines = r.readlines
    for line in lines:
        print(line)
        #url = 'http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode=' + line
        #html = urlopen(url)
        print(line)