# / modular_forms/__init__.py
import base 
import utils
import flask

MF_TOP = "Modular Forms"
MF = "mf"
mf = flask.Blueprint(MF, __name__, template_folder="views/templates",static_folder="views/static")
mf_logger=utils.make_logger(mf)

import views
import backend
import elliptic_modular_forms 
import maass_forms
from elliptic_modular_forms  import *

base.app.register_blueprint(mf, url_prefix="/ModularForm/")
base.app.register_blueprint(mf, url_prefix="/AutomorphicForm/")
base.app.register_blueprint(elliptic_modular_forms.emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
base.app.register_blueprint(maass_forms.maassf, url_prefix="/ModularForm/Maass")
base.app.register_blueprint(maass_forms.maass_waveforms.mwf, url_prefix="/ModularForm/GL2/Q/Maass")
base.app.register_blueprint(maass_forms.picard.mwfp, url_prefix="/ModularForm/GL2/C/Maass")

