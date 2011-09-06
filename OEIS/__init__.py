# -*- coding: utf-8 -*-
from base import app
from utils import make_logger
from flask import Blueprint

OEIS_object_page = Blueprint("OEIS_object", __name__, template_folder='templates', static_folder="static")
logger = make_logger(OEIS_object_page)

@OEIS_object_page.context_processor
def body_class():
  return { 'body_class' : 'OEIS_object' }

import main 

# This is one possibility to inject pages into the Flask framework.
# For another, see the L-function page
app.register_blueprint(OEIS_object_page, url_prefix="/OEIS/")
