from base import app
from utils import make_logger
from flask import Blueprint
import elliptic_modular_forms #import *


MF = "mf"
mf = Blueprint(MF, __name__, template_folder="views/templates",static_folder="views/static")
mf_logger=make_logger(mf)

import views
from elliptic_modular_forms import emf
app.register_blueprint(mf, url_prefix="/ModularForm/")
app.register_blueprint(emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
import modular_forms.maass_forms
from  modular_forms.maass_forms import maassf #mwf,mwfp
app.register_blueprint(maassf, url_prefix="/ModularForm/Maass")


#from  modular_forms.maass_forms.maass_waveforms import mwf,mwfp
#app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
#app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")


#app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
#app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")
