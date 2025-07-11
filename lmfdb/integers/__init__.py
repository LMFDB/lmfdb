
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

integers_page = Blueprint("integers", __name__, template_folder='templates', static_folder="static")
logger = make_logger(integers_page)


@integers_page.context_processor
def body_class():
    return {'body_class': 'integers'}

from . import main
assert main

app.register_blueprint(integers_page, url_prefix="/Integers")
