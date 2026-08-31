from urllib.parse import quote_plus
import os, sys, pymongo
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_utils import load_env

from crawler.scraper import *

load_env()

class MyMongoDB():
    def __init__(self, username: str, password: str, cluster: str):
        connection_string = f"mongodb+srv://{username}:{password}@{cluster}.mongodb.net/"
        try:
            self.client = MongoClient(connection_string)
            self.client.admin.command("ping")
            print(f"\n Successfully connected to MongoDB at {connection_string}.")
        except pymongo.errors.PyMongoError as e:
            raise SystemExit(e)
        pass


    def insert_data_to_database(self) -> None:
        DB = os.getenv("DEFAULT_DB")
        COLLECTION = os.getenv("DEFAULT_COLLECTION")

        db = self.client[DB]
        collection = self.client[DB][COLLECTION]

        crawler = MyCrawler()
        all_book_data = collect_all_book_data(crawler)
        collection.insert_many([book.model_dump() for book in all_book_data])

        print(f"\n{'*'*30} Insertion done. Let's check something... {'*'*30}\n")

        collection_names = guarded(lambda: db.list_collection_names())
        sample_document = guarded(lambda: collection.find_one())

        if collection_names and sample_document:
            print("Success!\n")
        else:
            print("Oops, need to investigate!\n")

        self.client.close()


if __name__ == "__main__":
    my_db = MyMongoDB(username="brinto", password="Brinto_says_%22Hi_There%22", cluster="cluster0.uy9kta3")
    my_db.insert_data_to_database()