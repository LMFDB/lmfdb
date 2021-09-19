# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

maass_page = Blueprint("maass", __name__, template_folder='templates')
logger = make_logger(maass_page)

@maass_page.context_processor
def body_class():
    return {'body_class': 'maass'}

from . import main
assert main # silence pyflakes

app.register_blueprint(maass_page, url_prefix="/ModularForm/GL2/Q/Maass")

register_search_function(
    "gl2_maass_forms",
    "GL2 Maass forms",
    "Search over GL2 Maass forms",
    auto_search = 'maass_newforms'
)
