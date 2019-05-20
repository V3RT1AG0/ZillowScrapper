from bs4 import BeautifulSoup
import requests
import re
from selenium import webdriver
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tkinter import *
import os
import time

proxy = '5.152.238.9:60826'
key = "X1-ZWz1h1sdyiz9jf_6v82r"


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
        #self.driver.get("https://www.whatismyip.com/my-ip-information/")
        self.findLocation(22030)

    def setHeaders(self):
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.8',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
        }

    def setSeleniumDriver(self):

        options = webdriver.ChromeOptions()
        options.add_argument('--proxy-server=%s' % proxy)
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--incognito')
        # options.add_argument('--headless')
        driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=options)
        return driver

    def scrapeForSold(self, soup2, returndata):
        returndata["cost/rent"] = return_number(soup2.find("div", {"class": "status"}))
        returndata["status"] = "Sold"
        returndata["address"] = returnString(soup2.find("h1", {"class": "zsg-h1"}))
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.find("h3", {"class": "edit-facts-light"}).findAll("span",{"class": False})
        print(bed_bath_area)
        # assigning each value in a list to a its corresponding varaible
        returndata["bed"], returndata["bath"], returndata["area"] = [return_number(span) for span in bed_bath_area]
        returndata["summary"] = returnString(soup2.find("div", {"class": "zsg-content-item home-description"}))
        returndata["zestimate"] = return_number(soup2.find("div", {"class": "zestimate primary-quote"}))
        #returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)

        facts = soup2.find("div", {"class": "home-facts-at-a-glance-section"}).find_all("div")
        for fact in facts:
            label = returnString(fact.find("div", {"class": "fact-label"}))
            value = returnString(fact.find("div", {"class": "fact-value"}))
            returndata[label] = value

        # You might have try catch pass this whole history
        try:
            price_history = soup2.find("table", {"class":"zsg-table zsg-content-component"}).find_all(
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
            print(e)
            pass

        # WRITING TO CSV FILE
        keys = returndata.keys()
        try:
            with open('zillow.csv', 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                writer.writeheader()
                writer.writerow(returndata)
        except IOError:
            print("I/O error")


    def scrapeForSale(self,soup2,returndata):
        returndata["cost/rent"] = returnString(soup2.find("span", {"class": "ds-value"}))
        returndata["status"] = returnString(soup2.find("span", {"class": "ds-status-details"}))
        returndata["address"] = returnString(soup2.find("h1", {"class": "ds-address-container"}))
        # finding all spans which gives bed bath and area
        bed_bath_area = soup2.findAll("span", {"class": "ds-bed-bath-living-area"})
        print(bed_bath_area)
        # assigning each value in a list to a its corresponding varaible
        returndata["bed"], returndata["bath"], returndata["area"] = [return_number(row.span) for row in bed_bath_area][:3]
        returndata["summary"] = returnString(soup2.find("div", {"class": "character-count-text-fold-container"}))
        returndata["zestimate"] = returnString(soup2.find("span", {"class": "ds-estimate-value"}))
        #returndata["Principal/Interest"] = returnString(soup2.find("span", text='Principal & interest').next_sibling)
        facts = soup2.find("ul", {"class": "ds-home-fact-list"}).find_all("li")
        for fact in facts:
            label = returnString(fact.find("span", {"class": "ds-standard-label ds-home-fact-label"}))
            value = returnString(fact.find("span", {"class": "ds-body ds-home-fact-value"}))
            returndata[label] = value

        # You might have try catch pass this whole history
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

        # WRITING TO CSV FILE
        keys = returndata.keys()
        try:
            with open('zillow.csv', 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                writer.writeheader()
                writer.writerow(returndata)
        except IOError:
            print("I/O error")

    def scrapeArticle(self,result):
        returndata = dict()

        # use selenium to load individual house article
        try:
            houseurl = "https://www.zillow.com/homes/for_sale/" + result['data-zpid'] + "_zpid"
            returndata["zipcode"] = result['data-zpid']
        except KeyError as e:
            houseurl = "https://www.zillow.com/homes/for_sale/" + result['id'][5:] + "_zpid"
            returndata["zipcode"] = result['id'][5:]


        self.driver.get(houseurl)
        html = self.driver.page_source
        soup2 = BeautifulSoup(html, 'lxml')
        if soup2.find("span", {"class": "ds-status-details"}) is None:
            WebDriverWait(self.driver, 100).until(
                EC.presence_of_element_located((By.ID, "price-and-tax-history")))
            self.driver.find_element_by_id("price-and-tax-history").click()
            WebDriverWait(self.driver, 100).until(
                EC.presence_of_element_located((By.ID, "hdp-price-history")))  # handle timeoutexceptio 100seconds
            html = self.driver.page_source
            soup2 = BeautifulSoup(html, 'lxml')
            self.scrapeForSold(soup2, returndata)
        else:
            self.scrapeForSale(soup2, returndata)


        #list.append(returndata)
        # self.driver.close()
        # print(list)

    def findLocation(self, zip):
        # get webpage and create soup
        with requests.Session() as s:
            url = 'https://www.zillow.com/homes/recently_sold/' + str(zip) + "_rb"
            #https://www.zillow.com/homes/for_sale/20002_rb/house_type/66126_rid/1_fr/1_rs/1_fs/0_mmm/
            #url = 'https://www.zillow.com/homes/for_sale/' + str(zip) + "_rb"
            r = s.get(url, headers=self.req_headers)
            print(url)
        soup = BeautifulSoup(r.content, 'lxml')
        #list = []

        # get number of pages
        pages = returnString(soup.find("li", {"class", "zsg-pagination-next"}).previous_sibling)

        #itereate over each page
        for page in range(int(pages)):
            print("PAGE:"+str(page))

            #make a request for that particular page and create soup for that page
            with requests.Session() as s:
                url = 'https://www.zillow.com/homes/recently_sold/' + str(zip) + "_rb"
                #url = 'https://www.zillow.com/homes/for_sale/' + str(zip) + "_rb/" + str(page) + "_p"
                r = s.get(url, headers=self.req_headers)
            soup = BeautifulSoup(r.content, 'lxml')
            cards = soup.find("ul", {"class": "photo-cards"})

            #find number of articles in that page and iterate over it
            results = cards.find_all("article")
            for result in results:
                print(result)
                self.scrapeArticle(result)


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
#https://www.zillow.com/homes/for_sale/Washington-DC-20002/house,apartment_duplex_type/66126_rid/38.953802,-76.915885,38.861765,-77.039481_rect/12_zm/
# 1_fr,1_rs,11_zm