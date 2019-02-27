# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

characters_page = Blueprint("characters", __name__, template_folder='templates',
    static_folder="static")
logger = make_logger(characters_page)


@characters_page.context_processor
def body_class():
    return {'body_class': 'characters'}

import main
assert main # silence pyflakes

app.register_blueprint(characters_page, url_prefix="/Character")
