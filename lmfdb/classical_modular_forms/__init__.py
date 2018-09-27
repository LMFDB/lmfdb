from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

emf_page = Blueprint("emf", __name__, template_folder='templates', static_folder="static")
emf = emf_page
emf_logger = make_logger(emf_page)

import main
assert main # silence pyflakes

