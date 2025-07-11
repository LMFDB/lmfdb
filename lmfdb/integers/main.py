# This Blueprint is a toy example based upon the Integers
# Author: Steven Clontz

from flask import render_template, request, url_for, redirect
from lmfdb.integers import integers_page, logger
from sage.all import Integer
from lmfdb.utils import flash_error


def get_bread(breads=None):
    bc = [("Integers", url_for(".index"))]
    if breads is None:
        return bc
    bc.extend(b for b in breads)
    return bc


@integers_page.route("/", methods=["GET"])
def index():
    r"""
    This gets called when this address gets loaded:

    /Integers/
    """
    bread = get_bread()
    return render_template("integers-index.html", title="Integers", bread=bread)


@integers_page.route("/", methods=["POST"])
def parse_and_redirect():
    r"""
    This gets called when the user submit some input in the data box of the
    following page:

    /Integers/

    It then redirects to the appropriate integer page.
    """
    assert request.method == "POST", "request.method is assumed to be POST"
    data = str(request.form.get('data', ''))
    return redirect(url_for(".show", label=data))


@integers_page.route("/<label>", methods=["GET"])
def show(label:str):
    r"""
    This gets called when an address of that kind gets loaded:

    /Integers/42
    """
    assert request.method == "GET", "request.method is assumed to be GET"
    try:
        n = Integer(label)
    except (TypeError, ValueError):
        logger.info("Impossible to create a natural from input.")
        flash_error("Ooops, impossible to create a natural from given input!")
        return redirect(url_for(".index"))
    return render_template("integers.html", integer=n, bread=get_bread([(f"{n}", "")]))
