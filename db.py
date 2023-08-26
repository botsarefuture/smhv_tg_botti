import pymongo

# Initialize the MongoDB client
def initialize_db():
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["training_bot"]
    trainings_collection = db["trainings"]
    trainings_collection.create_index([("datetime", pymongo.ASCENDING)])
    return db