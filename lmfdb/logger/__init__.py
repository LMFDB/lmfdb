# Python logging module
from logging import info, warning, debug, critical

from .start import start_logging, logger_file_handler
from .utils import make_logger

start_logging()

__all__ = ['info', 'warning', 'debug', 'critical', 'make_logger', 'logger_file_handler']
