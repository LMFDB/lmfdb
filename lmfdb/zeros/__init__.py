
from lmfdb.app import app

from . import main
from .zeta import zetazeros
app.register_blueprint(main.mod, url_prefix="/zeros")
app.register_blueprint(zetazeros.ZetaZeros, url_prefix="/zeros/zeta")
