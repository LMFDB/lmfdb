
from lmfdb.app import app
from flask import Blueprint

hiwf_page = Blueprint("hiwf", __name__, template_folder='templates', static_folder="static")


@hiwf_page.context_processor
def body_class():
    return {'body_class': 'hiwf'}

from . import half_integral_form
assert half_integral_form

app.register_blueprint(hiwf_page, url_prefix="/ModularForm/GL2/Q/holomorphic_half")
