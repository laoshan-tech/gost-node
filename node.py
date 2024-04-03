import argparse
import logging
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI

from routers import index, observer
from sched import Scheduler
from utils.log import fmt_logger

logger = logging.getLogger(__name__)


def load_config(config_path):
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"config file {config_path} not exist, please check")
        exit(0)

    with open(path, "rb") as f:
        config = tomllib.load(f)

    return config


@asynccontextmanager
async def lifespan(web_app: FastAPI):
    # start scheduler with fastapi
    web_app.include_router(index.router, prefix="")
    web_app.include_router(observer.router, prefix="/observer")
    await scheduler.start()
    yield
    # stop scheduler
    await scheduler.stop()


app = FastAPI(lifespan=lifespan)


def main():
    p = urlparse(cfg.get("mng", {}).get("endpoint", ""))
    uvicorn.run(app, host=p.hostname, port=p.port or 80, log_config=uvicorn_log_cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, help="config file path", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)

    log_level = cfg.get("log", {}).get("level", "DEBUG").upper()
    uvicorn_log_cfg = fmt_logger(log_level)
    scheduler = Scheduler(cfg=cfg)
    main()
