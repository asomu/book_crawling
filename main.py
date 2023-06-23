"""한국의 온라인 서점의 상품자료를 수집하는 프로그램.

    main.py : book_scraper를 사용하는 book_manager가 정의되어 있다.
    
"""
from kyobo import get_book_data
from book_scraper import BookScraperFactory
from book_info_save import BookInfoSaver
import sys


isbn = "isbn.txt"

#get_book_data(isbn)

class book_manager:
    """book_scraper를 사용하여 책품목의 정보를 가져온다.
       
       1. 대표 이미지
       2. 상세정보 이미지
       3. 아이템의 각 정보들.        
    """
    def __init__(self, isbn:str = "isbn.txt") -> None:
        self._isbn_file:str = isbn
          
    def run(self):
        """book_manager의 메인동작이다.
        1. BookScraperFactory에서 온라인 서점에 따른 scraper class를 가져온다.
        2. scraper를 이용하여 대표이미지를 저장한다.
        3. 상세페이지 이미지를 저장한다.
        4. 상품 정보를 가져와서 excel 파일로 저장한다.
        
        """
        book_info_data = []
        with open(f"./{self._isbn_file}", 'r') as r:
            isbns = r.readlines()
            for isbn in isbns:
                if isbn == "\n":
                    continue    
                scrap_factory = BookScraperFactory(isbn, "Kyobo");
                scraper = scrap_factory.create()
                scraper.save_cover_image()
                scraper.save_detailed_image()
                book_info_data.append(scraper.get_info())
            book_info_saver = BookInfoSaver(book_info_data)
            book_info_saver.save_info()
                        
if __name__ == "__main__":
    bm = book_manager()
    bm.run()

