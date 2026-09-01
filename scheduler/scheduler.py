import os, sys, apscheduler
from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.db import *
from crawler.scraper import *
from utils.env_utils import load_env


class MyScheduler:
    def __init__(self):
        pass


    def job_listener(self, event):
        if event.exception:
            print(f"Scheduler run failed: {event.exception}")
            return


    def run_scheduler(self, my_db: MyMongoDB, interval_hours: float = 0.0125) -> None:
        scheduler = BlockingScheduler()
        scheduler.add_job(
            my_db.detect_changes,
            "interval",
            hours=interval_hours,
        )
        # scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        print(f"Scheduler starting. Checking every {interval_hours:g} hour(s). Press Ctrl+C to stop.")
        scheduler.start()


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



if __name__ == "__main__":
    load_env()

    my_db = MyMongoDB(username="brinto", password="Brinto_says_%22Hi_There%22", cluster="cluster0.uy9kta3")
    scheduler = MyScheduler()
    scheduler.run_scheduler(my_db)