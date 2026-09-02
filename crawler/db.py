from urllib.parse import quote_plus
import os, sys, pymongo, httpx, datetime, asyncio
from pymongo import MongoClient
from pydantic import BaseModel
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_utils import load_env

from crawler.scraper import MyCrawler, collect_all_book_data, guarded

class Log(BaseModel):
    timestamp : str
    content : str


    
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


    async def insert_data_to_database(self) -> None:
        DB = os.getenv("DEFAULT_DB")
        COLLECTION = os.getenv("DEFAULT_COLLECTION")

        db = self.client[DB]
        collection = self.client[DB][COLLECTION]

        crawler = MyCrawler(httpx.AsyncClient())
        all_book_data = await collect_all_book_data(crawler)
        collection.insert_many([book.model_dump() for book in all_book_data])

        print(f"\n{'*'*30} Insertion done. Let's check something... {'*'*30}\n")

        collection_names = guarded(lambda: db.list_collection_names())
        sample_document = guarded(lambda: collection.find_one())

        if collection_names and sample_document:
            print("Success!\n")
        else:
            print("Oops, need to investigate!\n")



    async def detect_changes_in_website(self):
        DB = os.getenv("DEFAULT_DB")
        COLLECTION = os.getenv("DEFAULT_COLLECTION")
        LOG = os.getenv("LOG_COLLECTION")

        db = self.client[DB]
        collection = db[COLLECTION]
        logs = db[LOG]

        existing_url_set = set(collection.distinct("metadata.source_url"))

        crawler = MyCrawler(httpx.AsyncClient())
        all_book_data = await collect_all_book_data(crawler)

        new_books = [b for b in all_book_data if b.metadata.source_url not in existing_url_set]
        for book_data in new_books:
            collection.insert_one(book_data.model_dump())

            new_log_content = f"New book added. Book name : {book_data.name}, Category : {book_data.category}, url : {book_data.metadata.source_url}"
            new_log = Log(timestamp=datetime.datetime.now().__str__(), content=new_log_content)
            logs.insert_one(new_log.model_dump())
            pass


        modified_books = set()
        keys_to_inspect = os.getenv("KEYS_TO_INSPECT")
        keys_to_inspect = [key.strip() for key in keys_to_inspect.split(",")]

        for b in all_book_data:
            if b.metadata.source_url in existing_url_set:
                existing_book = collection.find_one({"metadata.source_url": b.metadata.source_url})
                if existing_book is None:
                    continue
                for key in keys_to_inspect:
                    if getattr(b, key) != existing_book.get(key):
                        modified_books.add(b)
                        collection.update_one({"_id": existing_book["_id"]}, {"$set": {key: getattr(b, key)}})

                        new_log_content = f"Change detected for book id : {existing_book['_id']}. field '{key}' : {existing_book[key]} -> {getattr(b, key)}"
                        new_log = Log(timestamp=datetime.datetime.now().__str__(), content=new_log_content)
                        logs.insert_one(new_log.model_dump())
                    pass
                pass

        # return new_books, modified_books
        


async def test_db():
    load_env()

    username = os.getenv("UNAME")
    password = os.getenv("PASS")
    cluster = os.getenv("CLUSTER")
    my_db = MyMongoDB(username, password, cluster)
    await my_db.insert_data_to_database()



if __name__ == "__main__":
    asyncio.run(test_db())