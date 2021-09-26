# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

abstract_page = Blueprint("abstract", __name__, template_folder='templates', static_folder="static")

abstract_logger = make_logger(abstract_page)

#abstract_logger = make_logger(abstract_page, fmt="%(asctime)s - %(message)s")

from . import main
assert main # silence pyflakes

app.register_blueprint(abstract_page, url_prefix="/Groups/Abstract")
