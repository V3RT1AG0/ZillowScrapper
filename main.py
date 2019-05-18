from bs4 import BeautifulSoup
import requests
import re
from selenium import webdriver
import csv
from tkinter import *
import os

# proxy = 'http://188.186.186.146:45121'
#
# os.environ['http_proxy'] = proxy
# os.environ['HTTP_PROXY'] = proxy
# os.environ['https_proxy'] = proxy
# os.environ['HTTPS_PROXY'] = proxy

key = "X1-ZWz1h1sdyiz9jf_6v82r"




def returnString(data):
    if data is None:
        return ""
    else:
        return data.get_text().strip()


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
    print(soup)
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
    # soup3 = BeautifulSoup(r.text, "html.parser")
    # sales = soup3.find_all("tr", {"class": "zsg-table_interactive"})
    # print(sales)

    # tr in soup.find_all('tr'):
    #     data.append([td.text for td in tr.find_all('td')])
    #
    # for row in data[:5]:  # Show first 5 entries
    #     print
    #     row
    print(returndata)


def findLocation(location,state):
    location_url = "http://www.zillow.com/webservice/GetDeepSearchResults.htm?zws-id=" + key + "&address=" + location + "&citystatezip=" + state
    s = requests.Session()
    s.headers[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
    base = s.get(location_url, verify=False)
    soup = BeautifulSoup(base.text, "lxml")
    results = soup.find_all("result")
    for result in results:
        print(crawl(returnString(result.find('zpid'))))


def findLocation2(zip):
    req_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }

    with requests.Session() as s:
        url = 'https://www.zillow.com/homes/for_sale/' + str(zip)
        r = s.get(url, headers=req_headers)
    soup = BeautifulSoup(r.content, 'lxml')
    cards = soup.find("ul", {"class": "photo-cards"})
    results = cards.find_all("article")
    list = []
    for result in results:
        print(result)
        returndata = dict()
        try:
            houseurl = "https://www.zillow.com/homes/for_sale/" + result['data-zpid'] + "_zpid"
        except KeyError as e:
            houseurl = "https://www.zillow.com/homes/for_sale/" + result['id'][5:] + "_zpid"
        # h = s.get(houseurl, headers=req_headers)
        #*****************************
        driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver')
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--incognito')
        options.add_argument('--headless')
        # driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver", chrome_options=options)
        h = driver.get(houseurl)
        html = driver.page_source
        #*************************************
        soup2 = BeautifulSoup(html, 'lxml')
        returndata["cost"] = returnString(soup2.find("span", {"class": "ds-value"}))
        returndata["address"]= returnString(soup2.find("h1", {"class": "ds-address-container"}))
        returndata["summary"] = returnString(soup2.find("div", {"class": "character-count-text-fold-container"}))
        returndata["zestimate"] = returnString(soup2.find("span", {"class": "ds-estimate-value"}))
        facts = soup2.find("ul", {"class": "ds-home-fact-list"}).find_all("li")
        for fact in facts:
            label = returnString(fact.find("span", {"class": "ds-standard-label ds-home-fact-label"}))
            value = returnString(fact.find("span", {"class": "ds-body ds-home-fact-value"}))
            returndata[label] = value
        print(soup2)
        price_history = soup2.find("table", {"class":"zsg-table ds-price-and-tax-section-table"}).find_all("tr")
        print(price_history)
        historyList = []
        for hs in price_history[1:]:
            hist = dict()
            items = hs.contents
            hist["date"] = returnString(items[0])
            hist["event"] = returnString(items[1])
            hist["price"] = returnString(items[2])
            historyList.append(hist)
        returndata["SaleHistory"] = historyList


        #WRITING TO CSV FILE
        keys = returndata.keys()
        try:
            with open('zillow.csv', 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                #writer.writeheader()
                writer.writerow(returndata)
        except IOError:
            print("I/O error")
        list.append(returndata)
        driver.close()
        print(list)
    print(list)





#CODE TO FETCH DATA USING API INSTEAD OF SCRAPING IT FROM WEBSITE
#findLocation("Richmond","Richmond%2C+VA")
#findLocation("Fairfax","Fairfax%2C+VA")


if __name__ == "__main__":
    window = Tk()
    window.title("Welcome to Zillow Scraper")
    window.geometry('350x200')
    lbl = Label(window, text="Enter Zipcode")
    txt = Entry(window, width=10)
    txt.grid(column=1, row=0)
    def clicked():
        findLocation2(txt.get())
        window.destroy()
    btn = Button(window, text="Start Scraping",command=clicked)
    btn.grid(column=1, row=1)
    lbl.grid(column=0, row=0)
    window.mainloop()

#HOW TO RUN THIS FILE:
#1. INSTALL CHROMEDRIVER Version 74.0. AND SET EXECUTABLE PATH IN THIS CODE TO POINT THAT CHROMEDRIVER
#2. INSTALL ALL DEPENDENCIES USING THE FOLLOWING COMMAND: pip install -r requirements.txt
#3. SIMPLY RUN THE PYTHON PROGRAM IN THE VIRTUAL ENVIORNMENT PROVIDED i.e "venv"
#4. ENTER THE ZIPCODE FOR WHICH YOU WANT TO FETCH THE DATA FOR IN THE PROGRAM RUNNING
#5. THE DATA WILL BE COLLECTED IN A FILE "zillow.csv".