from base import app
import backend
import views

app.register_module(views.mwf_main.mwf, url_prefix="/ModularForm/GL2/Q/Maass2")

