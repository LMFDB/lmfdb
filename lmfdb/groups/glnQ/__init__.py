from lmfdb.app import app
from flask import Blueprint

glnQ_page = Blueprint("glnQ", __name__, template_folder='templates', static_folder="static")

from . import main
assert main # silence pyflakes

app.register_blueprint(glnQ_page, url_prefix="/Groups/GLnQ")
