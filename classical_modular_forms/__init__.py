from base import app
import backend
import views
from backend import *

app.register_module(views.cmf_main.cmf, url_prefix="/ModularForm/GL2/Q/holomorphic")

