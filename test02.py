from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
import ssl

context = ssl._create_unverified_context()
url = f"http://www.yes24.com/Product/Search?domain=ALL&query=9791168340541"
html = urlopen(url, context=context)
soup = bs(html, "html.parser")
tag =  soup.select_one("#yesSchList > li > div > div.item_img > div.img_canvas > span > span > a")
item_url = tag.get("href")
url = f"http://www.yes24.com{item_url}"
print(url)

html = urlopen(url, context=context)
soup = bs(html, "html.parser")


img_tags = soup.select_one("#infoset_chYes > div.infoSetCont_wrap > div > img")
src = img_tags.get("src")
print(src)

title = soup.find("meta", property="og:title")['content']
title = title.split("-")[0]
print(title)

category = soup.select_one("#infoset_goodsCate > div.infoSetCont_wrap > dl:nth-child(1) > dd > ul > li > a:nth-child(6)")
category = category.text
print(category)

disc = soup.find('meta',{'name':'description'})
disc = disc['content']
print(disc)

author = soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_auth > a")
author = author.text
print(author)

publisher = soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_pub > a")
publisher = publisher.text
print(publisher)


price = soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoBot > div.gd_infoTbArea")
price = price.find_all("em")
if price[0].text == "":
    print(price[1].text.("원"))
else:
    print(price[0].text)

date = soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_date")
print(date.text)


date = soup.select_one("#infoset_specific > div.infoSetCont_wrap > div > table > tbody > tr:nth-child(2) > td")
print(date.text.split("|")[2].strip())