# -*- coding: utf8 -*-

from lmfdb.base import app

import main
app.register_blueprint(main.mod, url_prefix="/LfunctionDB")
