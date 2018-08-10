# -*- coding: utf-8 -*-

from lmfdb.utils import make_logger
from flask import Blueprint

mwfp = Blueprint("mwfp", __name__, template_folder="views/templates")
mwfp_logger = make_logger(mwfp)

import views
assert views
import backend
assert backend
