# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

groups_page = Blueprint("groups", __name__, template_folder='templates', static_folder="static")
groups = groups_page
groups_logger = make_logger(groups_page)

app.register_blueprint(groups_page, url_prefix="/Groups")
