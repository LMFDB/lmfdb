from __future__ import absolute_import
from lmfdb.app import app

from . import inventory_app
app.register_blueprint(inventory_app.inventory_app, url_prefix = inventory_app.url_pref)
