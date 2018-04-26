from lmfdb.base import app

import inventory_app
app.register_blueprint(inventory_app.inventory_app, url_prefix = inventory_app.url_pref)
