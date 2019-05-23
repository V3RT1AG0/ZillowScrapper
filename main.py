from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import csv
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tkinter import *
from db import insert_article
import json
import os
import time
from csv_utils import write_to_csv

proxyKey = 'XZApcdn3rvxztE9KQeuJgLyomYw7V5DT'
key = "X1-ZWz1h1sdyiz9jf_6v82r"
logger = logging.getLogger("Zillow Logger:")


def returnString(data):
    if data is None:
        return ""
    else:
        return data.get_text().strip()


def return_number(data):
    if data is None:
        return ""
    else:
        return re.sub('[^0-9]', '', returnString(data))


# Api call
def crawl(zpid):
    print(zpid)
    returndata = dict()
    base_url = 'http://www.zillow.com/webservice/GetUpdatedPropertyDetails.htm?zws-id=' + key + '&zpid=' + str(
        zpid)
    estimate_url = 'http://www.zillow.com/webservice/GetZestimate.htm?zws-id=' + key + '&zpid=' + str(
        zpid)
    s = requests.Session()
    s.headers[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
    try:
        base = s.get(base_url, verify=False)
        est = s.get(estimate_url, verify=False)
    except requests.exceptions.TooManyRedirects as e:
        return False
    soup = BeautifulSoup(base.text, "lxml")
    # print(soup)
    if (soup.find('address') == None):
        return None
    address = soup.find('address').contents
    returndata["address"] = returnString(address[0])
    returndata["zip"] = returnString(address[1])
    returndata["city"] = returnString(address[2])
    returndata["state"] = returnString(address[3])
    # returndata["price"] = returnString(soup.find('price'))
    returndata["desc"] = returnString(soup.find('homedescription'))
    returndata["bedreoom"] = returnString(soup.find('bedrooms'))
    returndata["bathroom"] = returnString(soup.find('bathrooms'))
    returndata["yearBuilt"] = returnString(soup.find('yearbuilt'))
    returndata["lotSize"] = returnString(soup.find('lotSizesqft'))
    returndata["parking"] = returnString(soup.find('parkingtype'))
    returndata["heatingSystem"] = returnString(soup.find('heatingsystem'))
    try:
        soup2 = BeautifulSoup(est.text, "lxml")
        estimate = soup2.find('zestimate').contents
        returndata["amount"] = returnString(estimate[0])
        returndata["valuechange"] = returnString(estimate[3])
        returndata["percentile"] = returnString(estimate[5])
    except:
        print("no zestimate")
    keys = returndata.keys()
    try:
        with open('zillow1.csv', 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            # writer.writeheader()
            writer.writerow(returndata)
    except IOError:
        print("I/O error")
    print(returndata)


def findLocation(location, state):
    location_url = "http://www.zillow.com/webservice/GetDeepSearchResults.htm?zws-id=" + key + "&address=" + location + "&citystatezip=" + state
    s = requests.Session()
    s.headers[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
    base = s.get(location_url, verify=False)
    soup = BeautifulSoup(base.text, "lxml")
    results = soup.find_all("result")
    for result in results:
        print(crawl(returnString(result.find('zpid'))))


class App:

    def __init__(self):
        self.req_headers = self.setHeaders()
        self.driver = self.setSeleniumDriver()
        # self.driver.get("https://www.whatismyip.com/my-ip-information/")
        for zipcode in self.get_zip_codes():
            self.current_zipcode = zipcode
            self.find_articles_by_zip(zipcode)
        #self.find_articles_by_state


    def get_zip_codes(self):
        zipcodes = ["75206","75205","75228"]
        return zipcodes

    def check_recaptcha(self, soup):
        captcha = soup.find("div",{"class":"g-recaptcha"})
        if captcha is None:
            return False
        else:
            print("Bot detected..")
            return True

    def rotate_ip(self):
        proxyRotatorUrl = "http://falcon.proxyrotator.com:51337/?apiKey=" + proxyKey + "&get=true"
        json_response = requests.get(proxyRotatorUrl).json()
        proxy = json_response["proxy"]
        print("Rotating IP...new proxy="+proxy)
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
        #options.addExtensions(new File("C:\\whatever\\Block-image_v1.0.crx"))
        options.add_argument('--proxy-server=%s' % proxy)
        options.add_argument("accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--incognito")
        #options.add_argument('--headless')
        options.add_experimental_option("prefs",{"profile.managed_default_content_settings.images": 2})#'disk-cache-size': 4096
        #TODO zipcode and abouve optimization and that error in bottom
        driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=options)
        driver.set_page_load_timeout(20)
        return driver

    def scrapeForSold(self, soup2, returndata):
        returndata["cost/rent"] = return_number(soup2.find("div", {"class": "status"}))
        returndata["status"] = "Sold"
        returndata["address"] = returnString(soup2.find("h1", {"class": "zsg-h1"}))
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.find("h3", {"class": "edit-facts-light"}).findAll("span", {"class": False})

        # assigning each value in a list to a its corresponding varaible
        returndata["bed"], returndata["bath"], returndata["area"] = [return_number(span) for span in bed_bath_area]

        #returndata["summary"] = returnString(soup2.find("div", {"class": "zsg-content-item home-description"}))
        returndata["zestimate"] = return_number(soup2.find("div", {"class": "zestimate primary-quote"}))
        # returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)

        facts = soup2.find("div", {"class": "home-facts-at-a-glance-section"}).find_all("div")
        for fact in facts:
            label = returnString(fact.find("div", {"class": "fact-label"}))
            value = returnString(fact.find("div", {"class": "fact-value"}))
            returndata[label] = value

        # GET HISTORICAL DATA
        try:
            price_history = soup2.find("table", {"class": "zsg-table zsg-content-component"}).find_all(
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
        write_to_csv(returndata)


    def scrapeForSale(self, soup2, returndata):
        returndata["cost/rent"] = returnString(soup2.find("span", {"class": "ds-value"}))
        returndata["status"] = returnString(soup2.find("span", {"class": "ds-status-details"}))
        returndata["address"] = returnString(soup2.find("h1", {"class": "ds-address-container"}))
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.findAll("span", {"class": "ds-bed-bath-living-area"})
        #print(bed_bath_area)
        # assigning each value in a list to a its corresponding varaible
        returndata["bed"], returndata["bath"], returndata["area"] = [return_number(row.span) for row in bed_bath_area][
                                                                    :3]
        #returndata["summary"] = returnString(soup2.find("div", {"class": "character-count-text-fold-container"}))
        #returndata["zestimate"] = return_number(soup2.find("h4", {"class": "zestimate-value"}))
        returndata["zestimate"] = return_number(soup2.find("span", {"class": "ds-estimate-value"}))

        # returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)
        facts = soup2.find("ul", {"class": "ds-home-fact-list"}).find_all("li")
        for fact in facts:
            label = returnString(fact.find("span", {"class": "ds-standard-label ds-home-fact-label"}))
            value = returnString(fact.find("span", {"class": "ds-body ds-home-fact-value"}))
            returndata[label] = value


        # SAVE HISTORICAL DATA
        try:
            price_history = soup2.find("table", {"class": "zsg-table ds-price-and-tax-section-table"}).find_all(
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
            logger.error("exception " + repr(e) + "in scrape for history for sale/rent ")
            returndata["SaleHistory"] = ""
            pass

        # WRITING TO CSV FILE
        write_to_csv(returndata)



    def scrapeArticle(self, result,type):
        returndata = dict()

        # use selenium to load individual house article
        #print(str(type))
        returndata["zip"] = self.current_zipcode
        if type==1:
            try:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result['data-zpid'] + "_zpid"
                returndata["zid"] = result['data-zpid']
            except KeyError as e:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result['id'][5:] + "_zpid"
                returndata["zid"] = result['id'][5:]
            except Exception as e:
                logger.error("exception " + repr(e) + " on line 248")
                return
            returndata["latitude"] = result["data-latitude"]
            returndata["longitude"] = result["data-longitude"]
        else:
            print(result)
            print(result.article)
            try:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result.article['data-zpid'] + "_zpid"
                returndata["zid"] = result.article['data-zpid']
            except KeyError as e:
                houseurl = "https://www.zillow.com/homes/for_sale/" + result.article['id'][5:] + "_zpid"
                returndata["zid"] = result.article['id'][5:]
            except Exception as e:
                logger.error("exception " + repr(e) + " on line 257")
                return
            returndata["latitude"] = json.loads(returnString(result.script))['geo']['latitude']
            returndata["longitude"] = json.loads(returnString(result.script))['geo']['longitude']


        try:
            self.driver.get(houseurl)
        except TimeoutException:
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            self.scrapeArticle(result,type)
            return

        html = self.driver.page_source
        soup2 = BeautifulSoup(html, 'lxml')

        # restart scraping for same article if captcha or error deteted
        if self.check_recaptcha(soup2) or soup2.find("div",{"id":"main-frame-error"}) is not None:
            self.driver.quit()
            self.driver = self.setSeleniumDriver()
            self.scrapeArticle(result,type)
            return


        try:
            if soup2.find("span", {"class": "ds-status-details"}) is None:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "price-and-tax-history")))
                self.driver.find_element_by_id("price-and-tax-history").click()
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "hdp-price-history")))  # handle timeoutexceptio 100seconds
                html = self.driver.page_source
                soup2 = BeautifulSoup(html, 'lxml')
                self.scrapeForSold(soup2, returndata)
            else:
                WebDriverWait(self.driver, 20).until(
                     EC.presence_of_element_located((By.CLASS_NAME, "ds-value")))
                self.scrapeForSale(soup2, returndata)
        except Exception as e:
            logger.error("exception "+repr(e)+" for url "+houseurl)
            pass

        # list.append(returndata)
        # self.driver.close()
        # print(list)

    def find_articles_by_state(self):
        self.find_articles_by_zip("Dallas-TX")

    def find_articles_by_zip(self, zip):

        # get webpage and create soup
        with requests.Session() as s:
            url = "https://www.zillow.com/homes/"+str(zip)+"_rb/house_type/0_rs/1_fs/1_fr/0_mmm/"
            #url = 'https://www.zillow.com/homes/recently_sold/' + str(zip) + "_rb"
            # https://www.zillow.com/homes/for_sale/20002_rb/house_type/66126_rid/1_fr/1_rs/1_fs/0_mmm/
            # url = 'https://www.zillow.com/homes/for_sale/' + str(zip) + "_rb"
            r = s.get(url, headers=self.req_headers)

        soup = BeautifulSoup(r.content, 'lxml')

        # get number of pages
        try:
            pages = returnString(soup.find("li", {"class", "zsg-pagination-next"}).previous_sibling)
        except AttributeError:
            pages = 1

        # itereate over each page
        for page in range(1, int(pages)+1):
            print("PAGE:" + str(page))

            # make a request for that particular page and create soup for that page
            with requests.Session() as s:
                url = "https://www.zillow.com/homes/" + str(zip) + "_rb/house_type/0_rs/1_fs/1_fr/0_mmm/"+str(page) + "_p"
                print(url)
                r = s.get(url, headers=self.req_headers)
            soup = BeautifulSoup(r.content, 'lxml')

            cards = soup.find("ul", {"class": "photo-cards"})
            #print(cards["class"])
            if cards["class"]==["photo-cards"]:
                results = cards.find_all("article")
                card_type = 1
            else:
                results = cards.find_all("li",recursive=False)
                card_type = 0

            # find number of articles in that page and iterate over it

            #print(results)
            for result in results:
                self.scrapeArticle(result,card_type)


