# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

st_page = Blueprint("st", __name__, template_folder='templates', static_folder="static")

@st_page.context_processor
def body_class():
    return {'body_class': 'st'}

from . import main

assert main # silence pyflakes

app.register_blueprint(st_page, url_prefix="/SatoTateGroup")

register_search_function("satotate", "Sato Tate Group",
    "Search over Sato Tate Groups", auto_search='gps_st', inv=['gps','gps_st'])
