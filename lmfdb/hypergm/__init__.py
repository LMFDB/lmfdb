
from lmfdb.app import app
from flask import Blueprint

hypergm_page = Blueprint("hypergm", __name__, template_folder='templates',
                         static_folder="static")


@hypergm_page.context_processor
def body_class():
    return {'body_class': 'hypergm'}


from . import main
assert main  # silence pyflakes

app.register_blueprint(hypergm_page, url_prefix="/Motive/Hypergeometric/Q")
