# -*- coding: utf-8 -*-

from lmfdb.logger import make_logger
from flask import Blueprint

MWF = "mwf"  # Maass waveforms
mwf = Blueprint(MWF, __name__, template_folder="views/templates", static_folder="views/static")
mwf_logger = make_logger(mwf)

import backend
assert backend
import views
assert views
