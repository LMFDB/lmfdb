# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

nf_page = Blueprint("number_fields", __name__, template_folder='templates', static_folder="static")
nf_logger = make_logger(nf_page)

@nf_page.context_processor
def body_class():
    return {'body_class': 'nf'}

import number_field
assert number_field

app.register_blueprint(nf_page, url_prefix="/NumberField")
