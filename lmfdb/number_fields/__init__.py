# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

nf_page = Blueprint("number_fields", __name__, template_folder='templates', static_folder="static")
nf_logger = make_logger(nf_page)

@nf_page.context_processor
def body_class():
    return {'body_class': 'nf'}

from . import number_field
assert number_field

app.register_blueprint(nf_page, url_prefix="/NumberField")

register_search_function(
    "number_fields",
    "Global number fields",
    "Search over global number fields",
    auto_search = 'nf_fields'
)
