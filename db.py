from pymongo import MongoClient


class mongo:
    def __init__(self):
        self.client = MongoClient('129.174.126.176', 27018)
        db = self.client['Zillow']  # NAME OF DATABASE
        self.collection = db['House']  # NAME OF COLLECTION
        # print("MongoDB connected...")
    # post = {"id":1,"name":"asdsad"}
    def insert_article(self, article):
        # post_id = collection.insert_one(article).inserted_id
        post_id = self.collection.update({"zid": article["zid"]}, article, upsert=True)
        print("Inserted data with post id" + str(post_id))

    def check_if_zid_already_exist(self, zid):
        # post_id = collection.insert_one(article).inserted_id
        exists = self.collection.find_one({"zid": zid})
        return exists

    def insert_article_without_upsert(self, article):
        post_id = self.collection.insert_one(article)
        print("Inserted data with post id " + str(post_id))


def get_collection():
    client = MongoClient('129.174.126.176', 27018)
    db = client['Zillow']  # NAME OF DATABASE
    collection = db['House']  # NAME OF COLLECTION
    # print("MongoDB connected...")
    return collection

# self.client = MongoClient('129.174.126.176', 27018)
#         db = self.client['Zillow']  # NAME OF DATABASE
#         self.collection = db['House']  # NAME OF COLLECTION
#         print("MongoDB connected...")

# self.client = MongoClient('localhost', 27017)
#         db = self.client['zillow']  # NAME OF DATABASE
#         self.collection = db['House4']  # NAME OF COLLECTION
#         print("MongoDB connected...")
