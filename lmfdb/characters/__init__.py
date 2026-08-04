
from lmfdb.app import app
from flask import Blueprint

characters_page = Blueprint("characters", __name__, template_folder='templates',
    static_folder="static")


@characters_page.context_processor
def body_class():
    return {'body_class': 'characters'}

from . import main
assert main # silence pyflakes

app.register_blueprint(characters_page, url_prefix="/Character")
