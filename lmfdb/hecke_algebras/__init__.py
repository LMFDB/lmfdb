# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

hecke_algebras_page = Blueprint("hecke_algebras", __name__, template_folder='templates', static_folder="static")
hecke_algebras_logger = make_logger(hecke_algebras_page)


@hecke_algebras_page.context_processor
def body_class():
    return {'body_class': 'hecke_algebras'}

import main
assert main

app.register_blueprint(hecke_algebras_page, url_prefix="/ModularForm/GL2/Q/HeckeAlgebra")
