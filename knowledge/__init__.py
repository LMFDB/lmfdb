# -*- coding: utf-8 -*-
from base import app
from utils import make_logger
from flask import Blueprint

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')
logger = make_logger(knowledge_page)

import main 

app.register_blueprint(knowledge_page, url_prefix="/knowledge")

