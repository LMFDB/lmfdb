from base import app
from utils import make_logger
from flask import Blueprint

MWF="mwf" # Maass waveforms
mwf = Blueprint(MWF, __name__, template_folder="views/templates",static_folder="views/static")

mwf_logger = make_logger(mwf)
#app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
import backend
import views
#from backend import *


#app.register_blueprint(views.mwf_picard_main.mwfp, url_prefix="/ModularForm/GL2/C/Maass")


