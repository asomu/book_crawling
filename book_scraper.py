"""book_scraper class가 정의되어 있는 파일

<Class>
1. BookScraperFactory
2. BookScraperBase
3. BookScraperKyobo
4. BookScraperYes24
"""
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
from abc import ABC, abstractmethod
from book_info import BookInfo
import sys
import ssl
import os

context = ssl._create_unverified_context()

class BookScraperFactory:
    """book scraper class를 생성하여 반환한다.
       
       1. site value에 따라 반환 class가 달라진다.
        'Kyobo' : BookScraperKyobo class 를 반환한다.
        'Yes24' : BookScraperYes24 class 를 반환한다.
    """
    def __init__(self, isbn: str, site: str):
        self._isbn = isbn
        self._site = site
        self._scraper = {"Kyobo": self.create_kyobo, "Yes24":self.create_yes24}
    
    def create(self):
        return self._scraper[self._site]()
        
    def create_kyobo(self):
        return BookScraperKyobo(self._isbn)
    
    def create_yes24(self):
        return BookScraperYes24(self._isbn)
        
        
class BookScraperBase(ABC):
    """This is abstract class for book information from Koean famous book online store.

    Args:
        ABC (): abstraction class
    """
    def __init__(self, isbn):
        self._isbn = isbn.strip()
        self.book_info: BookInfo = BookInfo()
        self.soup: bs.BeautifulSoup = None
    
    def get_info(self) -> BookInfo:
        if self.book_info.isbn == "":
            self.book_info.isbn = self._isbn
            self.book_info.title = self._get_title().strip()
            self.book_info.category = self._get_category()
            self.book_info.decription = self._get_description()
            self.book_info.author = self._get_author()
            self.book_info.publisher = self._get_publisher()
            self.book_info.price_ori = self._get_price_ori()
            self.book_info.price_rel = self._get_price_rel()
            self.book_info.publised_date = self._get_published_date()
            self.book_info.page = self._get_page()
            self.book_info.book_size = self._get_book_size()        
        return self.book_info
    
    def save_cover_image(self) -> None :
        self._make_img_folder()
        src = self._get_cover_img_src()
        self._save_src2file(src, "표지")

    def save_detailed_image(self) -> None :
        self._make_img_folder()
        src = self._get_detailed_img_src()
        if src == "":
            print(f"Fail {self.book_info.title} - Reason: 상세 페이지 없음...")
        else:
            self._save_src2file(src, "상세")
    
    def _save_src2file(self, src, post_fix) -> None:
        with urlopen(src, context=context) as f:
            with open(f'./img/{self.book_info.title}_{post_fix}.jpg', 'wb') as h:
                img = f.read()
                h.write(img)
                print(f"Save {self.book_info.title}_{post_fix}.jpg...")
    
    def _make_img_folder(self) -> None:
        if not os.path.isdir(f'./img/'):
            os.mkdir(f'./img/')
        
    @abstractmethod
    def connect_bs(self) -> None:
        pass

    @abstractmethod
    def connect_selenium(self) -> None:
        pass

    @abstractmethod
    def _get_cover_img_src(self) -> None:
        pass
    
    @abstractmethod
    def _get_detailed_img_src(self) -> None:
        pass

    @abstractmethod
    def _get_title(self) -> None:
        pass
    
    @abstractmethod
    def _get_category(self) -> None:
        pass
    
    @abstractmethod
    def _get_description(self) -> None:
        pass
    
    @abstractmethod
    def _get_author(self) -> None:
        pass
    
    @abstractmethod
    def _get_publisher(self) -> None:
        pass
    
    @abstractmethod
    def _get_price_ori(self) -> None:
        pass
    
    @abstractmethod
    def _get_price_rel(self) -> None:
        pass
    
    @abstractmethod
    def _get_published_date(self) -> None:
        pass
    
    @abstractmethod
    def _get_page(self) -> None:
        pass
    
    @abstractmethod
    def _get_book_size(self) -> None:
        pass
        
        
