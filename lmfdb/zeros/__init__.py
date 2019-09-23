from lmfdb.app import app

import main
import zeta.zetazeros
import first.firstzeros
app.register_blueprint(main.mod, url_prefix="/zeros")
app.register_blueprint(zeta.zetazeros.ZetaZeros, url_prefix="/zeros/zeta")
app.register_blueprint(first.firstzeros.FirstZeros, url_prefix="/zeros/first")
