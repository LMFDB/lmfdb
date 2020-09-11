# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function, register_singleton
from . import searchers

ec_page = Blueprint("ec", __name__, template_folder='templates', static_folder="static")
ec_logger = make_logger(ec_page)
#ec_logger.info("Initializing elliptic curves blueprint")


@ec_page.context_processor
def body_class():
    return {'body_class': 'ec'}

from . import elliptic_curve
assert elliptic_curve # for pyflakes

app.register_blueprint(ec_page, url_prefix="/EllipticCurve/Q")

register_search_function("elliptic_curves_q", "Elliptic curves over rationals",
    "Search over elliptic curves defined over rationals", auto_search = 'ec_curves')
register_singleton('EllipticCurve/Q', 'ec_curves',
    simple_search = searchers.ec_simple_label_search)
