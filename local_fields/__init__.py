# -*- coding: utf-8 -*-
from base import app
from utils import make_logger
from flask import Blueprint

local_fields_page = Blueprint("local_fields", __name__, template_folder='templates', static_folder="static")
logger = make_logger(local_fields_page)

@local_fields_page.context_processor
def body_class():
  return { 'body_class' : 'local_fields' }

import main 

app.register_blueprint(local_fields_page, url_prefix="/LocalField")


