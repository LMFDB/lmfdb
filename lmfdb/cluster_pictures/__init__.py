# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

#cp_logger = make_logger(cp_page)

from . import cluster_picture
