
from lmfdb.app import app
from flask import Blueprint

modcurve_page = Blueprint("modcurve", __name__, template_folder='templates')

from . import main
assert main # silence pyflakes

app.register_blueprint(modcurve_page, url_prefix="/ModularCurve")
