# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

permutations_page = Blueprint("permutations", __name__, template_folder='templates', static_folder="static")
logger = make_logger(permutations_page)


@permutations_page.context_processor
def body_class():
    return {'body_class': 'Permutations'}

import main
assert main

app.register_blueprint(permutations_page, url_prefix="/Permutations")
