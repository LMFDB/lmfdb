from lmfdb.app import app
from flask import redirect, url_for
from lmfdb.modular_forms import mf, MF, mf_logger


@mf.context_processor
def body_class():
    return {'body_class': MF}

mf_logger.debug("EN_V path: {0}".format(app.jinja_loader.searchpath))


@mf.route("/")
def modular_form_main_page():
    return redirect(url_for('modular_forms'),301)
