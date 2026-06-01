# -*- coding: utf-8 -*-

from lmfdb.app import app
from flask import Blueprint

hmsurface_page = Blueprint("hmsurface", __name__, template_folder='templates')

from . import main
assert main # silence pyflakes

app.register_blueprint(hmsurface_page, url_prefix="/HilbertModularSurface")
