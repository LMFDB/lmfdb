# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

g2c_page = Blueprint("g2c", __name__, template_folder='templates',
        static_folder="static")
g2c_logger = make_logger(g2c_page)
g2c_logger.info("Initializing genus 2 curves blueprint")

@g2c_page.context_processor
def body_class():
    return {'body_class': 'g2c'}

import genus2_curve

app.register_blueprint(g2c_page, url_prefix="/Genus2Curve")
