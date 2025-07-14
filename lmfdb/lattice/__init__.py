
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

genus_page = Blueprint("genus", __name__, template_folder='templates', static_folder="static")
genus_logger = make_logger(genus_page)

@genus_page.context_processor
def body_class():
    return {'body_class': 'genus'}

from . import genus
assert genus

app.register_blueprint(genus_page, url_prefix="/Lattice")
