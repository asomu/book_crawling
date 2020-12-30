
from os.path import isfile
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
import os
import sys

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
            try:
                os.mkdir("./img/" + line)
            except:
                print("Make Directory Skip")
            soup = bs(html, "html.parser")
            my_titles = soup.find_all('img')
            for title in my_titles:
                src = title.get('src')
                idx = src.find('large/')
                if(idx > 0):
                    xlarge_src = src[:idx] + 'xlarge' + src[idx+5:idx+10] + 'x' + src[idx+11:]
                    print(xlarge_src)
                    try:
                        with urlopen(xlarge_src) as f:
                            with open('./img/'+ line + '/' + 'main_' + line + '.jpg', 'wb') as h:
                                img = f.read()
                                h.write(img)      
                    except:
                        print("SKIP")
                if(src.find('i' + line) > 0):
                    print(src)
                    with urlopen(src) as f:
                        with open('./img/'+ line + '/' + line + '.jpg', 'wb') as h:
                            img = f.read()
                            h.write(img)