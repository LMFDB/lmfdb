# Python logging module
from logging import info, warning, debug, critical

from .start import start_logging, logger_file_handler

start_logging()

__all__ = ['info', 'warning', 'debug', 'critical', 'logger_file_handler']
