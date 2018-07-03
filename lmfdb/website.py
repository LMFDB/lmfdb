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

# Import top-level modules that makeup the site
# Note that this necessarily includes everything, even clode in still in an alpha state
import pages
assert pages
import api
assert api
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

import logging
import utils
import os
import sys
import time
import getopt
from pymongo import ReadPreference
from base import app, set_logfocus, get_logfocus, _init
from flask import g, render_template, request, make_response, redirect, url_for, current_app, abort
import sage
from lmfdb.config import Configuration

DEFAULT_MONGODB_PORT = 27017
DEFAULT_POSTGRESQL_PORT = 5432
LMFDB_SAGE_VERSION = '7.1'
DEFAULT_USER_PASSWORD = ["lmfdb", "lmfdb"];

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
    return render_template("404.html", title='LMFDB page not found', messages=messages), 404

@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s %s"%(timestamp(),request.url, error.args))
    return render_template("500.html", title='LMFDB error'), 500

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
    response = make_response(render_template("style.css"))
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

#def usage():
#    print """
#Usage: %s [OPTION]...
#
#  -p, --port=NUM                bind to port NUM (default 37777)
#  -h, --host=HOST               bind to host HOST (default "127.0.0.1")
#  -l, --log=FILE                log to FILE (default "flasklog")
#      --debug                   enable debug mode
#      --help                    show this help
#      --logfocus=NAME           name of a logger to focus on
#
#  MongoDB options:
#  -m, --mongo-client=FILE       config file for connecting to MongoDB server (default is "mongoclient.config")
#      --mongo-host=HOST         connect to the MongoDB server on the given HOST
#      --mongo-port=PORT         connect to the MongoDB server on the given PORT (default %d)
#      --dbmon=NAME              monitor MongoDB commands to the specified database (use NAME=* to monitor everything, NAME=~DB to monitor all but DB)
#
#  PostgreSQL options:
#  -s, --postgresql-client=FILE  config file for connecting to PostgreSQL server (default is "postgresclient.config")
#      --postgresql-host=HOST    connect to the PostgreSQL server on the given HOST
#      --postgresql-port=PORT    connect to the PostgreSQL server on the given PORT (default %d)
#
#""" % (sys.argv[0], DEFAULT_MONGODB_PORT, DEFAULT_POSTGRESQL_PORT )
#
#def get_configuration():
#
#    # default flask options
#    flask_options = {"port": 37777, "host": "127.0.0.1", "debug": False}
#    logging_options = {"logfile": "flasklog"}
#
#    # default options to pass to the MongoClient
#    mongo_client_options = {"port": DEFAULT_MONGODB_PORT, "host": "m0.lmfdb.xyz", "replicaset": None, "read_preference": ReadPreference.NEAREST};
#    read_preference_classes = {"PRIMARY": ReadPreference.PRIMARY, "PRIMARY_PREFERRED": ReadPreference.PRIMARY_PREFERRED , "SECONDARY": ReadPreference.SECONDARY, "SECONDARY_PREFERRED": ReadPreference.SECONDARY_PREFERRED, "NEAREST": ReadPreference.NEAREST };
#
#    # default options to pass to the psycopg2.connect
#    postgresql_client_options = {"dbname": "lmfdb", "host": "devmirror.lmfdb.xyz", "port": 5432};
#    # default user/password
#    user_password = [DEFAULT_USER_PASSWORD];
#
#    #setups the default mongo_client_config_filename, postgres_client_config_filename, and passwords_yaml_filename
#    mongo_client_config_filename = "mongoclient.config"
#    postgres_client_config_filename = "postgresclient.config"
#    config_dir = '/'.join( os.path.dirname(os.path.abspath(__file__)).split('/')[0:-1])
#    mongo_client_config_filename = '{0}/{1}'.format(config_dir, mongo_client_config_filename)
#    postgres_client_config_filename = '{0}/{1}'.format(config_dir, postgres_client_config_filename)
#
#
#
#    if not 'sage' in sys.argv[0] and not sys.argv[0].endswith('nosetests'):
#        try:
#            opts, args = getopt.getopt(
#                                        sys.argv[1:],
#                                        "p:h:l:tm:s:",
#                                       [
#                                           "port=",
#                                           "host=",
#                                           "log=",
#                                           "logfocus=",
#                                           "dbmon=",
#                                           "debug",
#                                           "help",
#                                           "mongo-client=",
#                                           "mongo-port=",
#                                           "mongo-host=",
#                                           "postgresql-client=",
#                                           "postgresql-host=",
#                                           "postgresql-port=",
#                                            # undocumented, see below
#                                            "enable-reloader", "disable-reloader",
#                                            "enable-debugger", "disable-debugger",
#                                            "enable-profiler"
#                                            # not currently used
#                                            "threading"
#                                        ]
#                                       )
#        except getopt.GetoptError, err:
#            sys.stderr.write("%s: %s\n" % (sys.argv[0], err))
#            sys.stderr.write("Try '%s --help' for usage\n" % sys.argv[0])
#            sys.exit(2)
#
#        for opt, arg in opts:
#            if opt == "--help":
#                usage()
#                sys.exit(0)
#            elif opt in ("-p", "--port"):
#                flask_options["port"] = int(arg)
#            elif opt in ("-h", "--host"):
#                flask_options["host"] = arg
#            #FIXME logfile isn't used
#            elif opt in ("-l", "--log"):
#                logging_options["logfile"] = arg
#            elif opt in ("--dbmon"):
#                mongo_client_options["dbmon"] = arg
#            elif opt == "--debug":
#                flask_options["debug"] = True
#            elif opt == "--logfocus":
#                logging_options["logfocus"] = arg
#
#
#            # MongoDB options
#            elif opt in ("-m", "--mongo-client"):
#                if os.path.exists(arg):
#                    mongo_client_config_filename = arg
#                else:
#                    sys.stderr.write("%s doesn't exist\n" % arg);
#                    sys.exit(2);
#            elif opt == "--mongo-port":
#                mongo_client_options['port'] = int(arg)
#            elif opt == "--mongo-host":
#                mongo_client_options['host'] = arg
#
#            # PostgreSQL options
#            elif opt in ("-s", "--postgresql-client"):
#                if os.path.exists(arg):
#                    postgres_client_config_filename = arg
#                else:
#                    sys.stderr.write("%s doesn't exist\n" % arg);
#                    sys.exit(2);
#            elif opt == "--postgresql-port":
#                postgresql_client_options['port'] = int(arg)
#            elif opt == "--postgresql-host":
#                postgresql_client_options['host'] = arg
#
#
#
#
#            # undocumented: the following allow changing the defaults for
#            # these options to werkzeug (they both default to False unless
#            # --debug is set, in which case they default to True but can
#            # be turned off)
#            elif opt == "--enable-reloader":
#                flask_options["use_reloader"] = True
#            elif opt == "--disable-reloader":
#                flask_options["use_reloader"] = False
#            elif opt == "--enable-debugger":
#                flask_options["use_debugger"] = True
#            elif opt == "--disable-debugger":
#                flask_options["use_debugger"] = False
#            elif opt =="--enable-profiler":
#                flask_options["PROFILE"] = True
#
#    from ConfigParser import ConfigParser;
#    #reads the kwargs from  mongo_client_config_filename
#    if os.path.exists(mongo_client_config_filename):
#        loggin.info("Parsing mongo-client = %s" % mongo_client_config_filename);
#        parser = ConfigParser()
#        parser.read(mongo_client_config_filename);
#        for key, value in parser.items("db"):
#            if key == "read_preference":
#                if value in read_preference_classes:
#                    mongo_client_options["read_preference"] = read_preference_classes[value];
#                else:
#                    try:
#                        mongo_client_options["read_preference"] = int(value);
#                    except ValueError:
#                        #it wasn't a number...
#                        pass;
#            elif key == "replicaset":
#                #if the string is empty
#                if not value:
#                    #enforcing None to be the default if
#                    mongo_client_options["replicaset"] = None
#                else:
#                    mongo_client_options["replicaset"] = value
#            else:
#                # tries to see if it is an integer valued keyword argument, if so converts it
#                if value == "":
#                    value = None
#                else:
#                    try:
#                        value = int(value);
#                    except ValueError:
#                        pass;
#                mongo_client_options[key] = value;
#
#        if os.path.exists(postgres_client_config_filename):
#            logging.info("Parsing postgresql-client = %s" % postgres_client_config_filename)
#            parser = ConfigParser()
#            parser.read(postgres_client_config_filename);
#            for key, value in parser.items("db"):
#                if value == "":
#                    value = None
#                else:
#                    try:
#                        value = int(value);
#                    except ValueError:
#                        pass;
#                postgresql_client_options[key] = value;
#
#    return { 'flask_options' : flask_options, 'mongo_client_options' : mongo_client_options, 'postgresql_client_options' : postgresql_client_options, 'logging_options' : logging_options, 'user_password' : user_password}

