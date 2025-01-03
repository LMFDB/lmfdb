from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

glnQ_page = Blueprint("glnQ", __name__, template_folder='templates', static_folder="static")
glnQ_logger = make_logger(glnQ_page)

from . import main
assert main # silence pyflakes

app.register_blueprint(glnQ_page, url_prefix="/Groups/GLnQ")
