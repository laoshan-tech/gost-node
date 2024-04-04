import logging

import uvicorn


def fmt_logger(level: str) -> dict:
    # default logging
    default_fmt = "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)s | %(message)s"
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    logging.basicConfig(
        level=level_map[level],
        format=default_fmt,
        force=True,
    )
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # uvicorn logging
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["access"]["fmt"] = default_fmt
    uvicorn_log_config["formatters"]["default"]["fmt"] = default_fmt
    return uvicorn_log_config
