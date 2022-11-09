from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
import ssl

context = ssl._create_unverified_context()
url = f"https://product.kyobobook.co.kr/detail/S000001835614"
html = urlopen(url, context=context)
soup = bs(html, "html.parser")

print(soup)