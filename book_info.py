"""
This is class for book information.


"""    
from dataclasses import dataclass, field


#["ISBN", "제목", "카테고리", "설명","저자", "출판사", "정가","판매가","출간일","쪽수","크기"])

@dataclass
class BookInfo:
    isbn: str = ""
    title: str = ""
    category: str = ""
    decription: str = ""
    author: str = ""
    publisher: str = ""
    price_ori: str = ""
    price_rel: str = ""
    date_publish: str = ""
    page: str = ""
    book_size: str = ""