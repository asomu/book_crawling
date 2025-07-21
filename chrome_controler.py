from selenium import webdriver
from selenium.webdriver.common.by import By

def get_driver(id, pw, site: str):      
    driver = webdriver.Chrome() 
    if site == "Kyobo":    
        driver.get("https://mmbr.kyobobook.co.kr/login")
        id_box = driver.find_element(By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.id > div > input')
        pw_box = driver.find_element(By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.pw > div > input')
        login_btn = driver.find_element(By.CSS_SELECTOR, '#loginBtn')
    elif site == "Yes24":
        driver.get("https://www.yes24.com/Templates/FTLogin.aspx")
        id_box = driver.find_element(By.CSS_SELECTOR, '#SMemberID')
        pw_box = driver.find_element(By.CSS_SELECTOR, '#SMemberPassword')
        login_btn = driver.find_element(By.CSS_SELECTOR, '#btnLogin')
    elif site == "Aladin":
        driver.get("https://www.aladin.co.kr/home/welcome")
        id_box = driver.find_element(By.CSS_SELECTOR, '#SMemberID')
        pw_box = driver.find_element(By.CSS_SELECTOR, '#SMemberPassword')
        login_btn = driver.find_element(By.CSS_SELECTOR, '#btnLogin')
    id_box.send_keys(id)
    pw_box.send_keys(pw)
    login_btn.click()
    return driver
