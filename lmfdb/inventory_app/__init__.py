
from lmfdb.app import app
from flask import Blueprint

# Initialize the Flask application
url_pref = '/inventory/'
inventory_app = Blueprint(
    "inventory_app",
    __name__,
    template_folder="./templates",
    static_folder="./static",
    static_url_path="static/",
)

from . import inventory_main
assert inventory_main # silence pyflakes

app.register_blueprint(inventory_app, url_prefix=url_pref)
