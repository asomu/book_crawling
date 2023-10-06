from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time


def get_driver(id, pw):  
    driver = webdriver.Chrome() 
    driver.get("https://mmbr.kyobobook.co.kr/login")
    id_box = driver.find_element(By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.id > div > input')
    pw_box = driver.find_element(By.CSS_SELECTOR, '#mainDiv > main > section > div.login_form_wrap > div.form_col_group.valid_check > div.col_box.pw > div > input')
    login_btn = driver.find_element(By.CSS_SELECTOR, '#loginBtn')
    id_box.send_keys(id)
    pw_box.send_keys(pw)
    login_btn.click()
    return driver
