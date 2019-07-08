import pandas as pd
import csv
import json
from history_utils import genrate_historical_data_for
from db import get_collection


def combineCSV():
    sell = pd.read_csv("./sell.csv")
    rent = pd.read_csv("./rent.csv")
    auction = pd.read_csv("./auction.csv")
    combined = pd.concat([sell, rent, auction], sort=False)
    combined = combined.reset_index(drop=True)
    combined.to_csv("./new5.csv")


def read_ZipCodesFoState(state):
    data = pd.read_csv("./All_Zip.csv")
    zip_list = data[data.state == state]["zip"].tolist()
    if len(zip_list) == 0:
        raise ValueError("Invalid state code")
    else:
        return zip_list


def read_visited_zipCode(state):
    with open('visited_zip.json') as json_file:
        data = json.load(json_file)
        try:
            return data[state]
        except KeyError:
            return []


def write_visited_zip_code(state, zipCode):
    with open('visited_zip.json') as json_file:
        data = json.load(json_file)

    try:
        data[state].append(zipCode)
    except KeyError:
        data[state] = [zipCode]

    with open('visited_zip.json', 'w') as outfile:
        json.dump(data, outfile)


def get_unvisited_zip(state):
    all = read_ZipCodesFoState(state)
    visited = read_visited_zipCode(state)
    unvisited = [zip for zip in all if zip not in visited]
    return unvisited


def write_to_csv(data):
    print(data)

    status = data["Status"]
    if status == "House for rent":
        filename = "rent.csv"
    elif status == "Sold":
        filename = "sold.csv"
    elif status == "For sale":
        filename = "sell.csv"
    else:
        filename = "auction.csv"
    write_data_to_csv(filename, data)


def remove_zip_code(state, zipCode):
    with open('visited_zip.json') as json_file:
        data = json.load(json_file)

    try:
        data[state].remove(zipCode)
    except Exception as e:
        print("Unable to remove zip" + zipCode)
        return

    with open('visited_zip.json', 'w') as outfile:
        json.dump(data, outfile)


def write_data_to_csv(filename, data):
    keys = data.keys()
    try:
        with open(filename, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            # writer.writeheader()
            writer.writerows(data)
    except IOError:
        print("I/O error")


def write_multi_data_to_csv(filename, data):
    try:
        with open(filename, 'a') as csvfile:
            fieldnames = ["_id", "State", "Status", "Type", "location", "zid", "Address", "Price",
                          "Price_PerSQFT", "AreaSpace_SQFT", "ZipCode", "ZestimatePrice",
                          "YearBuilt",
                          "Bathrooms", "Bedrooms",
                          "Cooling",
                          "Date_available", "Deposit_fees", "HOAFee", "Heating", "Latitude",
                          "Laundry", "Longitude", "Locality", "Lot", "Parking", "Pets",
                          "SaleHistory", "Saves", "DaysOnZillow", '']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except IOError:
        print("I/O error")


def remove_fields_with_value(column, value):
    # remove fields from history csv with specific column and value
    # Eg:- remove_fields_with_value("status","Listed for rent")
    df = pd.read_csv("./history-1.csv")
    df = df[df[column] != value]
    df.to_csv("./history2.csv")


def remove_rent_entries_from(filename, destFilename):
    # remove fields from history csv which contains rent data
    # Eg:- remove_fields_with_value("status","Listed for rent")
    df = pd.read_csv("./" + filename,low_memory=False)
    # df = pd.read_csv("./VA_history.csv",low_memory=False)
    indexes = df.index[df['event'] == "Listed for rent"].values.tolist()
    result = list(map(lambda x: x + 1, indexes))
    # print((df.loc[[107375]]["status"]=="Listing removed").all())
    result = list(filter(lambda x: x <= df.tail(1).index.item() and (
            df.loc[[x]]["event"] == "Listing removed").all(), result))
    remainder = df.drop(result + indexes)
    remainder.to_csv("./" + destFilename)


def getSaleandRentCsvFor(state):
    collection = get_collection()
    rent = list(collection.find({"State": state, "Status": {
        "$in": ["Townhouse for rent", "Condo for rent", "House for rent"]}}))
    sale = list(collection.find({"State": state,
                                 "Status": {"$nin": ["Townhouse for rent", "Condo for rent",
                                                     "House for rent"]}}))

    write_multi_data_to_csv(state + "_rent.csv", rent)
    write_multi_data_to_csv(state + "_sale.csv", sale)
    genrate_historical_data_for(state)
    remove_rent_entries_from(state + "_history.csv", state + "_history_without_rent.csv")


# getSaleandRentCsvFor("VA")

# def get_csv_file_for(array_of_state_code):
#     for state in array_of_state_code:
#         getSaleandRentCsvFor(state)
#         print("Done for state of"+state)
#
# get_csv_file_for(["VA","CA","TX","MD","NY","AZ"])
# combineCSV()

# remove_rent_entries_from("./VA_history.csv", "./VA_history_without_rent.csv")
