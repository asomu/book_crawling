from selenium import webdriver
import os, sys

def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)



# if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
#     chromedriver_path = os.path.join(sys._MEIPASS, "chromedriver.exe")
#     print('running in a PyInstaller bundle')
#     driver = webdriver.Chrome(chromedriver_path)
# else:
#     driver = webdriver.Chrome()
#     print('running in a normal Python process')

driver = webdriver.Chrome(resource_path("C:\DRIVERS\chromedriver.exe"))

# driver = webdriver.Chrome()
url = 'https://product.kyobobook.co.kr/detail/S000001835614'
driver.get(url)
#driver.implicitly_wait(3)
html = driver.page_source
print(html)
print("pause")
