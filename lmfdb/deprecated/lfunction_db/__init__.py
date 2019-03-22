# -*- coding: utf8 -*-

from lmfdb.app import app

import main
app.register_blueprint(main.mod, url_prefix="/LfunctionDB")
