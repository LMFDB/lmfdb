# -*- coding: utf-8 -*-

from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint


maass_rigor_page = Blueprint("maass_rigor", __name__, template_folder='templates')
logger = make_logger(maass_rigor_page)


@maass_rigor_page.context_processor
def body_class():
    return {'body_class': 'maass_rigor'}


from . import main
assert main


app.register_blueprint(maass_rigor_page, url_prefix="/ModularForm/GL2/Q/RigorMaass")
