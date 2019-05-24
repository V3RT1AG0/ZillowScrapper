import pandas as pd
import csv
from db import insert_article
import json



def combineCSV():
    sell = pd.read_csv("./sell.csv")
    rent = pd.read_csv("./rent.csv")
    auction = pd.read_csv("./auction.csv")
    combined = pd.concat([sell, rent,auction], sort=False)
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
        return data[state]


def write_visited_zip_code(state,zipCode):
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
    unvisited = [ l for l in all if l not in visited]
    return unvisited

def write_to_csv(data):
    print(data)

    status = data["status"]
    if status == "House for rent":
        filename = "rent.csv"
    elif status == "Sold":
        filename = "sold.csv"
    elif status == "For sale":
        filename = "sell.csv"
    else:
        filename = "auction.csv"


    keys = data.keys()
    try:
        with open(filename, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            # writer.writeheader()
            writer.writerow(data)
    except IOError:
        print("I/O error")

    insert_article(data)
