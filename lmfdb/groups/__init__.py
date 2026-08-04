from lmfdb.app import app
from flask import Blueprint

groups_page = Blueprint("groups", __name__, template_folder='templates', static_folder="static")
groups = groups_page

app.register_blueprint(groups_page, url_prefix="/Groups")
