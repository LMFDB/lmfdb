from base import app

import main
import zeta.zetazeros
app.register_blueprint(main.mod, url_prefix="/zeros")
app.register_blueprint(zeta.zetazeros.ZetaZeros, url_prefix="/zeros/zeta")
