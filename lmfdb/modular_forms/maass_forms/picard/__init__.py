# -*- coding: utf-8 -*-

from __future__ import absolute_import
from lmfdb.logger import make_logger
from flask import Blueprint

mwfp = Blueprint("mwfp", __name__, template_folder="views/templates")
mwfp_logger = make_logger(mwfp)

from . import views
assert views
from . import backend
assert backend
