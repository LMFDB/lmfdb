
from lmfdb.app import app
from flask import Blueprint

motive_page = Blueprint("motive", __name__, template_folder='templates', static_folder="static")


@motive_page.context_processor
def body_class():
    return {'body_class': 'motive'}

from . import main
assert main # silence pyflakes

app.register_blueprint(motive_page, url_prefix="/Motive")
