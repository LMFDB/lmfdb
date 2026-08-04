
from lmfdb.app import app
from flask import Blueprint

crystals_page = Blueprint("crystals", __name__, template_folder='templates', static_folder="static")


@crystals_page.context_processor
def body_class():
    return {'body_class': 'Crystals'}

from . import main
assert main # silence pyflakes

app.register_blueprint(crystals_page, url_prefix="/Crystals")
