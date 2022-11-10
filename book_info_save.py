"""book_info의 data를 excel로 저장하기 위한 클래스.

    Returns:
        _type_: _description_
"""

import xlsxwriter
import os
from datetime import date
from book_info import BookInfo
from typing import List

class BookInfoSaver:
    """book_info list를 excel로 저장한다.
    
    """
    def __init__(self, book_info:List[BookInfo]) -> None:
        self._book_info = book_info
    
    def save_info(self):
        workbook = self.get_workshet()
        worksheet = workbook.add_worksheet('Book_info')
        worksheet.write_row(0, 0, ["ISBN", "제목", "카테고리", "설명","저자", "출판사", "정가","판매가","출간일","쪽수","크기"])
        cell_format = workbook.add_format({'num_format': '0'})
        worksheet = self.sheet_init(worksheet, cell_format)
        self.set_cell_data(worksheet)
        workbook.close()
        
    def sheet_init(self, worksheet, cell_format):
        worksheet.set_column('A:A',15, cell_format)
        worksheet.set_column('B:B',30)
        worksheet.set_column('C:C',10)
        worksheet.set_column('D:D',15)
        worksheet.set_column('E:E',10)
        worksheet.set_column('F:F',10)
        worksheet.set_column('G:G',10)
        worksheet.set_column('H:H',10)
        worksheet.set_column('I:I',10)
        worksheet.set_column('J:J',10)
        worksheet.set_column('K:K',10)
        worksheet.set_column('L:L',10)
        worksheet.set_column('M:M',10)
        worksheet.set_column('N:N',10)
        worksheet.set_column('O:O',20)
        return worksheet
        
    def set_cell_data(self, worksheet):
        row = 1
        for info in self._book_info:
            info_list = [info.isbn, info.title, info.category, info.decription, info.author, info.publisher, info.price_ori, info.price_rel, info.publised_date, info.page, info.book_size]
            worksheet.write_row(row, 0, info_list)
            row += 1
    
    def get_workshet(self):
        order = 1
        while(True):
            if not os.path.isfile(f"./교보책_정보_{date.today()}_{str(order)}.xlsx"):
                workbook = xlsxwriter.Workbook(f"./교보책_정보_{date.today()}_{str(order)}.xlsx")
                break
            else:
                order += 1
        return workbook