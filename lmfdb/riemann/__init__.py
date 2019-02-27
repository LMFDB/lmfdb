from lmfdb.app import app

import main
import stieltjes
app.register_blueprint(main.mod, url_prefix="/riemann")
app.register_blueprint(stieltjes.StieltjesConstants, url_prefix="/riemann/stieltjes")
