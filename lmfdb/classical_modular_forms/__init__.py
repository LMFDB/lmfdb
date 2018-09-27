from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

cmf_page = Blueprint("cmf", __name__, template_folder='templates', static_folder="static")
cmf = cmf_page
cmf_logger = make_logger(cmf_page)

import main
assert main # silence pyflakes

app.register_blueprint(cmf_page, url_prefix="/ModularForm/GL2/Q/holomorphic")
