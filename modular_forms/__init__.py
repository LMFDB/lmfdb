# / modular_forms/__init__.py
from base import app
from utils import make_logger
from flask import Blueprint
MF = "mf"
mf = Blueprint(MF, __name__, template_folder="views/templates",static_folder="views/static")
mf_logger=make_logger(mf)

import views
import backend
import elliptic_modular_forms 
import maass_forms
#import maass_forms.picard

from elliptic_modular_forms import emf
from maass_forms import maassf
from maass_forms.maass_waveforms import mwf
from maass_forms.picard import mwfp

app.register_blueprint(mf, url_prefix="/ModularForm/")
app.register_blueprint(emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
app.register_blueprint(maassf, url_prefix="/ModularForm/Maass")
app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")

