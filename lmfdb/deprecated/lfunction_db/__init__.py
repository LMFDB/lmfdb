# -*- coding: utf8 -*-

from __future__ import absolute_import
from lmfdb.app import app

from . import main
app.register_blueprint(main.mod, url_prefix="/LfunctionDB")
