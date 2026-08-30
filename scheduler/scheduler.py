"""Daily scheduler: detects newly added books and changed records, logs each change.

Run from the repository root:

    python -m scheduler.scheduler
"""
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from crawler.db import connect_to_MongoDB
from crawler.scraper import collect_all_book_data
from utils.env_utils import get_env, load_env

load_env()


def log_change(log_entry: str) -> None:
    log_file = get_env("LOG_FILE", "logs/changes.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(log_entry + "\n")
    print(f"Logged change : {log_entry}")
    pass


def get_keys_to_inspect() -> list[str]:
    raw = get_env("KEYS_TO_INSPECT", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


def look_for_changes() -> None:
    client = connect_to_MongoDB(
        get_env("MONGO_USERNAME"),
        get_env("MONGO_PASSWORD"),
        get_env("MONGO_CLUSTER"),
    )
    db = client[get_env("DEFAULT_DB", "crawl_project")]
    collection = db[get_env("DEFAULT_COLLECTION", "books")]

    existing_url_set = set(collection.distinct("metadata.source_url"))

    all_book_data = collect_all_book_data()

    new_books = [b for b in all_book_data if b["metadata"]["source_url"] not in existing_url_set]

    keys_to_inspect = get_keys_to_inspect()
    for b in all_book_data:
        if b["metadata"]["source_url"] in existing_url_set:
            existing_book = collection.find_one({"metadata.source_url": b["metadata"]["source_url"]})
            if existing_book is None:
                continue
            for key in keys_to_inspect:
                if b.get(key) != existing_book.get(key):
                    log_change(
                        f"Change detected | book id : {existing_book['_id']} | "
                        f"field '{key}' : {existing_book.get(key)} -> {b.get(key)}"
                    )
                    collection.update_one(
                        {"_id": existing_book["_id"]},
                        {"$set": {key: b.get(key)}},
                    )
                pass
            pass

    for book_data in new_books:
        collection.insert_one(book_data)
        log_change(
            f"New book added | name : {book_data['name']} | category : {book_data['category']} | "
            f"url : {book_data['metadata']['source_url']}"
        )

    client.close()
    pass


def run_scheduler(interval_hours: float = 24) -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(look_for_changes, "interval", hours=interval_hours)
    print(f"Scheduler starting. Checking every {interval_hours:g} hour(s). Press Ctrl+C to stop.")
    scheduler.start()
    pass


if __name__ == "__main__":
    run_scheduler(float(get_env("SCHEDULING_INTERVAL_HOURS", "24")))