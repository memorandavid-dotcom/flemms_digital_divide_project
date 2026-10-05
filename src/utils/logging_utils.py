"""Logging setup shared by all pipeline modules.

Inside Airflow, task logs are captured automatically from the standard logging
module. When running pipeline.py from a terminal, configure_cli_logging() prints
the same messages with timestamps.
"""
import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_cli_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
