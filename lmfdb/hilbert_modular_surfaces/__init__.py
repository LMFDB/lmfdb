# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

hmsurface_page = Blueprint("hmsurface", __name__, template_folder='templates')
hmsurface_logger = make_logger(hmsurface_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(hmsurface_page, url_prefix="/HilbertModularSurface")
