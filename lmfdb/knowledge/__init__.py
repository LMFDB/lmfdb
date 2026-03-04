
from lmfdb.app import app
from flask import Blueprint

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')

from . import main
assert main

app.register_blueprint(knowledge_page, url_prefix="/knowledge")
