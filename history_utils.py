# Utility file to fetch historical data from mongoDb and dump it intoCSV file
import re
import logging
import csv
from db import get_collection

logger = logging.getLogger("Utlis Logger:")

# client = MongoClient('129.174.126.176', 27018)
# db = client['Zillow']  # NAME OF DATABASE
# get_collection() = db['House']  # NAME OF get_collection()
# print("MongoDB connected...")


# def combineCSV():
#     sell = pd.read_csv("./sell.csv")
#     rent = pd.read_csv("./rent.csv")
#     auction = pd.read_csv("./auction.csv")
#     combined = pd.concat([sell, rent, auction], sort=False)
#     combined = combined.reset_index(drop=True)
#     combined.to_csv("./new5.csv")
def get_number_from_string(string):
    if string is None or not string or string == 'No Data':
        return None
    result = re.sub('[^0-9]', '', string)
    result = int(result)
    return result


def cleanDollarSignAndCreateLocality():
    # Run this script to remove dollar sign from price and price_persquare and create locality from address
    for house in get_collection().find(no_cursor_timeout=True):
        try:
            id = house["_id"]
            if type(house.get("Price")) is int:
                    continue
            new_price = get_number_from_string(house.get("Price"))
            new_price_sqft = get_number_from_string(house.get("Price_PerSQFT"))
            address = house["Address"].split(",")
            locality = address[-2].strip()
            get_collection().update_one({
                '_id': id
            }, {
                '$set': {
                    'locality': locality,
                    'Price': new_price,
                    'Price_PerSQFT': new_price_sqft
                }
            }, upsert=False)
            # print(new_price_sqft, locality, new_price)
        except Exception as e:
            logger.error(repr(e))
            continue
    print("done")


def generate_state_and_zip():
    # Run this script to fix incorrect state and zipcodes
    for house in get_collection().find():
        id = house["_id"]
        address = house["Address"].split()
        zip = address[-1]
        state = address[-2]
        if "ZipCode" not in house or not zip == house["ZipCode"]:
            get_collection().update_one({
                '_id': id
            }, {
                '$set': {
                    'ZipCode': zip,
                    'State': state
                }
            }, upsert=False)
    print("done")


def genrate_historical_data_for(state):
    # Function to obtain historical data for a state.
    # Output: CSV file with well formated historical data
    arrayData = []
    for house in get_collection().find({"State": state}):
        zid = house["zid"]
        zip = house["ZipCode"]
        history = house["SaleHistory"]
        for sale in history:
            data = {}
            data["ZipCode"] = zip
            data["date"] = sale["date"]
            data["price"] = sale["price"]
            data["event"] = sale["event"]
            data["zid"] = zid
            arrayData.append(data)
    write_data_to_csv(state + "_history.csv", arrayData)
    print("done")

def write_data_to_csv(filename,data):
    keys = data[0].keys()
    try:
        with open(filename, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
    except IOError:
        print("I/O error")


#generate_state_and_zip()
