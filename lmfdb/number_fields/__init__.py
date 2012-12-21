# -*- coding: utf-8 -*-
from base import app
from utils import make_logger
from flask import Blueprint

nf_page = Blueprint("number_fields", __name__, template_folder='templates', static_folder="static")
nf_logger = make_logger(nf_page)

@nf_page.context_processor
def body_class():
    return {'body_class': 'nf'}

from number_field import *

app.register_blueprint(nf_page, url_prefix="/NumberField")
