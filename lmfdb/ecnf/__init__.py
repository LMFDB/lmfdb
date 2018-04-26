# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

ecnf_page = Blueprint("ecnf", __name__, template_folder='templates', static_folder="static")
logger = make_logger(ecnf_page)


@ecnf_page.context_processor
def body_class():
    return {'body_class': 'ecnf'}

import main
assert main # to keep pyflakes quiet

app.register_blueprint(ecnf_page, url_prefix="/EllipticCurve")
