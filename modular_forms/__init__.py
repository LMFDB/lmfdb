from base import app
from utils import make_logger
from flask import Blueprint
import elliptic_modular_forms 


MF = "mf"
mf = Blueprint(MF, __name__, template_folder="views/templates",static_folder="views/static")
mf_logger=make_logger(mf)

import views
import backend
app.register_blueprint(mf, url_prefix="/ModularForm/")
from elliptic_modular_forms import *
app.register_blueprint(emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
import modular_forms.maass_forms


