from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['zillow']
collection = db['Houses3']
print("MongoDB connected...")

#post = {"id":1,"name":"asdsad"}
def insert_article(article):
    #post_id = collection.insert_one(article).inserted_id
    post_id = collection.update({"zid":article["zid"]},article,upsert=True)
    print("Inserted data with post id"+str(post_id))
