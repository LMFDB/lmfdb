# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

hypergm_page = Blueprint("hypergm", __name__, template_folder='templates', static_folder="static")
hgm_logger = make_logger(hypergm_page)


@hypergm_page.context_processor
def body_class():
    return {'body_class': 'hypergm'}

import main

app.register_blueprint(hypergm_page, url_prefix="/Motive/Hypergeometric/Q")
