import logging


def fmt_logger(level: str):
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    logging.basicConfig(
        level=level_map[level], format="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)s | %(message)s"
    )
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
