# -*- coding: utf8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import os
import logging
from time import sleep
from flask import Flask, g, url_for, abort
import pymongo
from pymongo import MongoClient, MongoReplicaSetClient
from pymongo.cursor import Cursor
from pymongo.errors import AutoReconnect
from os.path import dirname, join

# logfocus
logfocus = None

def set_logfocus(lf):
    global logfocus
    logfocus = lf


def get_logfocus():
    return logfocus

# global db connection instance (will be set by the first call to
# getDBConnection() and should always be obtained from that)
_mongo_C = None
_mongo_port = None
_mongo_kwargs = None
_mongo_user = None
_mongo_pass = None
_mongo_dbmon = None

# simple event logger that logs commands sent to mongo db
# it will be used only if --dbmon is specified when the LMFDB server is started
# this implementation assumes pymongo is begin used synchronously (currently true in the LMFDB, even on the webserver we fork rather than thread)
# it would need to be modified to support multi-threading (although it would still work when _mongo_dbmon=None)
from pymongo import monitoring
class MongoEventLogger(monitoring.CommandListener):
    def __init__(self):
        self._last_request = 0
    def started(self, event):
        if not _mongo_dbmon or event.database_name == _mongo_dbmon or _mongo_dbmon[0] == '~' and event.database_name != _mongo_dbmon[1:]:
            logging.info("mongo db command %s(%x) on db %s with args %s"%(event.command_name,event.request_id,event.database_name,event.command))
            self._last_request = event.request_id
    def succeeded(self, event):
        if not _mongo_dbmon or event.request_id == self._last_request:
            logging.info("mongo db command %s(%x) took %.3fs"%(event.command_name,event.request_id,event.duration_micros/1000000.0))
    def failed(self, event):
        logging.info("mongo db command %s(%x) failed after %.3fs with error %s"%(event.command_name,event.request_id,event.duration_micros/1000000.0,event.failure))

def getDBConnection():
    if not _mongo_C:
        makeDBConnection()
        if not _mongo_C:
            abort(503)
    return _mongo_C

def configureDBConnection(port, **kwargs):
    global _mongo_port, _mongo_kwargs, _mongo_user, _mongo_pass, _mongo_dbmon

    if "dbmon" in kwargs:
        _mongo_dbmon = kwargs.pop("dbmon")
        if _mongo_dbmon == '*':
            _mongo_dbmon = ''
        kwargs["event_listeners"] = [MongoEventLogger()]

    _mongo_port = port
    _mongo_kwargs = kwargs
    pw_filename = join(dirname(dirname(__file__)), "password")
    try:
        _mongo_user = "webserver"
        _mongo_pass = open(pw_filename, "r").readlines()[0].strip()
    except:
        # file not found or any other problem
        # this is read-only everywhere
        logging.warning("authentication: no password -- fallback to read-only access")
        _mongo_user = "lmfdb"
        _mongo_pass = "lmfdb"

