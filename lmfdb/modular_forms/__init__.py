# / modular_forms/__init__.py
import lmfdb.base
import lmfdb.utils
from lmfdb.utils import make_logger
import flask

MF_TOP = "Modular Forms"
MF = "mf"
mf = flask.Blueprint(MF, __name__, template_folder="views/templates", static_folder="views/static")
mf_logger = make_logger(mf)

import views
import backend
import elliptic_modular_forms
import maass_forms
from elliptic_modular_forms import *
from maass_forms import *
lmfdb.base.app.register_blueprint(mf, url_prefix="/ModularForm/")
lmfdb.base.app.register_blueprint(mf, url_prefix="/AutomorphicForm/")
lmfdb.base.app.register_blueprint(elliptic_modular_forms.emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
lmfdb.base.app.register_blueprint(maass_forms.maassf, url_prefix="/ModularForm/Maass")
lmfdb.base.app.register_blueprint(maass_forms.maass_waveforms.mwf, url_prefix="/ModularForm/GL2/Q/Maass")
lmfdb.base.app.register_blueprint(maass_forms.picard.mwfp, url_prefix="/ModularForm/GL2/C/Maass")
