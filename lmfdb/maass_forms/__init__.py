# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

maass_page = Blueprint("maass", __name__, template_folder='templates')
logger = make_logger(maass_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(maass_page, url_prefix="/ModularForm/GL2/Q/NewMaass"")
