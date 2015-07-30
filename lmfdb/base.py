# -*- coding: utf8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import sys
import logging
from time import sleep
from flask import Flask, session, g, render_template, url_for, request, redirect
from pymongo.cursor import Cursor
from pymongo.errors import AutoReconnect
from sage.all import *
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

# logfocus
logfocus = None


def set_logfocus(lf):
    global logfocus
    logfocus = lf


def get_logfocus():
    global logfocus
    return logfocus

# global db connection instance (will be set by the first call to
# getDBConnection() and should always be obtained from that)
_C = None

def getDBConnection():
    return _C

def makeDBConnection(dbport):
    global _C
    if not _C:
        logging.info("establishing db connection at port %s ..." % dbport)
        import pymongo
        logging.info("using pymongo version %s" % pymongo.version)
        if pymongo.version_tuple[0] < 3:
            from pymongo import Connection
            _C = Connection(port=dbport)
        else:
            from pymongo.mongo_client import MongoClient
            _C = MongoClient(port=dbport)

# Note: the original intention was to have all databases and
# collections read-only except to users who could authenticate
# themselves with a password.  But this never worked, and this list
# (which is in any case incomplete) is now redundant.

readonly_dbs = ['HTPicard', 'Lfunction', 'Lfunctions', 'MaassWaveForm',
                'ellcurves', 'elliptic_curves', 'hmfs', 'modularforms', 'modularforms_2010',
                'mwf_dbname', 'numberfields', 'quadratic_twists', 'test', 'limbo']

readwrite_dbs = ['userdb', 'upload', 'knowledge']

readonly_username = 'lmfdb'
readonly_password = 'readonly'

readwrite_username = 'lmfdb_website'

AUTO_RECONNECT_MAX = 10
AUTO_RECONNECT_DELAY = 1
AUTO_RECONNECT_ATTEMPTS = 0
DEFAULT_DB_PORT = 37010
dbport = DEFAULT_DB_PORT


def _db_reconnect(func):
    """
    Wrapper to automatically reconnect when mongodb throws a AutoReconnect exception.

    See
      * http://stackoverflow.com/questions/5287621/occasional-connectionerror-cannot-connect-to-the-database-to-mongo
      * http://paste.pocoo.org/show/224441/
    and similar workarounds
    """
    def retry(*args, **kwargs):
        global AUTO_RECONNECT_ATTEMPTS
        while True:
            try:
                return func(*args, **kwargs)
            except AutoReconnect as e:
                AUTO_RECONNECT_ATTEMPTS += 1
                if AUTO_RECONNECT_ATTEMPTS > AUTO_RECONNECT_MAX:
                    AUTO_RECONNECT_ATTEMPTS = 0
                    import flask
                    flask.flash("AutoReconnect failed to reconnect", "error")
                    raise
                logging.warning(
                    'AutoReconnect #%d - %s raised [%s]' % (AUTO_RECONNECT_ATTEMPTS, func.__name__, e))
                sleep(AUTO_RECONNECT_DELAY)
    return retry

# disabling this reconnect thing, doesn't really help anyways
# Cursor._Cursor__send_message = _db_reconnect(Cursor._Cursor__send_message)
# Connection._send_message = _db_reconnect(Connection._send_message)
# Connection._send_message_with_response =
# _db_reconnect(Connection._send_message_with_response)


def _init(dbport, readwrite_password, parallel_authentication=False):
    makeDBConnection(dbport)
    C = getDBConnection()

    # Disabling authentication completely as it does not work:
    return

    def db_auth_task(db, readonly=False):
        if readonly or readwrite_password == '':
            C[db].authenticate(readonly_username, readonly_password)
            logging.info("authenticated readonly on database %s" % db)
        else:
            C[db].authenticate(readwrite_username, readwrite_password)
            logging.info("authenticated readwrite on database %s" % db)

    if parallel_authentication:
        logging.info("Authenticating to the databases in parallel")
        import threading
        tasks = []
        for db in readwrite_dbs:
            t = threading.Thread(target=db_auth_task, args=(db,))
            t.start()
            tasks.append(t)
        for db in readonly_dbs:
            t = threading.Thread(target=db_auth_task, args=(db, True))
            t.start()
            tasks.append(t)

        for t in tasks:
            t.join(timeout=15)
        logging.info(">>> db auth done")
    else:
        logging.info("Authenticating sequentially")
        for db in readwrite_dbs:
            db_auth_task(db)
        for db in readonly_dbs:
            db_auth_task(db, True)
        logging.info(">>> db auth done")

app = Flask(__name__)

# If the debug toolbar is installed then use it
if app.debug:
    try:
        from flask_debugtoolbar import DebugToolbarExtension
        app.config['SECRET_KEY'] = '''shh, it's a secret'''
        toolbar = DebugToolbarExtension(app)
    except ImportError:
        pass

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True

