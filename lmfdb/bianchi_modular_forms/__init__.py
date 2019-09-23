# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

bmf_page = Blueprint("bmf", __name__, template_folder='templates', static_folder="static")
bmf_logger = make_logger(bmf_page)


@bmf_page.context_processor
def body_class():
    return {'body_class': 'bmf'}

import bianchi_modular_form
assert bianchi_modular_form

app.register_blueprint(bmf_page, url_prefix="/ModularForm/GL2/ImaginaryQuadratic")
