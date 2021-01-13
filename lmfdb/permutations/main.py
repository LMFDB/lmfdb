# -*- coding: utf-8 -*-
# This Blueprint is about Permutations
# Author: Sebastien Labbe

from flask import render_template, request, url_for, redirect
from lmfdb.permutations import permutations_page, logger
from sage.all import Permutation, Integer
from lmfdb.utils import flash_error


def get_bread(breads=[]):
    bc = [("Permutations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


@permutations_page.route("/show", methods = ["POST"])
def parse_and_redirect():
    r"""
    This gets called when the user submit some input in the data box of the
    following page:

    http://127.0.0.1:37777/Permutations/

    It then redirects to the appropriate permutation page.
    """
    assert request.method == "POST", "request.method is assumed to be POST"
    data = str(request.form.get('data', ''))
    data = data.replace(',', '.')
    return redirect(url_for(".show", data=data))


@permutations_page.route("/show", methods = ["GET"])
def show():
    r"""
    This gets called when an address of that kind gets loaded:

    http://127.0.0.1:37777/Permutations/show?data=3.4.2.1
    """
    assert request.method == "GET", "request.method is assumed to be GET"
    data = str(request.args.get('data', ''))
    try:
        data = [Integer(z) for z in data.split('.')]
        p = Permutation(data)
    except (TypeError, ValueError):
        logger.info("Impossible to create a permutation from input.")
        flash_error("Ooops, impossible to create a permutation from given input!")
        return redirect(url_for(".index"))
    return render_template("permutations.html", permutation=p,
            rankbread=get_bread())

@permutations_page.route("/")
def index():
    r"""
    This gets called when this address gets loaded:

    http://127.0.0.1:37777/Permutations/
    """
    bread = get_bread()
    return render_template("permutations-index.html", title="Permutations", bread=bread)
