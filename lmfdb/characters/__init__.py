# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

characters_page = Blueprint("characters", __name__, template_folder='templates',
    static_folder="static")
logger = make_logger(characters_page)


@characters_page.context_processor
def body_class():
    return {'body_class': 'characters'}

import main

app.register_blueprint(characters_page, url_prefix="/Character")
