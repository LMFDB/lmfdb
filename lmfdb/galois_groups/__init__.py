# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

galois_groups_page = Blueprint("galois_groups", __name__, template_folder='templates', static_folder="static")
logger = make_logger(galois_groups_page)


@galois_groups_page.context_processor
def body_class():
    return {'body_class': 'galois_groups'}

from . import main
assert main

app.register_blueprint(galois_groups_page, url_prefix="/GaloisGroup")

# API2 has been disabled for now
#from lmfdb.api2.searchers import register_search_function
#register_search_function(
#    "transitive_groups",
#    "Galois groups",
#    "Search over Galois groups",
#    auto_search = 'gps_transitive'
#)
