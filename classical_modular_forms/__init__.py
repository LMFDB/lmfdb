from base import app
from utils import make_logger
import flask 

CMF="cmf"
cmf = flask.Blueprint(CMF, __name__, template_folder="views/templates",static_folder="views/static")

cmf_logger = make_logger(cmf)

import views
import backend
from backend import *

# registering the blueprint must come *after* defining all the url mappings in views!
app.register_blueprint(cmf, url_prefix="/ModularForm/GL2/Q/holomorphic")
