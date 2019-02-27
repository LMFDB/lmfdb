# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

belyi_page = Blueprint("belyi", __name__, template_folder='templates',
        static_folder="static")
belyi_logger = make_logger(belyi_page)

@belyi_page.context_processor
def body_class():
    return {'body_class': 'belyi'}

import main
assert main # silence pyflakes

app.register_blueprint(belyi_page, url_prefix="/Belyi")
