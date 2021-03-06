import traceback
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from db import mongo
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
        return ""
    else:
        return re.sub('[^0-9]', '', returnString(data))


class App:

    def __init__(self, state):
        self.proxyDict = {}
        self.req_headers = self.setHeaders()
        self.handle_fetch_cards_exception()
        self.driver = self.setSeleniumDriver()
        self.mongo_client = mongo()
        # self.driver.get("https://www.whatismyip.com/my-ip-information/")

        zipcode = self.get_zip_codes(state)[0]
        while zipcode is not None:
            self.current_zipcode = str(zipcode)
            self.current_state = state
            write_visited_zip_code(state, zipcode)
            try:
                self.find_articles_by_zip(str(zipcode))  # 22312
            except KeyboardInterrupt:
                print("KeyBoardInterupt. Removing zipcode..")
                remove_zip_code(state, zipcode)
                # self.driver.close()
                return
            except Exception as e:
                print("caught in second level exception handler")
                remove_zip_code(state, zipcode)
                print(traceback.format_exc())
                # self.driver.close()
                time.sleep(4)
                raise e
            zipcode = self.get_zip_codes(state)[0]
        self.driver.close()
        # self.find_articles_by_state

    def get_zip_codes(self, state):
        zipcodes = get_unvisited_zip(state)
        return zipcodes

    def check_recaptcha(self, soup):
        captcha = soup.find("div", {"class": "g-recaptcha"})
        if captcha is None:
            return False
        else:
            print("Bot detected..")
            return True

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

    def setHeaders(self):
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.8',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
        }

    def setSeleniumDriver(self):
        proxy = self.rotate_ip()
        options = webdriver.ChromeOptions()
        # options.addExtensions(new File("C:\\whatever\\Block-image_v1.0.crx"))
        options.add_argument('--proxy-server=%s' % proxy)
        options.add_argument(
            "accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--incognito")
        options.add_argument("--window-size=1366, 768")
        # options.add_argument('--headless')

        ############
        # options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        # options.add_argument("start-maximized")
        # options.add_argument("disable-infobars")
        # options.add_argument("--disable-extensions")
        ###########

        options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2})  # 'disk-cache-size': 4096
        # TODO zipcode and abouve optimization and that error in bottom
        driver = webdriver.Chrome(executable_path='./chromedriver', options=options)
        # /usr/local/bin/chromedriver
        driver.set_page_load_timeout(100)
        return driver

    def scrapeForSold(self, soup2, returndata):
        returndata["Price"] = return_number(soup2.find("div", {"class": "status"}))
        returndata["Status"] = "Sold"
        returndata["Address"] = returnString(soup2.find("h1", {"class": "zsg-h1"}))
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.find("h3", {"class": "edit-facts-light"}).findAll("span",
                                                                                {"class": False})

        # assigning each value in a list to a its corresponding varaible
        returndata["Bedrooms"], returndata["Bathrooms"], returndata["AreaSpace_SQFT"] = [return_number(span) for span in
                                                                     bed_bath_area]

        # returndata["summary"] = returnString(soup2.find("div", {"class": "zsg-content-item home-description"}))
        returndata["ZestimatePrice"] = return_number(
            soup2.find("div", {"class": "zestimate primary-quote"}))
        # returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)

        facts = soup2.find("div", {"class": "home-facts-at-a-glance-section"}).find_all("div")
        for fact in facts:
            label = returnString(fact.find("div", {"class": "fact-label"}))
            value = returnString(fact.find("div", {"class": "fact-value"}))
            returndata[label] = value

        # GET HISTORICAL DATA
        try:
            price_history = soup2.find("table",
                                       {"class": "zsg-table zsg-content-component"}).find_all(
                "tr")
            historyList = []
            for hs in price_history[1:]:
                hist = dict()
                items = hs.contents
                hist["date"] = returnString(items[0])
                hist["event"] = returnString(items[1])
                hist["price"] = returnString(items[2])
                historyList.append(hist)
            returndata["SaleHistory"] = historyList
        except Exception as e:
            logger.error("exception " + repr(e) + "in scrape for history for sold ")
            returndata["SaleHistory"] = ""
            pass

        # WRITING TO CSV FILE
        self.mongo_client.insert_article_without_upsert(returndata)
        # write_to_csv(returndata)

    def scrapeForSale(self, soup2, returndata):
        returndata["Price"] = returnInteger(soup2.find("span", {"class": "ds-value"}))
        returndata["Status"] = returnString(soup2.find("span", {"class": "ds-status-details"}))
        returndata["Address"] = returnString(soup2.find("h1", {"class": "ds-address-container"}))
        address = returndata["Address"].split()
        returndata["ZipCode"] = address[-1]
        returndata["State"] = address[-2]
        address = returndata["Address"].split(",")
        returndata["Locality"] = address[-2].strip()
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.findAll("span", {"class": "ds-bed-bath-living-area"})
        try:
            scores = soup2.findAll("a", {"class": "ws-value"})
            returndata["WalkScore"] = returnInteger(scores[0])
            returndata["TransitScore"] = returnInteger(scores[1])
        except Exception as e:
            print("unable to fetch walk/trasit score")
            logger.error(repr(e))
            pass
        # print(bed_bath_area)
        # assigning each value in a list to a its corresponding varaible
        returndata["Bedrooms"], returndata["Bathrooms"], returndata["AreaSpace_SQFT"] = [
                                                                                            return_number(
                                                                                                row.span)
                                                                                            for row
                                                                                            in
                                                                                            bed_bath_area][
                                                                                        :3]
        # returndata["summary"] = returnString(soup2.find("div", {"class": "character-count-text-fold-container"}))
        # returndata["zestimate"] = return_number(soup2.find("h4", {"class": "zestimate-value"}))
        returndata["ZestimatePrice"] = return_number(
            soup2.find("span", {"class": "ds-estimate-value"}))

        # returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)
        facts = soup2.find("ul", {"class": "ds-home-fact-list"}).find_all("li")
        for fact in facts:
            label = returnString(
                fact.find("span", {"class": "ds-standard-label ds-home-fact-label"}))
            value = returnString(fact.find("span", {"class": "ds-body ds-home-fact-value"}))
            if '$' in value:
                returndata[label] = string_to_int(value)
            else:
                returndata[label] = value

        try:
            if "Year built:" not in returndata:
                returndata["Year built:"] = returnString(
                    soup2.find("td", string="Year built").next_sibling)
        except Exception:
            print("Year data not found")
            pass

        # SAVE HISTORICAL DATA
        try:
            price_history = soup2.find("table", {
                "class": "zsg-table ds-price-and-tax-section-table"}).find_all(
                "tr")
            historyList = []
            for hs in price_history[1:]:
                hist = dict()
                items = hs.contents
                hist["date"] = returnString(items[0])
                hist["event"] = returnString(items[1])
                hist["price"] = returnString(items[2])
                historyList.append(hist)
            returndata["SaleHistory"] = historyList
        except Exception as e:
            print(soup2.prettify())
            logger.error("exception " + repr(e) + "in scrape for history for sale/rent ")
            returndata["SaleHistory"] = ""
            pass

        # WRITING TO CSV FILE
        # print(returndata)
        self.mongo_client.insert_article_without_upsert(returndata)
        # write_to_csv(returndata)

    def scrapeArticle(self, result, type, retry=0):
        returndata = dict()

        # use selenium to load individual house article
        # print(str(type))
        if type == 1:
            # data is obtained from result directly
            try:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result['data-zpid'] + "_zpid"
                returndata["zid"] = result['data-zpid']
            except KeyError as e:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result['id'][5:] + "_zpid"
                returndata["zid"] = result['id'][5:]
            except Exception as e:
                logger.error("exception " + repr(e) + " on line 248")
                return
            returndata["Latitude"] = float(result["data-latitude"]) / 1000000
            returndata["Longitude"] = float(result["data-longitude"]) / 1000000
        else:
            # else in case data is obtained from result.article
            try:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result.article[
                    'data-zpid'] + "_zpid"
                returndata["zid"] = result.article['data-zpid']
            except KeyError as e:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result.article['id'][
                                                                      5:] + "_zpid"
                returndata["zid"] = result.article['id'][5:]
            except Exception as e:
                logger.error("exception " + repr(e) + " on line 257")
                return
            returndata["Latitude"] = json.loads(returnString(result.script))['geo']['latitude']
            returndata["Longitude"] = json.loads(returnString(result.script))['geo']['longitude']

        if self.mongo_client.check_if_zid_already_exist(returndata["zid"]) is not None:
            print("zid: " + returndata["zid"] + " already exist in db")
            return

        # print(str(returndata["longitude"]) + " / " + str(returndata["latitude"]))
        returndata["location"] = {"type": "Point",
                                  "coordinates": [returndata["Longitude"], returndata["Latitude"]]}

        print("Fetching..." + houseurl)

        try:
            self.driver.get(houseurl)
        except Exception as e:
            print(str(e) + " exception while fetching houseurl [self.driver.get()]")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            self.scrapeArticle(result, type)
            return

        html = self.driver.page_source
        soup2 = BeautifulSoup(html, 'lxml')

        # restart scraping for same article if captcha or error deteted
        if self.check_recaptcha(soup2):
            print("Bot detected")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            self.scrapeArticle(result, type, 0)
            return

        if soup2.find("div", {"id": "main-frame-error"}) is not None:
            print("Error window detected")
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            if retry == 0:
                self.scrapeArticle(result, type, 1)
            return

        try:
            if soup2.find("span", {"class": "ds-status-details"}) is None:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "price-and-tax-history")))
                self.driver.find_element_by_id("price-and-tax-history").click()
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located(
                        (By.ID, "hdp-price-history")))  # handle timeoutexceptio 100seconds
                html = self.driver.page_source
                soup2 = BeautifulSoup(html, 'lxml')
                self.scrapeForSold(soup2, returndata)
            else:

                WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ds-value")))
                WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "ds-price-and-tax-section-table")))
                try:
                    if not len(self.driver.find_elements_by_class_name("ws-value")) > 0:
                        element = self.driver.find_element_by_link_text("See more neighborhood details")
                        self.driver.execute_script("arguments[0].scrollIntoView();", element)
                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.LINK_TEXT, "See more neighborhood details")))
                        element.click();
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ws-value")))
                except Exception as e:
                    logger.error(repr(e))
                    pass
                # HERE THE ACTUAL CLASS IS "zsg-table ds-price-and-tax-section-table" BUT I FEEL THAT
                # SELENIUM IS UNABLE TO DETECT BOTH THE CLASSES TOGETHER HENCE WAITING FOR SINGLE CLASS HERE
                html = self.driver.page_source
                soup2 = BeautifulSoup(html, 'lxml')
                self.scrapeForSale(soup2, returndata)
        except TimeoutException as e:
            print("Timeout exception while waiting for element")

            # EXPERIMENTAL CHANGES#
            if retry == 0:
                self.scrapeArticle(result, type, 1)
            else:
                self.driver.quit()
                self.driver = self.setSeleniumDriver()
            # self.scrapeArticle(result, type)
            # EXPERIMENTAL CHANGES
            pass
        except Exception as e:
            # raise e
            print(traceback.format_exc())
            logger.error("exception " + repr(e) + " for url " + houseurl)
            pass

    def find_articles_by_state(self):
        self.find_articles_by_zip("Dallas-TX")

    def handle_fetch_cards_exception(self):
        logger.error("Setting up new proxy for fetching cards...")
        self.cards_proxy = self.rotate_ip()
        print("http://" + self.cards_proxy)
        self.proxyDict = {
            "http": "http://" + self.cards_proxy,
            "https": "http://" + self.cards_proxy
        }

    def find_articles_by_zip(self, zip):
        # get webpage and create soup
        with requests.Session() as s:
            url = "https://www.zillow.com/homes/" + str(
                zip) + "_rb/house,townhouse,condo_type/0_rs/1_fs/1_fr/0_mmm/"
            # url = 'https://www.zillow.com/homes/recently_sold/' + str(zip) + "_rb"
            # https://www.zillow.com/homes/for_sale/20002_rb/house_type/66126_rid/1_fr/1_rs/1_fs/0_mmm/
            # url = 'https://www.zillow.com/homes/for_sale/' + str(zip) + "_rb"
            # r = s.get(url, headers=self.req_headers)
            # self.driver.get("http://www.showmemyip.com/")
            # self.pxy = "183.87.12.209:8080"
            # os.environ['http_proxy'] = self.pxy
            # os.environ['HTTP_PROXY'] = self.pxy
            # os.environ['https_proxy'] = self.pxy
            # os.environ['HTTPS_PROXY'] = self.pxy
            try:
                r = s.get(url, proxies=self.proxyDict, timeout=20.0, headers=self.req_headers)
            except Exception as e:
                print(str(e))
                self.handle_fetch_cards_exception()
                self.find_articles_by_zip(zip)
                return

        # print(r.text)
        soup = BeautifulSoup(r.text, 'lxml')
        if self.check_recaptcha(soup):
            self.handle_fetch_cards_exception()
            self.find_articles_by_zip(zip)
            return
        # print(soup.prettify())

        # print("Current process: " + multiprocessing.current_process().name + " " + returnString(
        #     soup.find("title")))

        # if re.search('\\b0 Homes\\b', returnString(soup.find("title"))) is not None:
        #     return
        if re.search('\\b0\\b', soup.find("meta", {"name": "description"})["content"]) is not None:
            print("no results for zip " + zip)
            return
        # if returnString(soup.find("span", {"class": "result-count"})) == "No Results":
        #     print("no results for "+zip)
        #     return

        # get number of pages
        try:
            pages = returnString(soup.find("li", {"class", "zsg-pagination-next"}).previous_sibling)
        except AttributeError:
            pages = 1

        # itereate over each page
        # for page in range(1, int(pages) + 1):
        page = 1
        while page < int(pages) + 1:
            print("PAGE:" + str(page))

            # make a request for that particular page and create soup for that page
            with requests.Session() as s:
                url = "https://www.zillow.com/homes/" + str(
                    zip) + "_rb/house,townhouse,condo_type/0_rs/1_fs/1_fr/0_mmm/" + str(page) + "_p"
                print(url)
                try:
                    r = s.get(url, proxies=self.proxyDict, timeout=20.0, headers=self.req_headers)
                except Exception as e:
                    print(str(e))
                    self.handle_fetch_cards_exception()
                    continue

            soup = BeautifulSoup(r.content, 'lxml')

            cards = soup.find("ul", {"class": "photo-cards"})
            if cards is None:
                if self.check_recaptcha(soup):
                    self.handle_fetch_cards_exception()
                    continue
                else:
                    page += 1
                    continue

            if cards["class"] == ["photo-cards"]:
                results = cards.find_all("article")
                card_type = 1
            else:
                results = cards.find_all("li", recursive=False)
                card_type = 0

            # find number of articles in that page and iterate over it

            # print(results)
            for result in results:
                try:
                    self.scrapeArticle(result, card_type)
                except Exception as e:
                    # raise e
                    print(traceback.format_exc())
                    logger.error(
                        repr(
                            e) + " exception occoured while handling a zid. Moving to next zid....")
                    continue
            page += 1


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
        time.sleep(5)

    # window = Tk()
    # window.title("Welcome to Zillow Scraper")
    # window.geometry('350x200')
    # lbl = Label(window, text="Enter Zipcode")
    # txt = Entry(window, width=10)
    # txt.grid(column=1, row=0)
    # def clicked():
    #     findLocation2(txt.get())
    #     window.destroy()
    # btn = Button(window, text="Start Scraping",command=clicked)
    # btn.grid(column=1, row=1)
    # lbl.grid(column=0, row=0)
    # window.mainloop()

# zillow url parameters:- /0_mmm - show only for sale items
# https://www.zillow.com/homes/for_sale/Washington-DC-20002/house,apartment_duplex_type/66126_rid/38.953802,-76.915885,38.861765,-77.039481_rect/12_zm/
# 1_fr,1_rs,11_zm
