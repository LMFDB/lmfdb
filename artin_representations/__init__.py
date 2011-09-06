# -*- coding: utf-8 -*-
from base import app
from utils import make_logger
from flask import Blueprint

artin_representations_page = Blueprint("artin_representations", __name__, template_folder='templates', static_folder="static")
logger = make_logger(artin_representations_page)

@artin_representations_page.context_processor
def body_class():
  return { 'body_class' : 'artin_representations' }

import main 

app.register_blueprint(artin_representations_page, url_prefix="/ArtinRepresentation")


