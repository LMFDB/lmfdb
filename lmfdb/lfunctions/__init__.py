# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

l_function_page = Blueprint("l_functions", __name__, template_folder='templates', static_folder="static")
logger = make_logger("LF")


@l_function_page.context_processor
def body_class():
    return {'body_class': 'l_functions'}

import main
assert main # silence pyflakes

app.register_blueprint(l_function_page, url_prefix="/L")

