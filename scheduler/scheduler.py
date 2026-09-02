import os, sys, httpx, asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.db import MyMongoDB
# from crawler.scraper import *
from utils.env_utils import load_env


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MyScheduler:
    def __init__(self):
        pass


    async def run_scheduler(self, my_db: MyMongoDB, interval_hours: float = 24) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            my_db.detect_changes_in_website,
            "interval",
            hours=interval_hours,
            next_run_time=datetime.now()
        )
        print(f"Scheduler starting. Checking every {interval_hours:g} hour(s). Press Ctrl+C to stop.")
        scheduler.start()

        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            scheduler.shutdown()



async def test_scheduler():
    load_env()

    username = os.getenv("UNAME")
    password = os.getenv("PASS")
    cluster = os.getenv("CLUSTER")
    my_db = MyMongoDB(username, password, cluster)

    scheduler = MyScheduler()
    await scheduler.run_scheduler(my_db)


if __name__ == "__main__":
    asyncio.run(test_scheduler())