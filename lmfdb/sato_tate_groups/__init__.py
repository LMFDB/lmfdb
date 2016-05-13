# -*- coding: utf-8 -*-
from lmfdb.base import app
from flask import Blueprint

st_page = Blueprint("st", __name__, template_folder='templates', static_folder="static")

@st_page.context_processor
def body_class():
    return {'body_class': 'st'}

import main

app.register_blueprint(st_page, url_prefix="/SatoTateGroup")