class BookScraperKyobo(BookScraperBase):
    """교보문고 사이트를 스크래핑하기 위한 클래스

    Args:
        BookScraperBase (_type_): _description_
    """
    def __init__(self, isbn):
        super().__init__(isbn)
        self._url: str = f'http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode={isbn}'
        # self.connect_bs()
        self.connect_selenium()
        self.get_info()

    def connect_bs(self) -> None:
        html = urlopen(self._url, context=context)
        self.soup = bs(html, "html.parser")

    def connect_selenium(self) -> None:
        # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        #     chromedriver_path = os.path.join(sys._MEIPASS, "chromedriver.exe")
        #     print('running in a PyInstaller bundle')
        #     driver = webdriver.Chrome(chromedriver_path)
        # else:
        #     driver = webdriver.Chrome()
        #     print('running in a normal Python process')

        driver = webdriver.Chrome()
        driver.get(self._url)
        html = driver.page_source
        self.soup = bs(html, "html.parser")

    def _get_cover_img_src(self) -> None:
        img_tags = self.soup.find_all("div", {"class": "prod_thumb_swiper_wrap"})
        for tag in img_tags:
            src = tag.find('img').get('src')                     
        return src
    
    def _get_detailed_img_src(self) -> None:
        img_tag = self.soup.select_one("#scrollSpyProdInfo > div.product_detail_area.detail_img > div > img")
        if img_tag is None:
            src = ""
        else:
            src = img_tag.get('src')
        return src
    
    def _get_title(self) -> None:
        title = self.soup.find("meta", property="og:title")['content']
        title = title.split("|")[0]
        return title
    
    def _get_category(self) -> None:
        category = self.soup.find('li', {'class': 'category_list_item'})
        if not category:
            category = "없습니다."
        else:
            category = category.select_one('a:last-of-type').text
        return category
    
    def _get_description(self) -> None:
        disc = self.soup.find('meta', {'name': 'description'})
        if disc is None:
            disc = "없음"
        else:
            disc = disc["content"]
        return disc
    
    def _get_author(self) -> None:
        author = self.soup.find('meta', {'name': 'title'})['content']
        author = author.split("|")[1].split('-')[0]
        return author
    
    def _get_publisher(self) -> None:
        try:
            publisher = self.soup.select_one(".btn_publish_link")
        except:
            publisher = "알수없음"
        return publisher.text
    
    def _get_price_ori(self) -> None:
        try:
            org_price = self.soup.select_one("#contents > div.prod_detail_header > div > div.prod_detail_view_wrap > div.prod_detail_view_area > div:nth-child(3) > div.prod_price_wrap > div.prod_price_box > div > span.sale_price > s")
            org_price = org_price.text[:-1]
        except:
            org_price = "알수없음"
        return org_price
    
    def _get_price_rel(self) -> None:
        try:
            sell_price = self.soup.select_one("#contents > div.prod_detail_header > div > div.prod_detail_view_wrap > div.prod_detail_view_area > div:nth-child(3) > div.prod_price_wrap > div.prod_price_box > div > span.price > span")
            sell_price = sell_price.text[:-1]
        except:
            sell_price = "알수없음"
        return sell_price
    
    def _get_published_date(self) -> None:
        publish_tag = self.soup.select_one(".publish_date")
        publish_date = publish_tag.get_text().split('·')[1].strip()    
        return publish_date
    
    def _get_page(self) -> None:
        page = self.soup.select_one("#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(3) > td")
        try:
            page = page.get_text()        
        except:
            print("페이지 수를 가져오지 못했습니다.")
            page = "확인필요"
        return page
    
    def _get_book_size(self) -> None:
        size = self.soup.select_one('#scrollSpyProdInfo > div.product_detail_area.basic_info > div.tbl_row_wrap > table > tbody > tr:nth-child(4) > td > div > span')
        try:
            size = size.get_text().strip().split('\n')[0]
        except:
            print("크기를 가져오지 못했습니다.")
            size = "확인필요"
        return size


