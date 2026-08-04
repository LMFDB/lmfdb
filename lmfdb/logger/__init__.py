# Python logging module
from logging import info, warning, debug, critical, getLogger

from .start import start_logging

start_logging()

logger = getLogger()

__all__ = ['info', 'warning', 'debug', 'critical', 'logger']
