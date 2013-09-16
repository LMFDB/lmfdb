# -*- coding: utf8 -*-
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
from base import *

import pages
import hilbert_modular_form
import siegel_modular_forms
import modular_forms
import elliptic_curves
import quadratic_twists
import plot_example
import number_fields
import lfunction_db
import lfunctions
# import maass_form_picard
# import maass_waveforms
import users
import knowledge
import upload
import characters
import local_fields
import galois_groups
import number_field_galois_groups
import artin_representations
import zeros
import crystals
import permutations
import hypergm
import motives
import logging

import raw
from modular_forms.maass_forms.picard import mwfp

import sys

try:
    import password
    logging.info("password imported")
    readwrite_password = password.readwrite_password
except:
    logging.warning("no password!")
    readwrite_password = ''


@app.errorhandler(404)
def not_found_404(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def not_found_500(error):
    return render_template("500.html"), 500


@app.route("/")
def index():
    return render_template('index.html', titletag="The L-functions and modular forms database", title="", bread=None)


def root_static_file(name):
    import flask

    def static_fn():
        import os
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
        if os.path.exists(fn):
            return open(fn).read()
        import logging
        logging.critical("root_static_file: file %s not found!" % fn)
        return flask.redirect(404)
    app.add_url_rule('/%s' % name, 'static_%s' % name, static_fn)
map(root_static_file, ['favicon.ico'])


@app.route("/robots.txt")
def robots_txt():
    if "www.lmfdb.org".lower() in request.url_root.lower():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    return "User-agent: *\nDisallow: / \n"


# TODO what is that? we have git now btw ...
@app.route("/hg/<arg>")
def hg(arg):
    if arg == "":
        return "Use /hg/parent, /hg/log or /hg/identify"
    import os
    if arg == "parent":
        f = os.popen("hg parent")
    elif arg == "tip":
        f = os.popen("hg tip")
    elif arg == "identify":
        f = os.popen("hg identify")
    else:
        return "Unrecognized command. Allowed are parent, tip and identify."
    text = f.read()
    return str(text)


@app.route("/style.css")
def css():
    from flask import make_response
    response = make_response(render_template("style.css"))
    response.headers['Content-type'] = 'text/css'
    # don't cache css file, if in debug mode.
    from flask import current_app
    if current_app.debug:
        response.headers['Cache-Control'] = 'no-cache, no-store'
    else:
        response.headers['Cache-Control'] = 'public, max-age=600'
    return response


@app.route('/a/<int:a>')
def a(a):
    a = Integer(a)
    return r'\(' + str(a / (1 + a)) + r'\)'


@app.route("/example/")
@app.route("/example/<blah>")
def example(blah=None):
    return render_template("example.html", blah=blah)


@app.route("/modular/")
@app.route("/ModularForm/")
@app.route("/AutomorphicForm/")
def modular_form_toplevel():
    return redirect(url_for("mf.render_modular_form_main_page"))
    # return render_template("modular_form_space.html", info = { })


@app.route("/calc")
def calc():
    return request.args['ep']


@app.route("/form")
def form_example():
    sidebar = [('topic1', [("abc", "#"), ("def", "#")]), ("topic2", [("ghi", "#"), ("jkl", "#")])]
    info = {'sidebar': sidebar}
    return render_template("form.html", info=info)

@app.route('/ModularForm/GSp/Q')
@app.route('/ModularForm/GSp/Q/<group>')
@app.route('/ModularForm/GSp/Q/<group>/<page>')
@app.route('/ModularForm/GSp/Q/<group>/<page>/<weight>')
@app.route('/ModularForm/GSp/Q/<group>/<page>/<weight>/<form>')
def ModularForm_GSp4_Q_top_level(group=None, page=None, weight=None, form=None):
    args = request.args
    if group:
        args = {}
        for k in request.args:
            args[k] = request.args[k]
        args['group'] = group
        if None != weight:
            page = 'specimen'
        args['page'] = page
        if 'specimen' == page:
            args['weight'] = weight
            args['form'] = form
    return siegel_modular_forms.siegel_modular_form.render_webpage(args)


@app.route('/example_plot')
def render_example_plot():
    return plot_example.render_plot(request.args)


@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html", title="Not Yet Implemented")

# the checklist is for testing on a high-level


@app.route("/checklist-list")
def checklist_list():
    return render_template("checklist.html", body_class="checklist")


@app.route("/checklist")
def checklist():
    return render_template("checklist-fs.html")


def usage():
    print """
Usage: %s [OPTION]...

  -p, --port=NUM      bind to port NUM (default 37777)
  -h, --host=HOST     bind to host HOST (default "127.0.0.1")
  -l, --log=FILE      log to FILE (default "flasklog")
  -t, --threading     multithread the database authentications
      --dbport=NUM    bind the MongoDB to the given port (default base.DEFAULT_DB_PORT)
      --debug         enable debug mode
      --logfocus=NAME enter name of logger to focus on
      --help          show this help
""" % sys.argv[0]

def get_configuration():
    global logfocus
        # I don't think that this global variable does anything at all,
        # but let's keep track of it anyway.

    # default options to pass to the app.run()
    options = {"port": 37777, "host": "127.0.0.1", "debug": False}
    # Default option to pass to _init
    threading_opt = False 
    # the logfocus can be set to the string-name of a logger you want
    # follow on the debug level and all others will be set to warning
    logfocus = None
    logfile = "flasklog"
    import base
    dbport = base.DEFAULT_DB_PORT
    if not sys.argv[0].endswith('nosetests'):
      try:
        import getopt
        try:
            opts, args = getopt.getopt(sys.argv[1:],
                                       "p:h:l:t",
                                       ["port=", "host=", "dbport=", "log=", "logfocus=", "debug", "help", "threading", 
                                        # undocumented, see below
                                        "enable-reloader", "disable-reloader",
                                        "enable-debugger", "disable-debugger",
                                        ])
        except getopt.GetoptError, err:
            sys.stderr.write("%s: %s\n" % (sys.argv[0], err))
            sys.stderr.write("Try '%s --help' for usage\n" % sys.argv[0])
            #sys.exit(2)

        for opt, arg in opts:
            if opt == "--help":
                usage()
                sys.exit()
            elif opt in ("-p", "--port"):
                options["port"] = int(arg)
            elif opt in ("-h", "--host"):
                options["host"] = arg
            elif opt in ("-t", "--threading"):
                threading_opt = True
            elif opt in ("-l", "--log"):
                logfile = arg
            elif opt in ("--dbport"):
                dbport = int(arg)
            elif opt == "--debug":
                options["debug"] = True
            elif opt == "--logfocus":
                logfocus = arg
                logging.getLogger(arg).setLevel(logging.DEBUG)
            # undocumented: the following allow changing the defaults for
            # these options to werkzeug (they both default to False unless
            # --debug is set, in which case they default to True but can
            # be turned off)
            elif opt == "--enable-reloader":
                options["use_reloader"] = True
            elif opt == "--disable-reloader":
                options["use_reloader"] = False
            elif opt == "--enable-debugger":
                options["use_debugger"] = True
            elif opt == "--disable-debugger":
                options["use_debugger"] = False
      except:
          pass # something happens on the server -> TODO: FIXME
    return { 'flask_options' : options, 'dbport' : dbport , 'threading_opt' : threading_opt }

configuration = get_configuration()

def main():
    base.set_logfocus(logfocus)
    logging.info("... done.")

    # just for debugging
    # if options["debug"]:
    #  logging.info(str(app.url_map))

    app.run(**configuration['flask_options'])

if True:
    # this bit is so that we can import website.py to use
    # with gunicorn.
    import logging
    logfile = "flasklog"
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.WARNING)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.name = "LMFDB"

    import utils
    formatter = logging.Formatter(utils.LmfdbFormatter.fmtString.split(r'[')[0])
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    logging.info("configuration: %s" % configuration)
    import base
    base._init(configuration['dbport'], readwrite_password, parallel_authentication = configuration["threading_opt"])
    app.logger.addHandler(file_handler)

def getDownloadsFor(path):
    return "bar"
