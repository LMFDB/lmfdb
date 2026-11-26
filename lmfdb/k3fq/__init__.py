from lmfdb.app import app
from flask import Blueprint

k3fq_page = Blueprint("k3fq", __name__, template_folder="templates", static_folder="static")


@k3fq_page.context_processor
def body_class():
    return {"body_class": "k3fq"}

from . import main
assert main

app.register_blueprint(k3fq_page, url_prefix="/Motive/K3/Fq")
