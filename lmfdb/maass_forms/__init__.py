
from lmfdb.app import app
from flask import Blueprint


maass_forms_page = Blueprint("maass_forms", __name__, template_folder='templates')


@maass_forms_page.context_processor
def body_class():
    return {'body_class': 'maass_forms'}


from . import main
assert main


app.register_blueprint(maass_forms_page, url_prefix="/ModularForm/GL2/Q/Maass")
