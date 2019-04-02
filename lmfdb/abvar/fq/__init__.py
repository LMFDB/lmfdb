# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

abvarfq_page = Blueprint("abvarfq", __name__, template_folder='templates', static_folder="static")
abvarfq_logger = make_logger(abvarfq_page)


@abvarfq_page.context_processor
def body_class():
    return {'body_class': 'abvarfq'}

import main
assert main

app.register_blueprint(abvarfq_page, url_prefix="/Variety/Abelian/Fq")
