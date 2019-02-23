# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

hmf_page = Blueprint("hmf", __name__, template_folder='templates', static_folder="static")
hmf_logger = make_logger(hmf_page)


@hmf_page.context_processor
def body_class():
    return {'body_class': 'hmf'}

import hilbert_modular_form
assert hilbert_modular_form

app.register_blueprint(hmf_page, url_prefix="/ModularForm/GL2/TotallyReal")
