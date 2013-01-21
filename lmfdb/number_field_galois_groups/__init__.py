# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

nfgg_page = Blueprint(
    "number_field_galois_groups", __name__, template_folder='templates', static_folder="static")
nfgg_logger = make_logger(nfgg_page)


@nfgg_page.context_processor
def body_class():
    return {'body_class': 'nfgg'}

import main

app.register_blueprint(nfgg_page, url_prefix="/NFGG")
