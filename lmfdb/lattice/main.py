import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ, latex

from lmfdb.lattice import lattice_page, lattice_logger

lattice_credit = 'someone'


def get_bread(breads=[]):
    bc = [("lattices", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')


@lattice_page.route("/")
def index():
    bread = get_bread([])
    info = {}
    friends=[]
    return render_template("lattice-index.html", title="Lattice label", bread=bread, credit=lattice_credit, info=info, friends=friends)

