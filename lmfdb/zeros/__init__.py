from __future__ import absolute_import
from lmfdb.app import app

from . import main
from .zeta import zetazeros
from .first import firstzeros
app.register_blueprint(main.mod, url_prefix="/zeros")
app.register_blueprint(zetazeros.ZetaZeros, url_prefix="/zeros/zeta")
app.register_blueprint(firstzeros.FirstZeros, url_prefix="/zeros/first")
