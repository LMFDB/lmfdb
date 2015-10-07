from lmfdb.utils import make_logger
import flask

## Some common definitions to use in this module.

default_prec = 10   # The default number of terms in a q-expansion
default_bprec = 53  # The default number of bits of precision to compute for floating point data
default_display_bprec = 26  # The default number of bits of precision to display for floating point data
from sage.env import SAGE_VERSION
version_major, version_minor = [int(x) for x in SAGE_VERSION.split('.')[:2]]
if (version_major, version_minor) >= (6,8):
    emf_version = 1.3
else:
    emf_version = 1.1

EMF_TOP = "Holomorphic Modular Forms"  # The name to use for the top of this catergory
EMF = "emf"  # The current blueprint name
emf = flask.Blueprint(EMF, __name__, template_folder="views/templates", static_folder="views/static")
emf_logger = make_logger(emf)
emf_logger.info("Initializing elliptic modular forms blueprint with Sage version %s, emf version %s" % (SAGE_VERSION, emf_version))

### Maximum values for computations
N_max_comp = 50
k_max_comp = 12
N_max_Gamma1_fdraw = 33
N_max_Gamma0_fdraw = 300
N_max_db = 5000
k_max_db = 12
N_max_extra_comp = 500

use_cache= True

import views
import backend
from backend import *
