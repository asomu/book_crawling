# %%
import yaml
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from PIL import Image
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs

# %%
isbn = "9788936479190"
url = f"https://product.kyobobook.co.kr/detail/S000000778486"
html = urlopen(url)
soup = bs(html, "html.parser")
print(soup)
# %%
# tag =  soup.select_one("#Search3_Result > div > table > tbody > tr > td:nth-child(3) > table > tbody > tr:nth-child(1) > td:nth-child(2) > div > div.button_search_cart_new > a")
tag = soup.select_one("#yDetailTopWrap")
tag2 = tag.find_all(".img")
print(tag2)
# %%
main_block = soup.find_all("div", {"class": "prod_thumb_swiper_wrap"})
# %%
for block in main_block:
    src = block.find('img').get('src')
    print(src)
# %%


with urlopen(src) as f:
    with open(f'./img/test.jpg', 'wb') as h:
        img = f.read()
        h.write(img)
        print(f"Save {img}.jpg...")
# %%
category = soup.find('li', {'class': 'category_list_item'})
# %%
# arr = soup.select('ul.list_basis div>a:first-child[tit
cat = category.select_one('a:last-of-type')
cat.text
# %%
category = soup.find('li', {'class': 'category_list_item'}).select_one(
    'a:last-of-type').text
category
# %%
pu = soup.select_one(".btn_publish_link")
# %%
pu.text
# %%
price = soup.select(".prod_price")
p1 = price[0].text[:-1]
p2 = price[1].text[:-1]
p3 = price[2].text[:-1]

print(p1, p2, p3)
# %%
a = soup.select_one(".publish_date")
print(a.get_text().split('·')[1].strip())
# %%
a = soup.select_one(
    "#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(3) > td > div > span")
# %%
a.get_text().strip().split('\n')[0]
# %%
page = soup.select_one(
    "#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(2) > td")
page.get_text()
# %%
author = soup.find('meta', {'name': 'title'})['content']
author = author.split("|")[1].split('-')[0]
print(author)
# %%
keywords = soup.select_one(
    '#contents > div.prod_detail_header > div > div.prod_detail_view_wrap > div.prod_detail_view_area > div:nth-child(3) > div.prod_price_wrap > div.prod_price_box > div > span.price > span')
# %%
keywords.text[:-1]
# %%
test = "testsa : asetaset"
print(test.replace(":", ""))
# %%
src = r"C:\python_workspace\VsProject\BookCrawling\img\미친 장난감_상세.jpg"
img = Image.open(src)
print(img.size)
# %%
resized_img = img.resize(
    (860, int(img.size[1]*860/img.size[0])), Image.LANCZOS)
resized_img.save(src)
# %%
driver = webdriver.Chrome()
# %%
driver.get("https://mmbr.kyobobook.co.kr/login")
# %%
id_box = driver.find_element(
    By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.id > div > input')
pw_box = driver.find_element(
    By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.pw > div > input')
login_btn = driver.find_element(By.CSS_SELECTOR, '#loginBtn')
# %%
id_box.send_keys('asomu')
pw_box.send_keys('judith6846!')
login_btn.click()

# %%


def get_login_info():
    with open('login.yaml') as f:
        film = yaml.load(f, Loader=yaml.FullLoader)
        print(film)


# %%
get_login_info()
# %%
