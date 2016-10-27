# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

l_function_page = Blueprint("l_functions", __name__, template_folder='templates', static_folder="static")
logger = make_logger("LF")


@l_function_page.context_processor
def body_class():
    return {'body_class': 'l_functions'}

import main
assert main # silence pyflakes

app.register_blueprint(l_function_page, url_prefix="/L")


## How to solve this redirection easily?
##
##@app.route("/Lfunction/")
##@app.route("/Lfunction/<arg1>/")
##@app.route("/Lfunction/<arg1>/<arg2>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
##@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
##@app.route("/L-function/")
##@app.route("/L-function/<arg1>/")
##@app.route("/L-function/<arg1>/<arg2>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
##@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
# def render_Lfunction_redirect(**args):
##    args.update(request.args)
##    return flask.redirect(url_for("render_Lfunction", **args), code=301)
