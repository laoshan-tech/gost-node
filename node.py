import argparse
import tomllib
from pathlib import Path

import loguru

logger = loguru.logger


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
    logger.debug(cfg)


if __name__ == "__main__":
    main()
