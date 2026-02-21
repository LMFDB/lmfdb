
from lmfdb.app import app
from flask import Blueprint

modlgal_page = Blueprint("modlgal", __name__, template_folder='templates', static_folder="static")

from . import main
assert main #silence pyflakes

app.register_blueprint(modlgal_page, url_prefix="/ModLGaloisRepresentation")
