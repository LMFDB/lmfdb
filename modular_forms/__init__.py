from base import app
from utils import make_logger
from flask import Blueprint
import elliptic_modular_forms 

MF = "mf"
mf = Blueprint(MF, __name__, template_folder="views/templates",static_folder="views/static")
mf_logger=make_logger(mf)

import views
import backend
from elliptic_modular_forms import *
import maass_forms
from maass_forms import *
import maass_forms.maass_waveforms
from  maass_forms.maass_waveforms import *
import maass_forms.picard
from  maass_forms.picard import *
app.register_blueprint(mf, url_prefix="/ModularForm/")
app.register_blueprint(emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
app.register_blueprint(maassf, url_prefix="/ModularForm/Maass")
app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")


#from maass_forms import *


