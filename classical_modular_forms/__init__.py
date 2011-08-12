from base import app
import backend
import views

#app.register_module(views.cmf_main.cmf, url_prefix="/ModularForm/GL2/Q/holomorphic")
app.register_blueprint(views.cmf_main.cmf, url_prefix="/ModularForm/GL2/Q/holomorphic")

