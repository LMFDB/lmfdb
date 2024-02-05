# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

shimcurve_page = Blueprint("shimcurve", __name__, template_folder='templates')
shimcurve_logger = make_logger(shimcurve_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(shimcurve_page, url_prefix="/ShimuraCurve")
