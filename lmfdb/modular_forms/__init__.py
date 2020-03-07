from __future__ import absolute_import
# / modular_forms/__init__.py

import flask

from lmfdb.logger import make_logger
from lmfdb.app import app

MF_TOP = "Modular Forms"
MF = "mf"
mf = flask.Blueprint(MF, __name__, template_folder="views/templates")
mf_logger = make_logger(mf)

from . import maass_forms
assert maass_forms
from . import views
assert views

app.register_blueprint(mf, url_prefix="/ModularForm/")
# app.register_blueprint(maass_forms.maassf, url_prefix="/ModularForm/Maass")
app.register_blueprint(maass_forms.maass_waveforms.mwf, url_prefix="/ModularForm/GL2/Q/Maass")
# app.register_blueprint(maass_forms.picard.mwfp, url_prefix="/ModularForm/GL2/C/Maass")
