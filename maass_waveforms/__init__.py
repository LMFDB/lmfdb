from base import app
from utils import make_logger
import flask 

MWF="mwf"
mwf = flask.Blueprint(MWF, __name__, template_folder="views/templates",static_folder="views/static")
mwf_logger = make_logger(mwf)

import backend
import views
from backend import *

app.register_blueprint(views.mwf_main.mwf, url_prefix="/ModularForm/GL2/Q/Maass")

app.register_blueprint(views.mwf_picard_main.mwfp, url_prefix="/ModularForm/GL2/C/Maass")



