
from lmfdb.app import app
from flask import Blueprint

modlmf_page = Blueprint("modlmf", __name__, template_folder='templates', static_folder="static")


@modlmf_page.context_processor
def body_class():
    return {'body_class': 'modlmf'}

from . import main
assert main

app.register_blueprint(modlmf_page, url_prefix="/ModularForm/GL2/ModL")
