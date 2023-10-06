"""한국의 온라인 서점의 상품자료를 수집하는 프로그램.

    main.py : book_scraper를 사용하는 book_manager가 정의되어 있다.
    
"""
from kyobo import get_book_data
from book_scraper import BookScraperFactory
from book_info_save import BookInfoSaver
from selenium import webdriver
from chrome_controler import get_driver
import yaml
import time

isbn = "isbn.txt"


def get_login_info():
    try:
        with open('login.yaml') as f:
            login_info = yaml.load(f, Loader=yaml.FullLoader)
            return (login_info["id"], login_info["pw"])
    except Exception as e:
        print("login.yaml 파일을 읽을 수가 없습니다. 확인 바랍니다.")

# get_book_data(isbn)


class book_manager:
    """book_scraper를 사용하여 책품목의 정보를 가져온다.

       1. 대표 이미지
       2. 상세정보 이미지
       3. 아이템의 각 정보들.        
    """

    def __init__(self, id: str, pw: str, isbn: str = "isbn.txt") -> None:
        self._isbn_file: str = isbn
        self._id = id
        self._pw = pw

    def run(self):
        """book_manager의 메인동작이다.
        1. BookScraperFactory에서 온라인 서점에 따른 scraper class를 가져온다.
        2. scraper를 이용하여 대표이미지를 저장한다.
        3. 상세페이지 이미지를 저장한다.
        """
        driver = get_driver(self._id, self._pw)
        time.sleep(5)
        with open(f"./{self._isbn_file}", 'r') as r:
            isbns = r.readlines()
            for isbn in isbns:
                if isbn == "\n":
                    continue
                scrap_factory = BookScraperFactory("Kyobo", driver)
                scrap_factory.set_isbn(isbn)
                scraper = scrap_factory.create()
                scraper.save_cover_image()
                scraper.save_detailed_image()


if __name__ == "__main__":
    id, pw = get_login_info()
    bm = book_manager(id, pw)
    bm.run()
