import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services import tyz as tyz_service

logger = logging.getLogger(__name__)


class Scheduler(object):
    def __init__(self, cfg: dict) -> None:
        # jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")}
        self.scheduler = AsyncIOScheduler()
        self.gost_endpoint = cfg.get("gost", {}).get("endpoint", "")
        self.tyz_endpoint = cfg.get("tyz", {}).get("endpoint", "")
        self.prom = cfg.get("gost", {}).get("prometheus", "")
        self.node_id = cfg.get("tyz", {}).get("node_id", 0)
        self.token = cfg.get("tyz", {}).get("token", "")

    def _add_schedules(self):
        # sync rules
        self.scheduler.add_job(
            func=tyz_service.sync_relay_rules,
            trigger="interval",
            seconds=30,
            misfire_grace_time=60,
            next_run_time=datetime.datetime.now(),
            kwargs={
                "endpoint": self.tyz_endpoint,
                "node_id": self.node_id,
                "token": self.token,
                "gost": self.gost_endpoint,
            },
        )

        # report traffic used
        self.scheduler.add_job(
            func=tyz_service.report_traffic_by_rules,
            trigger="interval",
            seconds=30,
            misfire_grace_time=60,
            next_run_time=datetime.datetime.now(),
            kwargs={"endpoint": self.tyz_endpoint, "prom": self.prom},
        )

    def run_scheduler(self):
        self._add_schedules()
        self.scheduler.start()

    async def start(self):
        self.run_scheduler()

    async def stop(self):
        self.scheduler.shutdown()
