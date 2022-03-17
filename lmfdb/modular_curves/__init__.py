# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

modcurve_page = Blueprint("modcurve", __name__, template_folder='templates')
modcurve_logger = make_logger(modcurve_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(modcurve_page, url_prefix="/ModularCurve")
