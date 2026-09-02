# FK Crawling Project

An asynchronous web-crawling project that scrapes [books.toscrape.com](https://books.toscrape.com/) (1000 books), stores data in **MongoDB Atlas**, schedules **change detection**, and serves the data via **FastAPI**.

---

## Table of Contents

1. [Pipeline](#pipeline)
2. [Dependencies](#dependencies)
3. [Setup](#setup)
4. [Environment Variables (.env)](#environment-variables-env)
5. [Running the Project](#running-the-project)
6. [Project Structure](#project-structure)
7. [Important Aspects](#important-aspects)
8. [API Endpoints](#api-endpoints)

---

## Pipeline

```
books.toscrape.com  (50 pages x 20 books)
        │  async scraping (httpx + BeautifulSoup + asyncio.gather)
        ▼
   crawler/scraper  ──►  list[Book]  (Pydantic v2)
        │
        ▼
   crawler/db  (MongoDB Atlas via PyMongo)
        │  bulk insert  /  change detection
        ▼
   books collection              logs collection
        ▲                               ▲
        │                               │
   scheduler/scheduler (APScheduler)    │
        │                               │
        └────────────── api/api (FastAPI + slowapi) ◄── reads both
```

**Flow:** scrape every book page concurrently → parse into `Book` models → persist to MongoDB → a scheduled job re-crawls to detect new/modified books → the FastAPI API reads the data for consumers.

Two persistence paths:
- `insert_data_to_database()` — one-shot **bulk** import (`insert_many`).
- `detect_changes_in_website()` — **incremental**: re-crawls, dedups `source_url`s, inserts only new books, and updates existing ones for the `KEYS_TO_INSPECT` fields. A `Log` is written to the `logs` collection for each new/updated book.

---

## Dependencies

| Package          | Version  | Purpose                                   |
| ---------------- | -------- | ----------------------------------------- |
| `httpx`          | 0.28.1   | Asynchronous HTTP client for scraping     |
| `requests`       | 2.34.2   | Synchronous HTTP fallback                 |
| `beautifulsoup4` | 4.15.0   | HTML parsing                              |
| `lxml`           | 6.1.2    | Parser backend for BeautifulSoup (`lxml`) |
| `pydantic`       | 2.13.5   | Data models (`Book`, `BookMetadata`, `Log`) |
| `pymongo`        | 4.17.0   | MongoDB Atlas connection & operations     |
| `apscheduler`    | 3.11.3   | Scheduling (`AsyncIOScheduler`)           |
| `fastapi`        | 0.141.1  | Web API framework                         |
| `uvicorn`        | 0.52.4   | ASGI server                               |
| `slowapi`        | 0.1.10   | API rate limiting                         |
| `python-dotenv`  | 1.2.3    | Load `.env` variables                     |

---

## Setup

1. Ensure Python 3.12+.
2. Install dependencies:
   ```bash
   pip install httpx requests beautifulsoup4 lxml pydantic pymongo apscheduler fastapi uvicorn slowapi python-dotenv
   ```
3. Create a `.env` file at the project root (see below) and fill in your MongoDB credentials and `API_KEY`.
4. Run everything from the project root (`Project/`).

---

## Environment Variables (.env)

The project is configured entirely through a `.env` file at the root. Existing OS variables are never overwritten. Below are the **keys exactly as used**; **sensitive values are omitted**.

| Key                 | Value (non-sensitive)                                   | Notes                         |
| ------------------- | ------------------------------------------------------- | ----------------------------- |
| `UNAME`             | *(your MongoDB username)*                               | 🔒 Secret                  |
| `PASS`              | *(your MongoDB password)*                               | 🔒 Secret                  |
| `CLUSTER`           | *(your Atlas cluster name)*                             | 🔒 Secret                  |
| `INDEX_URL`         | `https://books.toscrape.com/`                           | Site root                     |
| `INITIAL_URL`       | `https://books.toscrape.com/catalogue/`                 | Book pages location           |
| `DEFAULT_DB`        | `crawl_project`                                         | Database name                 |
| `DEFAULT_COLLECTION`| `books`                                                 | Books collection              |
| `LOG_COLLECTION`    | `logs`                                                  | Change-log collection         |
| `KEYS_TO_INSPECT`   | `name,description,category,euro_price_with_tax,euro_price_without_tax,availability,review_count,image_url,star_rating` | Fields compared for changes |
| `API_KEY`           | *(your chosen API key)*                                 | 🔒 Secret                  |

> 🔒 `UNAME`, `PASS`, `CLUSTER` and `API_KEY` are secret and must never be committed/shared. They are gitignored via `.gitignore`.

---

## Running the Project

```bash
# Crawl all books and bulk-insert into MongoDB (used for testing whether insertion works), has to use own (username + password + cluster) credentials
python crawler/db.py

# Scheduled change detection (re-crawls + detects new/modified)
python scheduler/scheduler.py
# Press Ctrl+C to stop

# FastAPI service (has to set own API_KEY in .env)
uvicorn api.api:app --reload --port 8000
# Docs: http://127.0.0.1:8000/docs
```

---

## Project Structure

```
Project/
├── api/
│   └── api.py                 # FastAPI: /, /books, /books/{id}, /changes
├── crawler/
│   ├── scraper.py             # MyCrawler, Book models, collect_all_book_data
│   └── db.py                  # MyMongoDB: bulk insert + change detection
├── scheduler/
│   └── scheduler.py           # MyScheduler (AsyncIOScheduler interval job)
├── utils/
│   └── env_utils.py           # load_env() / get_env() helpers
├── tests/                     # unit-test package
├── .env                       # configuration (gitignored)
└── .gitignore
```

---

## Some Mentionable Aspects

- **Could not touch all the additional tasks, but tried to complete all main tasks.**
- **Scraping information of 1000 books around just a minute** proves that asynchronous programming worked.
- **Small scheduling interval for testing.** Validated with a short interval (e.g. `1/12` hour ≈ 5 min, down to `0.0125` hour ≈ 45 s during dev). Production should use a much larger interval.
-**Small rate limit for testing.** Used "3/minute" for testing. Kept as it is.
- **Cold client per run.** Each run creates a fresh `httpx.AsyncClient()` (default 5 s timeout) and closes it with `aclose()`; no connection pool reuse across runs.
- **Best-effort dedup.** Newness is decided against a `distinct("metadata.source_url")` snapshot, not a unique index — overlapping concurrent runs could re-insert.
- **Field-whitelisted change detection.** Only the `KEYS_TO_INSPECT` keys are compared/updated; metadata (`timestamp`, `source_url`) is excluded.
- **Fault-tolerant extraction.** `guarded()` returns `"NULL"` on any selector failure instead of aborting a parse.
- **Concurrency without a cap.** Per-page book requests fire together via `asyncio.gather`; no `Semaphore`, so transient `httpx.ConnectTimeout` can occur under load.
- **Markup-driven pagination.** The loop follows `li.next` from `page-1.html` and stops automatically after the last page.
- **`_id` stringified for JSON.** Mongo `ObjectId`s are converted to `str` before being returned by the API.
- **API is key-guarded and rate-limited.** Endpoints require `X-API-Key`; `slowapi` limits books to `100/hour` and `/changes` to `3/minute`.


---

## API Endpoints

All endpoints except `/` require the `X-API-Key` header.

| Method | Path               | Auth    | Rate limit | Description                                  |
| ------ | ------------------ | ------- | ---------- | -------------------------------------------- |
| GET    | `/`                | none    | —          | Basic message                                |
| GET    | `/books`           | API key | 100/hour   | Filter by `category`, `min_price`, `max_price`, `rating` |
| GET    | `/books/{book_id}` | API key | 100/hour   | Fetch one book by Mongo `_id`                |
| GET    | `/changes`         | API key | 3/minute   | Return all change logs from the `logs` collection |

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/books?category=Travel&min_price=10&max_price=50&rating=4"
```