configuration = None


def main():
    logging.info("... done.")

    if "profiler" in configuration['flask_options'] and configuration['flask_options']["profiler"]:
        print "Profiling!"
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions = [30], sort_by=('cumulative','time','calls'))
        del configuration['flask_options']["profiler"]

    app.run(**configuration['flask_options'])

if True:
    # this bit is so that we can import website.py to use with gunicorn
    if not configuration:
        configuration = Configuration().get_all()

    file_handler = logging.FileHandler(configuration['logging_options']['logfile'])
    file_handler.setLevel(logging.WARNING)
    if 'logfocus' in configuration['logging_options']:
        set_logfocus(configuration['logging_options']['logfocus'])
        logging.getLogger(get_logfocus()).setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.name = "LMFDB"

    formatter = logging.Formatter(utils.LmfdbFormatter.fmtString.split(r'[')[0])
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    logging.info("configuration: %s" % configuration)
    _init()
    app.logger.addHandler(file_handler)
    if [int(c) for c in sage.version.version.split(".")[:2]] < [int(c) for c in LMFDB_SAGE_VERSION.split(".")[:2]]:
        logging.warning("*** WARNING: SAGE VERSION %s IS OLDER THAN %s ***"%(sage.version.version,LMFDB_SAGE_VERSION))
