# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

lattice_page = Blueprint("lattice", __name__, template_folder='templates', static_folder="static")
lattice_logger = make_logger(lattice_page)


@lattice_page.context_processor
def body_class():
    return {'body_class': 'lattice'}

import main
assert main

app.register_blueprint(lattice_page, url_prefix="/Lattice")
