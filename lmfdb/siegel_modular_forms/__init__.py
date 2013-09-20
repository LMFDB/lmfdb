# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

smf_page = Blueprint( 'siegel_modular_forms', __name__,
                 template_folder = 'templates', static_folder = 'static')
smf_logger = make_logger( smf_page)

@smf_page.context_processor
def body_class():
    return { 'body_class': 'siegel_modular_forms'}

from siegel_modular_form import *

app.register_blueprint( smf_page, url_prefix ='/ModularForm/GSp/Q')
