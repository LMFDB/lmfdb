# -*- coding: utf-8 -*-

from lmfdb.app import app
from flask import Blueprint

shimcurve_page = Blueprint("shimcurve", __name__, template_folder='templates')

from . import main
assert main # silence pyflakes

app.register_blueprint(shimcurve_page, url_prefix="/ShimuraCurve")
