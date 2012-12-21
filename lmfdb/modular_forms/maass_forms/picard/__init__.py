from utils import make_logger
from flask import Blueprint

MWFP="mwfp" 
mwfp = Blueprint(MWFP, __name__, template_folder="views/templates")
mwfp_logger=make_logger(mwfp)
mwfp_dbname = 'HTPicard'

import views
import backend


