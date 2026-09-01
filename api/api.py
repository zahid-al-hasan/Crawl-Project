import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from crawler.db import *
from utils.env_utils import load_env
from bson.objectid import ObjectId

load_env()

my_db = MyMongoDB(username="brinto", password="Brinto_says_%22Hi_There%22", cluster="cluster0.uy9kta3")
db = my_db.client[os.getenv("DEFAULT_DB")]
collection = db[os.getenv("DEFAULT_COLLECTION")]

books = list(collection.find())
print(books[1:4])

app = FastAPI()


@app.get("/")
def index():
    return "Hello, You are on the web crawling project"



@app.get("/books")
def get_books(category: str, min_price: float, max_price: float, rating: str):
    query = {
        "category" : category,
        "star_rating" : rating,
        "euro_price_without_tax" : {
            "$gte" : min_price,
            "$lte" : max_price
        }
    } 
    books = list(collection.find(query).sort([("star_rating", pymongo.ASCENDING), ("euro_price_without_tax", pymongo.ASCENDING), ("review_count", pymongo.ASCENDING)]))
    for book in books:
        book["_id"] = str(book["_id"])
    return books
    pass


@app.get("/books/{book_id}")
def get_book_by_id(book_id: str):
    book = collection.find_one({"_id" : ObjectId(book_id)})
    book["_id"] = str(book["_id"])
    return book
    pass


@app.get("/changes")
def get_changes():
    
    pass