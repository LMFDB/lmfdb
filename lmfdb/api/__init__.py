# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

api_page = Blueprint("API", __name__, template_folder='templates', static_folder="static")
api_logger = make_logger(api_page)

@api_page.context_processor
def body_class():
    return {'body_class': 'api'}

import api
assert api # silence pyflakes

app.register_blueprint(api_page, url_prefix="/api")
