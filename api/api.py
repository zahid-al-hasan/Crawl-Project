import os, sys, slowapi

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends, Header, HTTPException
from crawler.db import *
from utils.env_utils import load_env
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from bson.objectid import ObjectId

load_env()

my_db = MyMongoDB(username=os.getenv("UNAME"), password=os.getenv("PASS"), cluster=os.getenv("CLUSTER"))
db = my_db.client[os.getenv("DEFAULT_DB")]
collection = db[os.getenv("DEFAULT_COLLECTION")]


app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(slowapi.errors.RateLimitExceeded, _rate_limit_exceeded_handler)



def require_api_key(api_key: str = Header(default=None)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="invalid credential or missing API key")
    return api_key



@app.get("/")
def index():
    return "On the web crawling project"



@app.get("/books", dependencies=[Depends(require_api_key)])
@limiter.limit("100/hour")
def get_books(request: Request, category: str, min_price: float, max_price: float, rating: int):
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


@app.get("/books/{book_id}", dependencies=[Depends(require_api_key)])
@limiter.limit("100/hour")
def get_book_by_id(request: Request, book_id: str):
    book = collection.find_one({"_id" : ObjectId(book_id)})
    book["_id"] = str(book["_id"])
    return book
    pass


@app.get("/changes", dependencies=[Depends(require_api_key)])
@limiter.limit("3/minute")
def get_changes(request: Request):
    logs = db[os.getenv("LOG_COLLECTION")]
    updates = list(logs.find())
    for update in updates:
        update["_id"] = str(update["_id"])
    return updates
    pass