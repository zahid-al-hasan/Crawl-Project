import os, sys
from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.db import *
from crawler.scraper import *
from utils.env_utils import get_env, load_env



PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log_change(log_entry: str) -> None:
    log_file = os.getenv("LOG_FILE", "logs/changes.log")
    if not os.path.isabs(log_file):
        log_file = os.path.join(PROJECT_ROOT, log_file)
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(log_entry + "\n")
    print(f"Logged change : {log_entry}")
    pass


def get_keys_to_inspect() -> list[str]:
    raw = os.getenv("KEYS_TO_INSPECT", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


def look_for_changes(username: str, password: str, cluster: str) -> None:
    client = connect_to_MongoDB(username, password, cluster)
    db = client[os.getenv("DEFAULT_DB", "crawl_project")]
    collection = db[os.getenv("DEFAULT_COLLECTION", "books")]

    existing_url_set = set(collection.distinct("metadata.source_url"))

    all_book_data = collect_all_book_data()

    new_books = [b for b in all_book_data if b["metadata"]["source_url"] not in existing_url_set]
    for book_data in new_books:
        collection.insert_one(book_data)
        log_change(f"New book added. Book name : {book_data["name"]}, Category : {book_data["category"]}, url : {book_data["metadata"]["source_url"]}")
        pass

    modified_books = set()
    keys_to_inspect = get_keys_to_inspect()
    for b in all_book_data:
        if b["metadata"]["source_url"] in existing_url_set:
            existing_book = collection.find_one({"metadata.source_url": b["metadata"]["source_url"]})
            if existing_book is None:
                continue
            for key in keys_to_inspect:
                if b.get(key) != existing_book.get(key):
                    modified_books.add(b)
                    log_change(f"Change detected for book id : {existing_book['_id']}. field '{key}' : {existing_book[key]} -> {b[key]}")
                    collection.update_one({"_id": existing_book["_id"]}, {"$set": {key: b[key]}})
                pass
            pass

    
    client.close()
    return new_books, modified_books
    pass


def job_listener(event):
    if event.exception:
        print(f"Scheduler run failed: {event.exception}")
        return

    new_books, modified_books = event.retval

    new_count = len(new_books) if new_books else 0
    modified_count = len(modified_books) if modified_books else 0
    print(f"{'No' if new_count == 0 else new_count} new book(s) are added in the website.")
    print(f"{'No' if modified_count == 0 else modified_count} book(s) are modified in the website.")


def run_scheduler(db_username: str, db_password: str, db_cluster: str, interval_hours: float = 0.0125) -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        look_for_changes,
        "interval",
        hours=interval_hours,
        args=[db_username, db_password, db_cluster]
    )
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    print(f"Scheduler starting. Checking every {interval_hours:g} hour(s). Press Ctrl+C to stop.")
    scheduler.start()

    pass


if __name__ == "__main__":
    load_env()
    run_scheduler(db_username="brinto", db_password="Brinto_says_%22Hi_There%22", db_cluster="cluster0.uy9kta3")