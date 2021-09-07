# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint
from lmfdb.api2.searchers import register_search_function

g2c_page = Blueprint("g2c", __name__, template_folder='templates')
g2c_logger = make_logger(g2c_page)

@g2c_page.context_processor
def body_class():
    return {'body_class': 'g2c'}

from . import main
assert main # silence pyflakes

app.register_blueprint(g2c_page, url_prefix="/Genus2Curve")

register_search_function(
    "genus_2_curves",
    "Genus 2 curves over rationals",
    "Search over genus 2 curves defined over rationals",
    auto_search = 'g2c_curves'
)
register_search_function(
    "genus_2_curve_ratpoints",
    "Rational points on genus 2 curves over rationals",
    "Search over genus 2 curve rational points",
    auto_search = 'g2c_ratpts'
)
