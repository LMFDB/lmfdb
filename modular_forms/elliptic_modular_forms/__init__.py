import utils
import flask

EMF="emf"
emf = flask.Blueprint(EMF, __name__, template_folder="views/templates",static_folder="views/static")
emf_logger = utils.make_logger(emf)

import views
import backend
from backend import *
