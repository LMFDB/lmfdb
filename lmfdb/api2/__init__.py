# -*- coding: utf-8 -*-
from lmfdb.app import app
assert app # keeps pyflakes happy
from lmfdb.logger import make_logger
assert make_logger # keeps pyflakes happy
from flask import Blueprint
assert Blueprint # keeps pyflakes happy

__version__ = '1.0.0'
