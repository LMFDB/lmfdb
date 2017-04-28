import flask
from flask import redirect, url_for

mod = flask.Blueprint('zeros', __name__, template_folder="templates")
title = "zeros"


@mod.context_processor
def body_class():
    return {'body_class': 'LfunctionDB'}


@mod.route("/")
def default_route():
    return redirect(url_for("zeta zeros.zetazeros"))


@mod.route("/zeta")
def query(**kwargs):
    return redirect(url_for("zeta zeros.zetazeros"))
