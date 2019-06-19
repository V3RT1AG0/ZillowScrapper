# Utility file to fetch historical data from mongoDb and dump it intoCSV file
from pymongo import MongoClient
from csv_utils import write_data_to_csv

client = MongoClient('129.174.126.176', 27018)
db = client['Zillow']  # NAME OF DATABASE
collection = db['House']  # NAME OF COLLECTION
print("MongoDB connected...")


# def combineCSV():
#     sell = pd.read_csv("./sell.csv")
#     rent = pd.read_csv("./rent.csv")
#     auction = pd.read_csv("./auction.csv")
#     combined = pd.concat([sell, rent, auction], sort=False)
#     combined = combined.reset_index(drop=True)
#     combined.to_csv("./new5.csv")


def generate_state_and_zip():
    # Run this script to fix incorrect state and zipcodes
    for house in collection.find():
        id = house["_id"]
        address = house["address"].split()
        zip = address[-1]
        state = address[-2]
        if not zip == house["zip"]:
            collection.update_one({
                '_id': id
            }, {
                '$set': {
                    'zip': zip,
                    'state': state
                }
            }, upsert=False)
    print("done")


def genrate_historical_data_for(state):
    # Function to obtain historical data for a state.
    # Output: CSV file with well formated historical data
    for house in collection.find({"state": state}):
        zid = house["zid"]
        zip = house["zip"]
        history = house["SaleHistory"]
        for sale in history:
            data = {}
            data["zip"] = zip
            data["date"] = sale["date"]
            data["price"] = sale["price"]
            data["event"] = sale["event"]
            data["zid"] = zid
            write_data_to_csv("history.csv", data)
    print("done")


generate_state_and_zip()
