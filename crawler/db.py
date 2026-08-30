from urllib.parse import quote_plus

import pymongo, os
from dotenv import load_dotenv
from pymongo import MongoClient

from crawler.scraper import *

load_dotenv()

def connect_to_MongoDB(username: str, password: str, cluster: str):
    connection_string = f"mongodb+srv://{quote_plus(str(username))}:{quote_plus(str(password))}@{cluster}/"
    try:
        client = MongoClient(connection_string)
        client.admin.command("ping")
        print(f"\n Successfully connected to MongoDB at {connection_string}.")
        return client
    except pymongo.errors.PyMongoError as e:
        raise SystemExit(e)
    pass 


def insert_data_to_database(username: str, password: str, cluster: str, ) -> None:
    client = connect_to_MongoDB(username, password, cluster)
    db = client[os.getenv("DEFAULT_DB", "crawl_project")]    
    collection = db[os.getenv("DEFAULT_COLLECTION", "books")]

    all_book_data = collect_all_book_data()
    collection.insert_many([book_data for book_data in all_book_data])

    print(f"\n{'*'*30} Insertion done. Let's check something... {'*'*30}\n")

    collection_names = guarded(lambda: db.list_collection_names())
    sample_document = guarded(lambda: collection.find_one())

    if collection_names and sample_document:
        print("Success!\n")
    else:
        print("Oops, need to investigate!\n")

    client.close()


if __name__ == "__main__":
    from utils.env_utils import get_env, load_env

    load_env()
    insert_data_to_database(
        get_env("MONGO_USERNAME"),
        get_env("MONGO_PASSWORD"),
        get_env("MONGO_CLUSTER"),
    )