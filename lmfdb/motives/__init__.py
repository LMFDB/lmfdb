# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

motive_page = Blueprint("motive", __name__, template_folder='templates', static_folder="static")
motive_logger = make_logger(motive_page)


@motive_page.context_processor
def body_class():
    return {'body_class': 'motive'}

import main
assert main # silence pyflakes

app.register_blueprint(motive_page, url_prefix="/Motive")
