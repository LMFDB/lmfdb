
from . import api2
from flask import Blueprint
from lmfdb.logger import make_logger
from lmfdb.app import app
assert app  # keeps pyflakes happy
assert make_logger  # keeps pyflakes happy

__version__ = "1.0.0"

api2_page = Blueprint(
    "API2",
    __name__,
    template_folder='templates',
    static_folder="static")

assert api2

app.register_blueprint(api2_page, url_prefix="/api2")
