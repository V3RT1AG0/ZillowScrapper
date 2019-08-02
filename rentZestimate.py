import traceback
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from db import get_collection
import re
import json
import os
import time
from csv_utils import write_to_csv, get_unvisited_zip, write_visited_zip_code, remove_zip_code
import multiprocessing

from pyvirtualdisplay import Display

display = Display(visible=0, size=(1366, 768))
display.start()

proxyKey = 'XZApcdn3rvxztE9KQeuJgLyomYw7V5DT'
logger = logging.getLogger("Zillow Logger:")


def returnString(data):
    if data is None:
        return ""
    else:
        return data.get_text().strip()


def string_to_int(string):
    result = re.sub('[^0-9]', '', string)
    try:
        result = int(result)
    except ValueError as e:
        print(e)
    return result


def returnInteger(data):
    string = returnString(data)
    if string == "":
        return ""
    else:
        return string_to_int(string)


def return_number(data):
    if data is None:
        return None
    else:
        return re.sub('[^0-9]', '', returnString(data))


req_headers = {

    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.8',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
}


class App:
    def __init__(self, state):
        self.driver = self.setSeleniumDriver()
        self.collection = get_collection()
        item = self.collection.find_one(
            {"State": state, "Rentzestimate": {"$exists": False}, "Status": "For sale"},
            no_cursor_timeout=True)
        while item is not None:
            try:
                self.get_data(item)
                item = self.collection.find_one(
                    {"State": state, "Rentzestimate": {"$exists": False}, "Status": "For sale"},
                    no_cursor_timeout=True)
            except Exception as e:
                rentZestimate = 0
                self.collection.update_one({"zid": item["zid"]}, {
                    '$set': {
                        "Rentzestimate": rentZestimate
                    }
                }, upsert=False)
                print(traceback.format_exc())
                print(repr(e))
                pass

    def check_recaptcha(self, soup):
        captcha = soup.find("div", {"class": "g-recaptcha"})
        if captcha is None:
            return False
        else:
            print("Bot detected..")
            return True

    def get_data(self, item, retry=0):
        url = "https://www.zillow.com/homes/for_sale/" + item["zid"] + "_zpid"
        print(url)
        try:
            self.driver.get(url)
        except Exception as e:
            print(str(e) + " exception while fetching houseurl [self.driver.get()]")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            if retry == 0:
                self.get_data(item, 1)
            return
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        if self.check_recaptcha(soup):
            print("Bot detected")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            self.get_data(item)
            return

        if soup.find("div", {"id": "main-frame-error"}) is not None:
            print("Error window detected")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            if retry == 0:
                self.get_data(item, 1)
            return

        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "home-details-content")))
        rentZestimate = return_number(soup.find("div", {"class": "rent-zestimate"}))
        if rentZestimate is None:
            print("try 2")
            rentZestimate = return_number(soup.find("div", {"id": "ds-rental-home-values"}))
        if rentZestimate is None:
            rentZestimate = 0
        #     print("try3")
        #     element = self.driver.find_element_by_link_text("Zestimate history & details")
        #     WebDriverWait(self.driver, 7).until(
        #         EC.element_to_be_clickable((By.LINK_TEXT, "Zestimate history & details")))
        #     element.click()
        #     WebDriverWait(self.driver, 3)
        #     html2 = self.driver.page_source
        #     soup2 = BeautifulSoup(html2, 'lxml')
        #     rentZestimate = return_number(
        #         soup2.find("li", {"class": "tertiary-item"}).find("div",
        #                                                           {"class": "zestimate-value"}))
        print("rentZestimate = " + str(rentZestimate) + "for zid=" + str(item["zid"]))
        self.collection.update_one({"zid": item["zid"]}, {
            '$set': {
                "Rentzestimate": rentZestimate
            }
        }, upsert=False)

    def setSeleniumDriver(self):
        proxy = self.rotate_ip()
        options = webdriver.ChromeOptions()
        options.add_argument('--proxy-server=%s' % proxy)
        options.add_argument(
            "accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--incognito")
        options.add_argument("--window-size=1366, 768")
        options.add_argument('--no-sandbox')
        # options.add_experimental_option("prefs", {
        #     "profile.managed_default_content_settings.images": 2})  # 'disk-cache-size': 4096
        # TODO zipcode and abouve optimization and that error in bottom
        driver = webdriver.Chrome(executable_path='./chromedriver', options=options)
        # /usr/local/bin/chromedriver
        driver.set_page_load_timeout(100)
        return driver

    def rotate_ip(self):
        success = False
        proxyRotatorUrl = "http://falcon.proxyrotator.com:51337/?apiKey=" + proxyKey + "&get=true"
        while not success:
            try:
                json_response = requests.get(proxyRotatorUrl).json()
                success = True
            except Exception as e:
                print("Exception while fetching proxy url" + str(e) + "retrying...")
        proxy = json_response["proxy"]
        print("Rotating IP...new proxy=" + proxy)
        return proxy


def spawnProcess(state):
    App(state)


if __name__ == "__main__":
    state = input("Enter State Code:")
    process_count = int(input("How many process would you like to spawn in parallel:"))
    os.system('sudo killall chrome')
    os.system('sudo killall chromedriver')
    os.system('sudo killall xvfb')
    # spawnProcess(state)
    for i in range(0, process_count):
        p1 = multiprocessing.Process(target=spawnProcess, args=(state,))
        p1.start()
        time.sleep(60)
