from kyobo import get_book_data
from book_scraper import BookScraperFactory
from book_info_save import BookInfoSaver

isbn = "isbn.txt"

#get_book_data(isbn)

class book_manager:
    def __init__(self, isbn:str = "isbn.txt") -> None:
        self._isbn_file:str = isbn
          
    def run(self):
        book_info_data = []
        with open(f"./{self._isbn_file}", 'r') as r:
            isbns = r.readlines()
            for isbn in isbns:
                if isbn == "\n":
                    continue    
                scrap_factory = BookScraperFactory(isbn, "Yes24");
                scraper = scrap_factory.create()
                scraper.save_cover_image()
                scraper.save_detailed_image()
                book_info_data.append(scraper.get_info())
            book_info_saver = BookInfoSaver(book_info_data)
            book_info_saver.save_info()
                        
if __name__ == "__main__":
    bm = book_manager()
    bm.run()

    