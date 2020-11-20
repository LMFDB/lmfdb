# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_singleton, register_search_function
from . import searchers

ecnf_page = Blueprint("ecnf", __name__, template_folder='templates', static_folder="static")
logger = make_logger(ecnf_page)


@ecnf_page.context_processor
def body_class():
    return {'body_class': 'ecnf'}

from . import main
assert main # to keep pyflakes quiet

app.register_blueprint(ecnf_page, url_prefix="/EllipticCurve")

register_search_function(
    "elliptic_curves_nf",
    "Elliptic curves over number fields",
    "Search over elliptic curves defined over number fields",
    auto_search='ec_nfcurves'
)
register_singleton('EllipticCurve', 'ec_nfcurves',
    simple_search = searchers.ecnf_simple_label_search)
