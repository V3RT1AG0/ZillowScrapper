from pymongo import MongoClient

client = MongoClient('localhost', 27018)
db = client['Zillow'] #NAME OF DATABASE
collection = db['House'] #NAME OF COLLECTION
print("MongoDB connected...")

#post = {"id":1,"name":"asdsad"}
def insert_article(article):
    #post_id = collection.insert_one(article).inserted_id
    post_id = collection.update({"zid":article["zid"]},article,upsert=True)
    print("Inserted data with post id"+str(post_id))

def check_if_zid_already_exist(zid):
    #post_id = collection.insert_one(article).inserted_id
    exists = collection.find_one({"zid":zid})
    return exists

def insert_article_without_upsert(article):
    post_id = collection.insert_one(article)
    print("Inserted data with post id " + str(post_id))
