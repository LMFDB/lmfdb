from base import app
import backend
import views

app.register_module(views.mwf_main.mwf, url_prefix="/ModularForm/GL2/Q/Maass")

app.register_module(views.mwf_picard_main.mwfp, url_prefix="/ModularForm/GL2/C/Maass")



