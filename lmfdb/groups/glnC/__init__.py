from lmfdb.app import app
from flask import Blueprint

glnC_page = Blueprint("glnC", __name__, template_folder='templates', static_folder="static")

from . import main
assert main # silence pyflakes

app.register_blueprint(glnC_page, url_prefix="/Groups/GLnC")
