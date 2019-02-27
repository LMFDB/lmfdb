# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

crystals_page = Blueprint("crystals", __name__, template_folder='templates', static_folder="static")
logger = make_logger(crystals_page)


@crystals_page.context_processor
def body_class():
    return {'body_class': 'Crystals'}

import main
assert main # silence pyflakes

app.register_blueprint(crystals_page, url_prefix="/Crystals")
