import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services import tyz as tyz_service

logger = logging.getLogger(__name__)


class Scheduler(object):
    def __init__(self, gost_endpoint: str, mng_endpoint: str, tyz_endpoint: str, node_id: int, token: str) -> None:
        # jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")}
        self.scheduler = AsyncIOScheduler()
        self.gost_endpoint = gost_endpoint
        self.panel_endpoint = mng_endpoint
        self.tyz_endpoint = tyz_endpoint
        self.node_id = node_id
        self.token = token

    def _add_schedules(self):
        self.scheduler.add_job(
            func=tyz_service.sync_relay_rules,
            trigger="interval",
            seconds=20,
            next_run_time=datetime.datetime.now(),
            kwargs={
                "endpoint": self.tyz_endpoint,
                "node_id": self.node_id,
                "token": self.token,
                "gost": self.gost_endpoint,
            },
        )

    def run_scheduler(self):
        self._add_schedules()
        self.scheduler.start()

    async def start(self):
        self.run_scheduler()

    async def stop(self):
        self.scheduler.shutdown()