def makeDBConnection():
    global _mongo_C

    logging.info("attempting to establish mongo db connection on port %s ..." % _mongo_port)
    logging.info("using pymongo version %s" % pymongo.version)
    try:
        if pymongo.version_tuple[0] >= 3 or _mongo_kwargs.get("replicaset",None) is None:
            _mongo_C = MongoClient(port = _mongo_port,  **_mongo_kwargs)
        else:
            _mongo_C = MongoReplicaSetClient(port = _mongo_port,  **_mongo_kwargs)
        mongo_info = _mongo_C.server_info()
        logging.info("mongodb version: %s" % mongo_info["version"])
        logging.info("_mongo_C = %s", (_mongo_C,) )
        #the reads are not necessarily from host/address
        #those depend on the cursor, and can be checked with cursor.conn_id or cursor.address 
        if pymongo.version_tuple[0] >= 3:
            logging.info("_mongo_C.address = %s" % (_mongo_C.address,) )
        else:
            logging.info("_mongo_C.host = %s" % (_mongo_C.host,) )

        logging.info("_mongo_C.nodes = %s" %  (_mongo_C.nodes,) )
        logging.info("_mongo_C.read_preference = %s" %  (_mongo_C.read_preference,) )

        try:
            _mongo_C["admin"].authenticate(_mongo_user, _mongo_pass)
            if _mongo_user == "webserver":
                logging.info("authentication: partial read-write access enabled")
        except pymongo.errors.PyMongoError as err:
            logging.error("authentication: FAILED -- aborting")
            raise err
        #read something from the db    
        #and check from where was it read
        if pymongo.version_tuple[0] >= 3:
            cursor = _mongo_C.userdb.users.find({},{'_id':True}).limit(-1)
            list(cursor)
            logging.info("MongoClient conection is reading from: %s" % (cursor.address,));
        elif _mongo_kwargs.get("replicaset",None) is not None:
            cursor = _mongo_C.userdb.users.find({},{'_id':True}).limit(-1)
            list(cursor)
            logging.info("MongoReplicaSetClient connection is reading from: %s" % (cursor.conn_id,));
        else:
            logging.info("MongoClient conection is reading from: %s" % (_mongo_C.host,));
    except Exception as err:
        logging.info("connection attempt failed: %s", err)
        _mongo_C = None
        return


# Global to track of many auto reconnect attempts for _db_reconnect
AUTO_RECONNECT_ATTEMPTS = 0

def _db_reconnect(func):
    """
    Wrapper to automatically reconnect when mongodb throws a AutoReconnect exception.
    See
      * http://stackoverflow.com/questions/5287621/occasional-connectionerror-cannot-connect-to-the-database-to-mongo
      * http://paste.pocoo.org/show/224441/
    and similar workarounds
    """
    # maximum number of auto reconnect attempts
    AUTO_RECONNECT_MAX = 3 # there is no reason to make this large, if the database is down we may as well wait for the user to hit refresh or click on something before trying again
    # delay between attempts
    AUTO_RECONNECT_DELAY = 1

    def retry(*args, **kwargs):
        global AUTO_RECONNECT_ATTEMPTS
        while True:
            try:
                return func(*args, **kwargs)
            except AutoReconnect as e:
                AUTO_RECONNECT_ATTEMPTS += 1
                if AUTO_RECONNECT_ATTEMPTS > AUTO_RECONNECT_MAX:
                    AUTO_RECONNECT_ATTEMPTS = 0
                    abort(503)
                logging.warning(
                    'AutoReconnect #%d - %s raised [%s]' % (AUTO_RECONNECT_ATTEMPTS, func.__name__, e))
                sleep(AUTO_RECONNECT_DELAY)
                makeDBConnection()
    return retry

# disabling this reconnect thing, doesn't really help anyways
Cursor._Cursor__send_message = _db_reconnect(Cursor._Cursor__send_message)

def _init(port, **kwargs):
    configureDBConnection(port, **kwargs)
    makeDBConnection()

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
app.jinja_env.add_extension('jinja2.ext.do')

# the following context processor inserts
#  * empty info={} dict variable
#  * body_class = ''
#  * bread = [...] for the default bread crumb hierarch
#  * title = 'test string'


def is_debug_mode():
    from flask import current_app
    return current_app.debug

branch = "prod"
if (os.getenv('BETA')=='1'):
    branch = "beta"

@app.before_request
def set_beta_state():
    g.BETA = (os.getenv('BETA')=='1') or is_debug_mode()

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
    vars['meta_description'] = r'Welcome to the LMFDB, the database of L-functions, modular forms, and related objects. These pages are intended to be a modern handbook including tables, formulas, links, and references for L-functions and their underlying objects.'
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
    except:
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
_url_changeset = 'https://github.com/LMFDB/lmfdb/commits/%s' % branch
_latest_changeset = '<a href="%s">%s</a>' % (_url_changeset, git_date)


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
        assert lmfdb.website
        self.C = getDBConnection()
