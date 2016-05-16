#-*- coding: utf8 -*-
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
import pages
import api
import hilbert_modular_forms
import siegel_modular_forms
import modular_forms
import elliptic_curves
import ecnf
import quadratic_twists
import plot_example
import number_fields
import lfunction_db
import lfunctions
# import maass_form_picard
# import maass_waveforms
import genus2_curves
import sato_tate_groups
import users
import knowledge
import upload
import characters
import local_fields
import galois_groups
import number_field_galois_groups
import artin_representations
import tensor_products
import zeros
import crystals
import permutations
import hypergm
import motives
import riemann
import logging
import lattice
import higher_genus_w_automorphisms
import modlmf
import rep_galois_modl


import raw
from modular_forms.maass_forms.picard import mwfp

import sys
#import base
from base import app, render_template, request, DEFAULT_DB_PORT, set_logfocus, _init

@app.errorhandler(404)
def not_found_404(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def not_found_500(error):
    return render_template("500.html"), 500


#@app.route("/")
#def index():
#    return render_template('index.html', titletag="The L-functions and modular forms database", title="", bread=None)


def root_static_file(name):
    from flask import redirect

    def static_fn():
        import os
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
        if os.path.exists(fn):
            return open(fn).read()
        import logging
        logging.critical("root_static_file: file %s not found!" % fn)
        return redirect(404)
    app.add_url_rule('/%s' % name, 'static_%s' % name, static_fn)
map(root_static_file, ['favicon.ico'])


@app.route("/robots.txt")
def robots_txt():
    if "www.lmfdb.org".lower() in request.url_root.lower():
        import os
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

@app.before_request
def get_menu_cookie():
    from flask import g
    g.show_menu = request.cookies.get('showmenu') != "False"

@app.after_request
def set_menu_cookie(response):
    from flask import g
    response.set_cookie("showmenu", str(g.show_menu))
    return response


@app.route('/_menutoggle/<show>')
def menutoggle(show):
    from flask import g, redirect
    g.show_menu = show != "False"
    url = request.referrer or url_for('index')
    return redirect(url)

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
    from flask import redirect
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
    flask_options = {"port": 37777, "host": "127.0.0.1", "debug": False}
    # Default option to pass to _init
    threading_opt = False 
    # the logfocus can be set to the string-name of a logger you want
    # follow on the debug level and all others will be set to warning
    logfocus = None
    #FIXME logfile isn't used
    logfile = "flasklog"

    # default options to pass to the MongoClient
    from pymongo import ReadPreference
    mongo_client_options = {"port": DEFAULT_DB_PORT, "host": "localhost", "replicaset": None, "read_preference": ReadPreference.NEAREST};
    read_preference_classes = {"PRIMARY": ReadPreference.PRIMARY, "PRIMARY_PREFERRED": ReadPreference.PRIMARY_PREFERRED , "SECONDARY": ReadPreference.SECONDARY, "SECONDARY_PREFERRED": ReadPreference.SECONDARY_PREFERRED, "NEAREST": ReadPreference.NEAREST };


        
    # deals with argv's
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
                                        "enable-profiler"
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
                flask_options["port"] = int(arg)
            elif opt in ("-h", "--host"):
                flask_options["host"] = arg
            #FIXME logfile isn't used
            elif opt in ("-l", "--log"):
                logfile = arg
            elif opt in ("--dbport"):
                mongo_client_options["port"] = int(arg)
            elif opt == "--debug":
                flask_options["debug"] = True
            elif opt == "--logfocus":
                logfocus = arg
                logging.getLogger(arg).setLevel(logging.DEBUG)
            # undocumented: the following allow changing the defaults for
            # these options to werkzeug (they both default to False unless
            # --debug is set, in which case they default to True but can
            # be turned off)
            elif opt == "--enable-reloader":
                flask_options["use_reloader"] = True
            elif opt == "--disable-reloader":
                flask_options["use_reloader"] = False
            elif opt == "--enable-debugger":
                flask_options["use_debugger"] = True
            elif opt == "--disable-debugger":
                flask_options["use_debugger"] = False
            elif opt =="--enable-profiler":
                flask_options["PROFILE"] = True
      except:
          pass # something happens on the server -> TODO: FIXME
    
    #deals with kwargs for mongoclient 
    import os
    #perhaps the filename could be an argv
    mongo_client_config_filename = "mongoclient.config"
    """
    Example mongoclient.config equivalent to default
    [db]
    port = 37010
    host = localhost
    replicaset =
    read_preference = NEAREST
    """
    config_dir = '/'.join( os.path.dirname(os.path.abspath(__file__)).split('/')[0:-1])
    mongo_client_config_filename = '{0}/{1}'.format(config_dir,mongo_client_config_filename)
    if os.path.exists(mongo_client_config_filename):
        from ConfigParser import ConfigParser;
        parser = ConfigParser()
        parser.read(mongo_client_config_filename);
        for key, value in parser.items("db"):
            if key in mongo_client_options.keys():
                if key == "port":
                    mongo_client_options["port"] = int(value);
                elif key == "read_preference":
                    if value in read_preference_classes:
                        mongo_client_options["read_preference"] = read_preference_classes[value];
                    else:
                        try:
                            mongo_client_options["read_preference"] = int(value);
                        except ValueError:
                            #it wasn't a number...
                            pass;
                elif key == "replicaset":
                    #if the string is empty
                    if not value:
                        #enforcing None to be the default if
                        mongo_client_options["replicaset"] = None
                    else: 
                        mongo_client_options["replicaset"] = value
                else:
                    mongo_client_options[key] = value        




    return { 'flask_options' : flask_options, 'mongo_client_options' : mongo_client_options}

configuration = None


def main():
    set_logfocus(logfocus)
    logging.info("... done.")

    # just for debugging
    # if options["debug"]:
    #  logging.info(str(app.url_map))

    global configuration
    if not configuration:
        configuration = get_configuration()
    if "PROFILE" in configuration['flask_options'] and configuration['flask_options']["PROFILE"]:
        print "Profiling!"
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions = [30], sort_by=('cumulative','time','calls'))
        del configuration['flask_options']["PROFILE"]

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

    if not configuration:
        configuration = get_configuration()
    logging.info("configuration: %s" % configuration)
    _init(**configuration['mongo_client_options'])
    app.logger.addHandler(file_handler)

def getDownloadsFor(path):
    return "bar"
