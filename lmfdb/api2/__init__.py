# -*- coding: utf-8 -*-
from lmfdb.app import app
assert app # keeps pyflakes happy
from lmfdb.logger import make_logger
assert make_logger # keeps pyflakes happy
from flask import Blueprint

__version__ = "1.0.0"

api2_page = Blueprint("API2", __name__, template_folder='templates', static_folder="static")

import api2
assert api2

app.register_blueprint(api2_page, url_prefix="/api2")
