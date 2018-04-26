# -*- coding: utf-8 -*-
from lmfdb.base import app
assert app # keeps pyflakes happy
from lmfdb.utils import make_logger
assert make_logger # keeps pyflakes happy
from flask import Blueprint
assert Blueprint # keeps pyflakes happy

__version__ = '1.0.0'