# CODE TO FETCH DATA USING API INSTEAD OF SCRAPING IT FROM WEBSITE
# findLocation("Richmond","Richmond%2C+VA")
# findLocation("Fairfax","Fairfax%2C+VA")


if __name__ == "__main__":
    app = App()
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

# HOW TO RUN THIS FILE:
# 1. INSTALL CHROMEDRIVER Version 74.0. AND SET EXECUTABLE PATH IN THIS CODE TO POINT THAT CHROMEDRIVER
# 2. INSTALL ALL DEPENDENCIES USING THE FOLLOWING COMMAND: pip install -r requirements.txt
# 3. SIMPLY RUN THE PYTHON PROGRAM IN THE VIRTUAL ENVIORNMENT PROVIDED i.e "venv"
# 4. ENTER THE ZIPCODE FOR WHICH YOU WANT TO FETCH THE DATA FOR IN THE PROGRAM RUNNING
# 5. THE DATA WILL BE COLLECTED IN A FILE "zillow.csv".

# zillow url parameters:- /0_mmm - show only for sale items
# https://www.zillow.com/homes/for_sale/Washington-DC-20002/house,apartment_duplex_type/66126_rid/38.953802,-76.915885,38.861765,-77.039481_rect/12_zm/
# 1_fr,1_rs,11_zm



