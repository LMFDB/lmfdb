# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

ec_page = Blueprint("ec", __name__, template_folder='templates', static_folder="static")
ec_logger = make_logger(ec_page)
ec_logger.info("Initializing elliptic curves blueprint")


@ec_page.context_processor
def body_class():
    return {'body_class': 'ec'}

#from elliptic_curves import *
import elliptic_curve

app.register_blueprint(ec_page, url_prefix="/EllipticCurve/Q")
