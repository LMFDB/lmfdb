# -*- coding: utf-8 -*-

from __future__ import absolute_import
from lmfdb.logger import make_logger
from flask import Blueprint

MAASSF = "maassf"
maassf = Blueprint(MAASSF, __name__, template_folder="views/templates")
maassf_logger = make_logger(maassf)

from . import maass_waveforms
assert maass_waveforms
from . import picard
assert picard
