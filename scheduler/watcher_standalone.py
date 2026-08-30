"""Standalone single-file watcher prototype (new-books-only change detection).

Kept as a self-contained reference implementation. The integrated version with
new + changed detection lives in scheduler/scheduler.py.

Run from the repository root:

    python -m scheduler.watcher_standalone
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pymongo
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pymongo import MongoClient

from utils.env_utils import get_env, load_env

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "changes.log"

INDEX_URL = "https://books.toscrape.com/"
INITIAL_LINK_FOR_BOOKS = "https://books.toscrape.com/catalogue/category/books_1/"


def get_connection_string() -> str:
    load_env()
    uri = get_env("MONGO_URI")
    if not uri:
        raise SystemExit("MONGO_URI not set. Add MONGO_URI to your .env file.")
    return uri


def connect() -> MongoClient:
    uri = get_connection_string()
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        print(f"Connected to MongoDB at {uri}")
        return client
    except pymongo.errors.PyMongoError as e:
        raise SystemExit(f"Could not connect to MongoDB: {e}\n")


def get_soup(webpage_link: str, parser: str = 'lxml') -> BeautifulSoup:
    response = requests.get(webpage_link).text
    return BeautifulSoup(response, parser)


def get_total_pages() -> int:
    index_soup = get_soup(INDEX_URL)
    pager = index_soup.find('ul', class_='pager').find('li').text
    return int(pager.replace("\n", '').strip().split(' ')[-1])


def scrape_catalog_books() -> list[dict]:
    books = []
    total_pages = get_total_pages()
    for page_number in range(total_pages):
        page_link = INITIAL_LINK_FOR_BOOKS + f"page-{page_number + 1}.html"
        page_soup = get_soup(page_link)
        for book in page_soup.find('ol', class_='row').find_all('li'):
            anchor = book.find('h3').find('a')
            books.append({
                "url": urljoin(page_link, anchor['href']),
                "title": anchor['title'].strip(),
            })
        print(f"Scraped page {page_number + 1}/{total_pages}")
        time.sleep(0.3)
    return books


def log_change(line: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def detect_new_books() -> None:
    client = connect()
    db_name = get_env("WATCHER_DB", "crawl_project")
    collection_name = get_env("WATCHER_COLLECTION", "books")
    collection = client[db_name][collection_name]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    books = scrape_catalog_books()
    existing_ids = set(collection.distinct("_id"))

    new_books = [b for b in books if b["url"] not in existing_ids]

    if new_books:
        collection.insert_many([
            {"_id": b["url"], "title": b["title"], "first_seen": now}
            for b in new_books
        ])
        for b in new_books:
            log_change(f"{now} | ADDED | {b['title']} | {b['url']}")

    log_change(f"{now} | RUN OK | scanned {len(books)} | added {len(new_books)} new")
    client.close()


def main() -> None:
    detect_new_books()

    interval_hours = float(get_env("CHECK_INTERVAL_HOURS", "6"))
    print(f"Scheduling detection every {interval_hours:g} hour(s).")
    scheduler = BlockingScheduler()
    scheduler.add_job(detect_new_books, "interval", hours=interval_hours)
    scheduler.start()


if __name__ == "__main__":
    main()