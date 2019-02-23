# Python logging module
from logging import info, warning, debug

from .start import setup_logging
from .utils import timestamp

setup_logging()

__all__ = ['info', 'warning', 'debug', 'timestamp']
