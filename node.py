import argparse
import logging
import tomllib
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, help="config file path", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)

    log_level = cfg.get("log", {}).get("level", "DEBUG").upper()
    fmt_logger(log_level)

    gost_endpoint = cfg.get("gost", {}).get("endpoint", "")
    panel_endpoint = cfg.get("panel", {}).get("endpoint", "")
    scheduler = Scheduler(gost_endpoint, panel_endpoint)
    scheduler.start()


if __name__ == "__main__":
    main()
