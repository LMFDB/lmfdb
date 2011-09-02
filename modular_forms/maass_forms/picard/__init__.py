from base import app
from utils import make_logger
import flask 

MWFP="mwfp" # Maass waveforms on the Picard group SL(2,Z[i])
mwfp = flask.Blueprint(MWFP, __name__, template_folder="views/templates",static_folder="views/static")

mwfp_logger=make_logger(mwfp)

import views



