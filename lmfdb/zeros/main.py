import flask

mod = flask.Blueprint('zeros', __name__, template_folder="templates")
title = "zeros"


@mod.context_processor
def body_class():
    return {'body_class': 'LfunctionDB'}


@mod.route("/")
def default_route():
    return ""


@mod.route("/zeta")
def query(**kwargs):
    pass
