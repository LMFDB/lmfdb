# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

crystal_page = Blueprint("crystal", __name__, template_folder='templates', static_folder="static")
logger = make_logger(crystal_page)


@crystal_page.context_processor
def body_class():
    return {'body_class': 'galois_groups'}

import main

app.register_blueprint(crystal_page, url_prefix="/Crystal")
