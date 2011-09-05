from utils import make_logger
from flask import Blueprint

EMF="emf"
emf = Blueprint(EMF, __name__, template_folder="views/templates",static_folder="views/static")
emf_logger = make_logger(emf)

import views
import backend

