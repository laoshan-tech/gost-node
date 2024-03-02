import asyncio
import datetime
import logging

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

from service import gost as gost_service

logger = logging.getLogger(__name__)


class Scheduler(object):
    def __init__(self, gost_endpoint: str, panel_endpoint: str) -> None:
        self.scheduler = AsyncScheduler()
        self.gost_endpoint = gost_endpoint
        self.panel_endpoint = panel_endpoint

    async def _add_schedules(self):
        await self.scheduler.add_schedule(
            func_or_task_id=gost_service.fetch_all_config,
            trigger=IntervalTrigger(seconds=20, start_time=datetime.datetime.now()),
            kwargs={"endpoint": self.gost_endpoint},
        )

    async def run_scheduler(self):
        async with self.scheduler:
            await self._add_schedules()

        await self.scheduler.run_until_stopped()

    def start(self):
        try:
            asyncio.run(self.run_scheduler())
        except KeyboardInterrupt:
            asyncio.run(self.scheduler.stop())
        finally:
            logger.warning("scheduler shut down")