# enable break and continue in jinja loops
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# the following context processor inserts
#  * empty info={} dict variable
#  * body_class = ''
#  * bread = [...] for the default bread crumb hierarch
#  * title = 'test string'


def is_debug_mode():
    from flask import current_app
    return current_app.debug

@app.before_request
def set_beta_state():
    g.BETA = os.getenv('BETA') is not None or is_debug_mode()

@app.context_processor
def ctx_proc_userdata():
    # insert an empty info={} as default
    # set the body class to some default, blueprints should
    # overwrite it with their name, using @<blueprint_object>.context_processor
    # see http://flask.pocoo.org/docs/api/?highlight=context_processor#flask.Blueprint.context_processor
    vars = {'info': {}, 'body_class': ''}

    # insert the default bread crumb hierarchy
    # overwrite this variable when you want to customize it
    vars['bread'] = None  # [ ('Bread', '.'), ('Crumb', '.'), ('Hierarchy', '.')]

    # default title
    vars['title'] = r'LMFDB'

    # meta_description appears in the meta tag "description"
    import knowledge
    vars['meta_description'] = knowledge.knowl.Knowl("intro.description").content
    vars['shortthanks'] = r'This project is supported by <a href="%s">grants</a> from the US National Science Foundation and the UK Engineering and Physical Sciences Research Council.' % (url_for('acknowledgment') + "#sponsors")
#    vars['feedbackpage'] = url_for('contact')
    vars['feedbackpage'] = r"https://docs.google.com/spreadsheet/viewform?formkey=dDJXYXBleU1BMTFERFFIdjVXVmJqdlE6MQ"
    vars['LINK_EXT'] = lambda a, b: '<a href="%s" target="_blank">%s</a>' % (b, a)

    # debug mode?
    vars['DEBUG'] = is_debug_mode()
    vars['BETA'] = g.BETA

    return vars


# datetime format in jinja templates
# you can now pass in a datetime.datetime python object and via
# {{ <datetimeobject>|fmtdatetime }} you can format it right inside the template
# if you want to do more than just the default, use it for example this way:
# {{ <datetimeobject>|fmtdatetime('%H:%M:%S') }}
@app.template_filter("fmtdatetime")
def fmtdatetime(value, format='%Y-%m-%d %H:%M:%S'):
    import datetime
    if isinstance(value, datetime.datetime):
        return value.strftime(format)
    else:
        return "-"


@app.template_filter("nl2br")
def nl2br(s):
    return s.replace('\n', '<br>\n')


@app.template_filter('obfuscate_email')
def obfuscate_email(email):
    """
    obfuscating the email
    TODO: doesn't work yet
    """
    return u"%s…@…%s" % (email[:2], email[-2:])


@app.template_filter('urlencode')
def urlencode(kwargs):
    import urllib
    return urllib.urlencode(kwargs)

# start: link to google code at the bottom


def git_infos():
    try:
        from subprocess import Popen, PIPE
        git_rev_cmd = '''git rev-parse HEAD'''
        git_date_cmd = '''git show --format="%ci" -s HEAD'''
        rev = Popen([git_rev_cmd], shell=True, stdout=PIPE).communicate()[0]
        date = Popen([git_date_cmd], shell=True, stdout=PIPE).communicate()[0]
        cmd_output = rev, date
    except e:
        cmd_output = '-', '-'
    return cmd_output

git_rev, git_date = git_infos()
from sage.env import SAGE_VERSION

"""
Creates link to the source code at the most recent commit.
"""
_url_source = 'https://github.com/LMFDB/lmfdb/tree/'
_current_source = '<a href="%s%s">%s</a>' % (_url_source, git_rev, "Source")
"""
Creates link to the list of revisions on the master, where the most recent commit is on top.
"""
_url_changeset = 'https://github.com/LMFDB/lmfdb/commit/'
_latest_changeset = '<a href="%s%s">%s</a>' % (_url_changeset, git_rev, git_date)


@app.context_processor
def link_to_current_source():
    return {'current_source': _current_source,
            'latest_changeset': _latest_changeset,
            'sage_version': 'SageMath version %s' % SAGE_VERSION}

# end: google code links


# for testing.py ###
import unittest2


class DoctestExampleTest(object):

    """
    This is a general purpose class with a doctest
    """

    def __init__(self, k):
        self.k = k

    def i_am_tested(self, n):
        """
        >>> det = DoctestExampleTest(5)
        >>> det.i_am_tested(1)
        47
        """
        return n * 42 + self.k

    def __str__(self):
        """
        >>> det = DoctestExampleTest(42)
        >>> print(det)
        I am 42
        """
        return "I am %d" % self.k


class LmfdbTest(unittest2.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.app = app
        self.tc = app.test_client()
        import lmfdb.website
        self.C = getDBConnection()
