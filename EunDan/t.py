
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus

with open("./eunDan/isbn.txt", 'r') as r:
    lines = r.readlines()
    for line in lines:
        line = line.strip()
        url = 'http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode=' + line
        html = urlopen(url)
        soup = bs(html, "html.parser")
        my_titles = soup.find_all('img')
        for title in my_titles:
            src = title.get('src')
            idx = src.find('large/')
            if(idx > 0):
                xlarge_src = src[:idx] + 'xlarge' + src[idx+5:idx+10] + 'x' + src[idx+11:]
                print(xlarge_src)
                with urlopen(xlarge_src) as f:
                    with open('./EunDan/img/main_' + line + '.jpg', 'wb') as h:
                        img = f.read()
                        h.write(img)           
            if(src.find('i' + line) > 0):
                with urlopen(src) as f:
                    with open('./EunDan/img/' + line + '.jpg', 'wb') as h:
                        img = f.read()
                        h.write(img)