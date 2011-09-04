from base import app
from utils import make_logger
from flask import Blueprint

MWFP="mwfp" # Maass waveforms on the Picard group SL(2,Z[i])
mwfp = Blueprint(MWFP, __name__, template_folder="views/templates",static_folder="views/static")
#app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")
mwfp_logger=make_logger(mwfp)

import views
import backend
#from views import *


