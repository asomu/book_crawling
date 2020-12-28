from typing import Tuple


with open("./eunDan/isbn.txt", 'r') as r:
    lines = r.readlines()
    with open("./eunDan/isbn_test2.txt", 'w') as f:
        for line in lines:
            f.write(line)
