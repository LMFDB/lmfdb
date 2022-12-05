# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

characters_page = Blueprint("characters", __name__, template_folder='templates',
    static_folder="static")
logger = make_logger(characters_page)


@characters_page.context_processor
def body_class():
    return {'body_class': 'characters'}

from . import main
assert main # silence pyflakes

app.register_blueprint(characters_page, url_prefix="/Character")

# API2 has been disabled for now
#from lmfdb.api2.searchers import register_search_function
#register_search_function(
#    "char_dirichlet_orbits",
#    "Orbits of Dirichlet characters",
#    "Search over orbits of Dirichlet characters",
#    auto_search = 'char_dir_orbits'
#)
#register_search_function(
#    "char_dirichlet_values",
#    "Individual Dirichlet characters",
#    "Search over individual Dirichlet characters",
#    auto_search = 'char_dir_values'
#)
