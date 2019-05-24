from bs4 import BeautifulSoup
import requests
import csv
key = "X1-ZWz1h1sdyiz9jf_6v82r"


def returnString(data):
    if data is None:
        return ""
    else:
        return data.get_text().strip()
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


# CODE TO FETCH DATA USING API INSTEAD OF SCRAPING IT FROM WEBSITE
# findLocation("Richmond","Richmond%2C+VA")
# findLocation("Fairfax","Fairfax%2C+VA")