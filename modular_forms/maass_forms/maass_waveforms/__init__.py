from utils import make_logger
from flask import Blueprint

MWF="mwf" # Maass waveforms
mwf = Blueprint(MWF, __name__, template_folder="views/templates",static_folder="views/static")
mwf_logger = make_logger(mwf)

import backend
import views


