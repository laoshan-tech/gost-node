import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services import gost as gost_service

logger = logging.getLogger(__name__)


class Scheduler(object):
    def __init__(self, gost_endpoint: str, panel_endpoint: str) -> None:
        # jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")}
        self.scheduler = AsyncIOScheduler()
        self.gost_endpoint = gost_endpoint
        self.panel_endpoint = panel_endpoint

    def _add_schedules(self):
        self.scheduler.add_job(
            func=gost_service.fetch_all_config,
            trigger="interval",
            seconds=20,
            kwargs={"endpoint": self.gost_endpoint},
        )

    def run_scheduler(self):
        self._add_schedules()
        self.scheduler.start()

    async def start(self):
        self.run_scheduler()

    async def stop(self):
        self.scheduler.shutdown()
