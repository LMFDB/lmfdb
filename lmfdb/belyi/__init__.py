
from lmfdb.app import app
from flask import Blueprint

belyi_page = Blueprint(
    "belyi", __name__, template_folder="templates", static_folder="static"
)


@belyi_page.context_processor
def body_class():
    return {"body_class": "belyi"}


from . import main
assert main  # silence pyflakes

app.register_blueprint(belyi_page, url_prefix="/Belyi")
