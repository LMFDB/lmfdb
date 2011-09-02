from base import app
from utils import make_logger
import flask 
from flask import Blueprint
### The different kinds of Maass forms we have.
MAASSF = "maassf"
maassf = Blueprint(MAASSF, __name__, template_folder="views/templates")
maassf_logger=make_logger(maassf)
#app.register_blueprint(views.maass_forms.maassf, url_prefix="/ModularForm/Maass")
app.register_blueprint(maassf, url_prefix="/ModularForm/Maass")
#app.register_blueprint(views.mwf_picard_main.mwfp, url_prefix="/ModularForm/GL2/C/Maass")
import views
import maass_waveforms
import picard

from  modular_forms.maass_forms.maass_waveforms import mwf
from  modular_forms.maass_forms.picard import mwfp
app.register_blueprint(mwf, url_prefix="/ModularForm/GL2/Q/Maass")
app.register_blueprint(mwfp, url_prefix="/ModularForm/GL2/C/Maass")
