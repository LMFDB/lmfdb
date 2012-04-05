import utils
import flask

## Some common definitions to use in this module.

default_prec = 10   # The default number of terms in a q-expansion
default_bprec = 26 # The default number of bits of precision to display in floating point data
EMF_TOP = "Holomorphic Modular Forms" # The name to use for the top of this catergory
EMF="emf" # The current blueprint name
emf = flask.Blueprint(EMF, __name__, template_folder="views/templates",static_folder="views/static")
emf_logger = utils.make_logger(emf)
### Maximum values for computations
N_max_comp = 50
k_max_comp = 12
N_max_Gamma1_fdraw = 33
N_max_Gamma0_fdraw = 300
N_max_db = 5000
k_max_db = 12
N_max_AL = 500

import views
import backend
from backend import *