# PAGE:1
# [<article class="list-card list-card_not-saved" data-index="0" id="zpid_414258" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">837 3rd St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,800/mo</div><ul class="list-card-details"><li>3<span class="list-card-label"> <!-- -->bds</span></li><li>2<span class="list-card-label"> <!-- -->ba</span></li><li>1,600<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">1 hour ago</div><div></div><div class="list-card-img"><img alt="837 3rd St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/ISe0l8lvloro7h1000000000.jpg"/></div></div><a aria-label="House for rent, 837 3rd St NE, Washington, DC, $3,800/mo" class="list-card-link" href="https://www.zillow.com/homedetails/837-3rd-St-NE-Washington-DC-20002/414258_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="1" id="zpid_501231" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1011 16th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$1,200/mo</div><ul class="list-card-details"><li>1<span class="list-card-label"> <!-- -->bd</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>2,640<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">3 hours ago</div><div></div><div class="list-card-img"><img alt="1011 16th St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/IS6645p8kx364a1000000000.jpg"/></div></div><a aria-label="House for rent, 1011 16th St NE, Washington, DC, $1,200/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1011-16th-St-NE-Washington-DC-20002/501231_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="2" id="zpid_501072" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1109 Montello Ave NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,500/mo</div><ul class="list-card-details"><li>3<span class="list-card-label"> <!-- -->bds</span></li><li>1.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,567<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">3 hours ago</div><div></div><div class="list-card-img"><img alt="1109 Montello Ave NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/ISesylebs3ox370000000000.jpg"/></div></div><a aria-label="House for rent, 1109 Montello Ave NE, Washington, DC, $3,500/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1109-Montello-Ave-NE-Washington-DC-20002/501072_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="3" id="zpid_71720748" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">647 16th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$4,753/mo</div><ul class="list-card-details"><li>4<span class="list-card-label"> <!-- -->bds</span></li><li>2.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,623<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">23 hours ago</div><div></div><div class="list-card-img"></div></div><a aria-label="House for rent, 647 16th St NE, Washington, DC, $4,753/mo" class="list-card-link" href="https://www.zillow.com/homedetails/647-16th-St-NE-Washington-DC-20002/71720748_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="4" id="zpid_416083" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">730 6th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,600/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>2.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,600<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">1 day ago</div><div></div><div class="list-card-img"><img alt="730 6th St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/ISewp9is9t97m81000000000.jpg"/></div></div><a aria-label="House for rent, 730 6th St NE, Washington, DC, $3,600/mo" class="list-card-link" href="https://www.zillow.com/homedetails/730-6th-St-NE-Washington-DC-20002/416083_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="5" id="zpid_2089865271" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1211 1/2 D St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$2,400/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>900<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">3 days ago</div><div></div><div class="list-card-img"><img alt="1211 1/2 D St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/ISe44iwqxj285h1000000000.jpg"/></div></div><a aria-label="House for rent, 1211 1/2 D St NE, Washington, DC, $2,400/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1211-1-2-D-St-NE-Washington-DC-20002/2089865271_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="6" id="zpid_2084399666" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">Warren St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$2,550/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>850<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">3 days ago</div><div></div><div class="list-card-img"><img alt="Warren St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/ISmy8kbi2i9ui60000000000.jpg"/></div></div><a aria-label="House for rent, Warren St NE, Washington, DC, $2,550/mo" class="list-card-link" href="https://www.zillow.com/homedetails/Warren-St-NE-Washington-DC-20002/2084399666_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="7" id="zpid_419506" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">912 K St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,600/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,140<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">3 days ago</div><div></div><div class="list-card-img"><img alt="912 K St NE, Washington, DC" src="https://photos.zillowstatic.com/p_e/IS2jndlcmsak951000000000.jpg"/></div></div><a aria-label="House for rent, 912 K St NE, Washington, DC, $3,600/mo" class="list-card-link" href="https://www.zillow.com/homedetails/912-K-St-NE-Washington-DC-20002/419506_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="8" id="zpid_415961" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">515 M St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-sale"></span>House for sale</div><div class="list-card-heading"><div class="list-card-price">$799,000</div><ul class="list-card-details"><li>3<span class="list-card-label"> <!-- -->bds</span></li><li>2<span class="list-card-label"> <!-- -->ba</span></li><li>1,024<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">4 days ago</div><div></div><div class="list-card-img"></div></div><a aria-label="House for sale, 515 M St NE, Washington, DC, $799,000" class="list-card-link" href="https://www.zillow.com/homedetails/515-M-St-NE-Washington-DC-20002/415961_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="9" id="zpid_422408" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">116 Tennessee Ave NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$4,000/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>2.5<span class="list-card-label"> <!-- -->ba</span></li><li>2,000<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">5 days ago</div><div></div><div class="list-card-img"><img alt="116 Tennessee Ave NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 116 Tennessee Ave NE, Washington, DC, $4,000/mo" class="list-card-link" href="https://www.zillow.com/homedetails/116-Tennessee-Ave-NE-Washington-DC-20002/422408_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="10" id="zpid_423014" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1341 I St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$4,500/mo</div><ul class="list-card-details"><li>5<span class="list-card-label"> <!-- -->bds</span></li><li>2.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,823<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">6 days ago</div><div></div><div class="list-card-img"><img alt="1341 I St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1341 I St NE, Washington, DC, $4,500/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1341-I-St-NE-Washington-DC-20002/423014_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="11" id="zpid_507882" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1636 Rosedale St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,500/mo</div><ul class="list-card-details"><li>3<span class="list-card-label"> <!-- -->bds</span></li><li>3.5<span class="list-card-label"> <!-- -->ba</span></li><li>2,200<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">10 days ago</div><div></div><div class="list-card-img"><img alt="1636 Rosedale St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1636 Rosedale St NE, Washington, DC, $3,500/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1636-Rosedale-St-NE-Washington-DC-20002/507882_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="12" id="zpid_500084" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1213 Queen St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$2,300/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>800<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">10 days ago</div><div></div><div class="list-card-img"><img alt="1213 Queen St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1213 Queen St NE, Washington, DC, $2,300/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1213-Queen-St-NE-Washington-DC-20002/500084_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="13" id="zpid_421079" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1101 Florida Ave NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-sale"></span>New construction</div><div class="list-card-heading"><div class="list-card-price">$2,800,000</div><ul class="list-card-details"><li>10<span class="list-card-label"> <!-- -->bds</span></li><li>10<span class="list-card-label"> <!-- -->ba</span></li><li>4,150<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">10 days ago</div><div></div><div class="list-card-img"><img alt="1101 Florida Ave NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="New construction, 1101 Florida Ave NE, Washington, DC, $2,800,000" class="list-card-link" href="https://www.zillow.com/homedetails/1101-Florida-Ave-NE-Washington-DC-20002/421079_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="14" id="zpid_295436064" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1214 Meigs Pl NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-sale"></span>Auction</div><div class="list-card-heading"><div class="list-card-price">$588K</div><ul class="list-card-details"><li>4<span class="list-card-label"> <!-- -->bds</span></li><li>--<span class="list-card-label"> <!-- -->ba</span></li><li>3,278<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">12 days ago</div><div></div><div class="list-card-img"><img alt="1214 Meigs Pl NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="Auction, 1214 Meigs Pl NE, Washington, DC, $588K" class="list-card-link" href="https://www.zillow.com/homedetails/1214-Meigs-Pl-NE-Washington-DC-20002/295436064_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="15" id="zpid_500846" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1228 Montello Ave NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$2,450/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>913<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">13 days ago</div><div></div><div class="list-card-img"><img alt="1228 Montello Ave NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1228 Montello Ave NE, Washington, DC, $2,450/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1228-Montello-Ave-NE-Washington-DC-20002/500846_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="16" id="zpid_421372" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">209 11th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$4,495/mo</div><ul class="list-card-details"><li>4<span class="list-card-label"> <!-- -->bds</span></li><li>3<span class="list-card-label"> <!-- -->ba</span></li><li>3,000<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">15 days ago</div><div></div><div class="list-card-img"><img alt="209 11th St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 209 11th St NE, Washington, DC, $4,495/mo" class="list-card-link" href="https://www.zillow.com/homedetails/209-11th-St-NE-Washington-DC-20002/421372_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="17" id="zpid_499749" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1308 Gallaudet St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$1,485/mo</div><ul class="list-card-details"><li>1<span class="list-card-label"> <!-- -->bd</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>600<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">17 days ago</div><div></div><div class="list-card-img"><img alt="1308 Gallaudet St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1308 Gallaudet St NE, Washington, DC, $1,485/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1308-Gallaudet-St-NE-Washington-DC-20002/499749_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="18" id="zpid_420360" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">738 11th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-sale"></span>House for sale</div><div class="list-card-heading"><div class="list-card-price">$1,350,000</div><ul class="list-card-details"><li>Studio</li><li>--<span class="list-card-label"> <!-- -->ba</span></li><li>2,196<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">18 days ago</div><div><div class="list-card-brokerage list-card-img-overlay">CENTURY 21 New Millennium<div> <!-- -->(202) 546-0055</div></div></div><div class="list-card-img"><img alt="738 11th St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for sale, 738 11th St NE, Washington, DC, $1,350,000" class="list-card-link" href="https://www.zillow.com/homedetails/738-11th-St-NE-Washington-DC-20002/420360_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="19" id="zpid_423589" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1359 C St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$2,000/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1.5<span class="list-card-label"> <!-- -->ba</span></li><li>768<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">20 days ago</div><div></div><div class="list-card-img"><img alt="1359 C St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1359 C St NE, Washington, DC, $2,000/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1359-C-St-NE-Washington-DC-20002/423589_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="20" id="zpid_295436049" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1238 Simms Pl NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$1,340/mo</div><ul class="list-card-details"><li>1<span class="list-card-label"> <!-- -->bd</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>500<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">22 days ago</div><div></div><div class="list-card-img"><img alt="1238 Simms Pl NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 1238 Simms Pl NE, Washington, DC, $1,340/mo" class="list-card-link" href="https://www.zillow.com/homedetails/1238-Simms-Pl-NE-Washington-DC-20002/295436049_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="21" id="zpid_415520" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">418 D St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$4,950/mo</div><ul class="list-card-details"><li>3<span class="list-card-label"> <!-- -->bds</span></li><li>2.5<span class="list-card-label"> <!-- -->ba</span></li><li>1,800<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">25 days ago</div><div></div><div class="list-card-img"><img alt="418 D St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 418 D St NE, Washington, DC, $4,950/mo" class="list-card-link" href="https://www.zillow.com/homedetails/418-D-St-NE-Washington-DC-20002/415520_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="22" id="zpid_2084791302" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">1038 6th St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-sale"></span>Auction</div><div class="list-card-heading"><div class="list-card-price">$694K</div><ul class="list-card-details"><li>--<span class="list-card-label"> <!-- -->bds</span></li><li>--<span class="list-card-label"> <!-- -->ba</span></li><li>--<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">26 days ago</div><div></div><div class="list-card-img"><img alt="1038 6th St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="Auction, 1038 6th St NE, Washington, DC, $694K" class="list-card-link" href="https://www.zillow.com/homedetails/1038-6th-St-NE-Washington-DC-20002/2084791302_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>, <article class="list-card list-card_not-saved" data-index="23" id="zpid_418836" role="presentation"><div class="list-card-info"><h3 class="list-card-addr">823 L St NE, Washington, DC</h3><div class="list-card-type"><span class="list-card-type-icon zsg-icon-for-rent"></span>House for rent</div><div class="list-card-heading"><div class="list-card-price">$3,000/mo</div><ul class="list-card-details"><li>2<span class="list-card-label"> <!-- -->bds</span></li><li>1<span class="list-card-label"> <!-- -->ba</span></li><li>792<span class="list-card-label"> <!-- -->sqft</span></li></ul></div></div><div class="list-card-top"><div class="list-card-variable-text list-card-img-overlay">27 days ago</div><div></div><div class="list-card-img"><img alt="823 L St NE, Washington, DC" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"/></div></div><a aria-label="House for rent, 823 L St NE, Washington, DC, $3,000/mo" class="list-card-link" href="https://www.zillow.com/homedetails/823-L-St-NE-Washington-DC-20002/418836_zpid/"></a><button aria-label="Save" class="list-card-save" type="button"><span class="list-card-save-content" tabindex="-1"><svg aria-label="Heart icon" height="34" viewbox="0 0 31 31" width="34" xmlns="http://www.w3.org/2000/svg"><title>Heart icon</title><path d="M18.5,0.00109769484 C22.0897727,0.00109769484 25,2.81119649 25,6.27991218 C25,8.06147091 24.2318182,9.66630077 22.9977273,10.8100988 L12.5,21 L1.8125,10.6256861 C0.690909091,9.49725576 0,7.96706915 0,6.27881449 C0,2.81119649 2.91022727,3.19744231e-14 6.5,3.19744231e-14 C9.20227273,3.19744231e-14 11.5193182,1.5949506 12.5,3.86388584 C13.4795455,1.5949506 15.7965909,0.00109769484 18.5,0.00109769484 L18.5,0.00109769484 Z" fill="#000" fill-opacity="0.2" stroke="#FFF" stroke-width="2" transform="translate(3 3)"></path></svg></span></button></article>]
# exception 'NoneType' object has no attribute 'find_all' for urlhttps://www.zillow.com/homes/for_sale/414258_zpid
# exception 'NoneType' object has no attribute 'find_all' for urlhttps://www.zillow.com/homes/for_sale/501231_zpid
# exception 'NoneType' object has no attribute 'find_all' for urlhttps://www.zillow.com/homes/for_sale/501072_zpid
# exception 'NoneType' object has no attribute 'find_all' for urlhttps://www.zillow.com/homes/for_sale/71720748_zpid