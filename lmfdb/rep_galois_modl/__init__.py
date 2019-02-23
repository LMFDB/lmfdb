# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

rep_galois_modl_page = Blueprint("rep_galois_modl", __name__, template_folder='templates', static_folder="static")
rep_galois_modl_logger = make_logger(rep_galois_modl_page)


@rep_galois_modl_page.context_processor
def body_class():
    return {'body_class': 'rep_galois_modl'}

import main
assert main #silence pyflakes

app.register_blueprint(rep_galois_modl_page, url_prefix="/Representation/Galois/ModL")
