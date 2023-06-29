import unittest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests

chromeOptions = Options()
chromeOptions.headless = True

# Login Test
class Login(unittest.TestCase):
        
    def setUp(self):
        self.driver = webdriver.Chrome('chromedriver.exe')

    def test_login(self):
        driver = self.driver
        driver.implicitly_wait(30)
        driver.set_page_load_timeout(50)
        driver.get("http://127.0.0.1:5000/login")
        print(driver)
        login = driver.find_element(By.ID, "lgn_username")
        login.send_keys("anmol0")
        password = driver.find_element(By.ID, "lgn_password")
        password.send_keys("anm123")
        loginBtn = driver.find_element(By.ID, "lgn_submit")
        loginBtn.click()

        print(driver.current_url)
        try:
            assert "http://127.0.0.1:5000/" == driver.current_url

        except:
            print("Error in login")

        
    def tearDown(self):
        self.driver.close() 


if __name__ == "__main__":
    unittest.main()