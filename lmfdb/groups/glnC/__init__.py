# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

glnC_page = Blueprint("glnC", __name__, template_folder='templates', static_folder="static")
glnC_logger = make_logger(glnC_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(glnC_page, url_prefix="/Groups/GLnC")
