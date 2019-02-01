#-*- coding: utf-8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
"""
start this via $ sage -python website.py --port <portnumber>
add --debug if you are developing (auto-restart, full stacktrace in browser, ...)
"""


import logging
import utils
import os
import time
from base import app, set_logfocus, get_logfocus, _init
from flask import g, render_template, request, make_response, redirect, url_for, current_app, abort
import sage
from lmfdb.config import Configuration


LMFDB_SAGE_VERSION = '7.1'

def setup_logging():
    logging_options = Configuration().get_logging();
    file_handler = logging.FileHandler(logging_options['logfile'])


    file_handler.setLevel(logging.WARNING)
    if 'logfocus' in logging_options:
        set_logfocus(logging_options['logfocus'])
        logging.getLogger(get_logfocus()).setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.name = "LMFDB"

    formatter = logging.Formatter(utils.LmfdbFormatter.fmtString.split(r'[')[0])
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    app.logger.addHandler(file_handler)


if True:
    # this bit is so that we can import website.py to use with gunicorn
    # and to setup logging before anything
    setup_logging()
    logging.info("Configuration = %s" % Configuration().get_all())

    _init()
    if [int(c) for c in sage.version.version.split(".")[:2]] < [int(c) for c in LMFDB_SAGE_VERSION.split(".")[:2]]:
        logging.warning("*** WARNING: SAGE VERSION %s IS OLDER THAN %s ***"%(sage.version.version,LMFDB_SAGE_VERSION))

# Import top-level modules that makeup the site
# Note that this necessarily includes everything, even code in still in an alpha state
import pages
assert pages
import api
assert api
import belyi
assert belyi
import bianchi_modular_forms
assert bianchi_modular_forms
import hilbert_modular_forms
assert hilbert_modular_forms
import half_integral_weight_forms
assert half_integral_weight_forms
import siegel_modular_forms
assert siegel_modular_forms
import modular_forms
assert modular_forms
import elliptic_curves
assert elliptic_curves
import ecnf
assert ecnf
import number_fields
assert number_fields
import lfunction_db
assert lfunction_db
import lfunctions
assert lfunctions
import genus2_curves
assert genus2_curves
import sato_tate_groups
assert sato_tate_groups
import users
assert users
import knowledge
assert knowledge
import characters
assert characters
import local_fields
assert local_fields
import galois_groups
assert galois_groups
import artin_representations
assert artin_representations
import tensor_products
assert tensor_products
import zeros
assert zeros
import crystals
assert crystals
import permutations
assert permutations
import hypergm
assert hypergm
import motives
assert motives
import riemann
assert riemann
import lattice
assert lattice
import higher_genus_w_automorphisms
assert higher_genus_w_automorphisms
import abvar
assert abvar
import abvar.fq
assert abvar.fq
import modlmf
assert modlmf
import rep_galois_modl
assert rep_galois_modl
import hecke_algebras
assert hecke_algebras
from inventory_app.inventory_app import inventory_app
assert inventory_app


def timestamp():
    return '[%s UTC]'%time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())

@app.before_request
def redirect_nonwww():
    """Redirect lmfdb.org requests to www.lmfdb.org"""
    from urlparse import urlparse, urlunparse
    urlparts = urlparse(request.url)
    if urlparts.netloc == 'lmfdb.org':
        replaced = urlparts._replace(netloc='www.lmfdb.org')
        return redirect(urlunparse(replaced), code=301)

@app.errorhandler(404)
def not_found_404(error):
    app.logger.info('%s 404 error for URL %s %s'%(timestamp(),request.url,error.description))
    messages = error.description if isinstance(error.description,(list,tuple)) else (error.description,)
    return render_template("404.html", title='LMFDB Page Not Found', messages=messages), 404

@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s %s"%(timestamp(),request.url, error.args))
    return render_template("500.html", title='LMFDB Error'), 500

@app.errorhandler(503)
def not_found_503(error):
    return render_template("503.html"), 503

#@app.route("/") is now handled in pages.py

def root_static_file(name):
    def static_fn():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
        if os.path.exists(fn):
            return open(fn).read()
        logging.critical("root_static_file: file %s not found!" % fn)
        return abort(404, 'static file %s not found.' % fn)
    app.add_url_rule('/%s' % name, 'static_%s' % name, static_fn)
map(root_static_file, ['favicon.ico'])


@app.route("/robots.txt")
def robots_txt():
    if "www.lmfdb.org".lower() in request.url_root.lower():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    # not running on www.lmfdb.org
    else:
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "default_robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    return "User-agent: *\nDisallow: / \n"

@app.route("/style.css")
def css():
    from lmfdb.config import Configuration
    color = Configuration().get_color()
    response = make_response(render_template("style.css", color_template=color))
    response.headers['Content-type'] = 'text/css'
    # don't cache css file, if in debug mode.
    if current_app.debug:
        response.headers['Cache-Control'] = 'no-cache, no-store'
    else:
        response.headers['Cache-Control'] = 'public, max-age=600'
    return response

@app.before_request
def get_menu_cookie():
    g.show_menu = request.cookies.get('showmenu') != "False"

@app.after_request
def set_menu_cookie(response):
    if hasattr(g, 'show_menu'):
        response.set_cookie("showmenu", str(g.show_menu))
    return response

@app.route('/_menutoggle/<show>')
def menutoggle(show):
    g.show_menu = show != "False"
    url = request.referrer or url_for('index')
    return redirect(url)

@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html", title="Not Yet Implemented")

# the checklist is used for human testing on a high-level, supplements test.sh

@app.route("/checklist-list")
def checklist_list():
    return render_template("checklist.html", body_class="checklist")


@app.route("/checklist")
def checklist():
    return render_template("checklist-fs.html")


def main():
    logging.info("main: ...done.")
    flask_options = Configuration().get_flask();

    if "profiler" in flask_options and flask_options["profiler"]:
        print "Profiling!"
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions = [30], sort_by=('cumulative','time','calls'))
        del flask_options["profiler"]

    app.run(**flask_options)




