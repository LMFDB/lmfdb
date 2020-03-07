# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

galois_groups_page = Blueprint("galois_groups", __name__, template_folder='templates', static_folder="static")
logger = make_logger(galois_groups_page)


@galois_groups_page.context_processor
def body_class():
    return {'body_class': 'galois_groups'}

from . import main
assert main

app.register_blueprint(galois_groups_page, url_prefix="/GaloisGroup")

register_search_function(
    "transitive_groups",
    "Galois groups",
    "Search over Galois groups",
    auto_search = 'gps_transitive'
)