class BookScraperYes24(BookScraperBase):
    """Yes24를 스크래핑하기 위한 클래스

    Args:
        BookScraperBase (_type_): _description_
    """
    def __init__(self, isbn):
        super().__init__(isbn)
        self._url: str = f'http://www.yes24.com/Product/Search?domain=ALL&query={isbn}'        
        self.connect_bs()
        self.get_info()
        
    def connect_bs(self) -> None:            
        url = self.get_item_url()
        html = urlopen(url, context=context)
        self.soup = bs(html, "html.parser")

    def connect_selenium(self) -> None:
        pass

    def get_item_url(self):
        html = urlopen(self._url, context=context)
        soup = bs(html, "html.parser")
        tag =  soup.select_one("#yesSchList > li > div > div.item_img > div.img_canvas > span > span > a")
        if tag is None:
            item_url = "56015266"
        else:
            item_url = tag.get("href")
        url = f"http://www.yes24.com/{item_url}"
        return url

    def _get_cover_img_src(self) -> None:
        img_tags = self.soup.select_one("#yDetailTopWrap > div.topColLft > div > span > em > img")
        src = img_tags.get("src")               
        return src
    
    def _get_detailed_img_src(self) -> None:
        img_tag = self.soup.select_one("#infoset_chYes > div.infoSetCont_wrap > div > img")
        if img_tag is None:
            src = ""
        else:
            src = img_tag.get('src')
        return src
    
    def _get_title(self) -> None:
        title = self.soup.find("meta", property="og:title")['content']
        title = title.split("-")[0]
        return title
    
    def _get_category(self) -> None:
        category = self.soup.select_one("#infoset_goodsCate > div.infoSetCont_wrap > dl:nth-child(1) > dd > ul > li > a:nth-child(6)")        
        if not category:
            category = "없습니다."
        else:
            category = category.text
        return category
    
    def _get_description(self) -> None:
        disc = self.soup.find('meta',{'name':'description'})
        if disc is None:
            disc = "없음"
        else:
            disc = disc['content']
        return disc
    
    def _get_author(self) -> None:
        try:
            author = self.soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_auth > a")        
            author = author.text
        except:
            author = "알수없음"
        return author
    
    def _get_publisher(self) -> None:
        try:
            publisher = self.soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_pub > a")
            publisher = publisher.text
        except:
            publisher = "알수없음"
        return publisher
    
    def _get_price_ori(self) -> None:
        try:
            price = self.soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoBot > div.gd_infoTbArea ")
            org_price = price.find_all("em")
            if org_price[0].text == "":
                org_price = org_price[1].text.strip("원")
            else:
                org_price = org_price[0].text.strip("원")
        except:
            org_price = "알수없음"
        return org_price
    
    def _get_price_rel(self) -> None:
        try:
            price = self.soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoBot > div.gd_infoTbArea ")
            sell_price = price.find_all("em")
            if sell_price[0].text == "":
                sell_price = sell_price[2].text.strip("원")
            else:
                sell_price = sell_price[1].text.strip("원")
        except:
            sell_price = "알수없음"
        return sell_price
    
    def _get_published_date(self) -> None:
        try:
            publish_date = self.soup.select_one("#yDetailTopWrap > div.topColRgt > div.gd_infoTop > span.gd_pubArea > span.gd_date").text
        except:
            publish_date = "알수없음"
        return publish_date
    
    def _get_page(self) -> None:        
        try:
            page = self.soup.select_one("#infoset_specific > div.infoSetCont_wrap > div > table > tbody > tr:nth-child(2) > td")
            page = page.text.split("|")[0].strip()
        except:
            print("페이지 수를 가져오지 못했습니다.")
            page = "확인필요"
        return page
    
    def _get_book_size(self) -> None:
        size = self.soup.select_one("#infoset_specific > div.infoSetCont_wrap > div > table > tbody > tr:nth-child(2) > td")
        try:
            size = size.text.split("|")[2].strip()
        except:
            print("크기를 가져오지 못했습니다.")
            size = "확인필요"
        return size
