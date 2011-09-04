from base import app
from utils import make_logger
import flask 

EMF="emf"
FULLNAME = "Classical Holomorphic Modular Forms"
emf = flask.Blueprint(EMF, __name__, template_folder="views/templates",static_folder="views/static")

emf_logger = make_logger(emf)

import views
#import backend
from backend import *

# registering the blueprint must come *after* defining all the url mappings in views!
#app.register_blueprint(emf, url_prefix="/ModularForm/GL2/Q/holomorphic")
