
from . import main
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')
logger = make_logger(knowledge_page)

assert main

app.register_blueprint(knowledge_page, url_prefix="/knowledge")
