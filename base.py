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
from pymongo import Connection
from pymongo.cursor import Cursor                                                             
from pymongo.errors import AutoReconnect  
from pymongo.connection import Connection
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

# global db connection instance
_C = None

readonly_dbs = [ 'HTPicard', 'Lfunction', 'Lfunctions', 'MaassWaveForm',
        'ellcurves', 'elliptic_curves', 'hmfs', 'modularforms', 'modularforms_2010',
        'mwf_dbname', 'numberfields', 'quadratic_twists', 'test', 'limbo']

readwrite_dbs = ['userdb', 'upload', 'knowledge']

readonly_username = 'lmfdb'
readonly_password = 'readonly'

readwrite_username = 'lmfdb_website'

AUTO_RECONNECT_MAX = 10
AUTO_RECONNECT_DELAY = 1
AUTO_RECONNECT_ATTEMPTS = 0

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
      except AutoReconnect, e:
        AUTO_RECONNECT_ATTEMPTS += 1
        if AUTO_RECONNECT_ATTEMPTS > AUTO_RECONNECT_MAX:
           AUTO_RECONNECT_ATTEMPTS = 0
           import flask
           flask.flash("AutoReconnect failed to reconnect", "error")
           raise
        logging.warning('AutoReconnect #%d - %s raised [%s]' % (AUTO_RECONNECT_ATTEMPTS, func.__name__, e))
        sleep(AUTO_RECONNECT_DELAY)
  return retry

# disabling this reconnect thing, doesn't really help anyways
#Cursor._Cursor__send_message = _db_reconnect(Cursor._Cursor__send_message)
#Connection._send_message = _db_reconnect(Connection._send_message)
#Connection._send_message_with_response = _db_reconnect(Connection._send_message_with_response)

 
def _init(dbport, readwrite_password):
    global _C
    logging.info("establishing db connection at port %s ..." % dbport)
    _C = Connection(port=dbport)
    
    def db_auth_task(db, readonly=False):
        if readonly or readwrite_password == '':
            _C[db].authenticate(readonly_username, readonly_password)
            logging.info("authenticated readonly on database %s" % db)
        else:
            _C[db].authenticate(readwrite_username, readwrite_password)
            logging.info("authenticated readwrite on database %s" % db)

    import threading
    tasks = []
    for db in readwrite_dbs:
      t = threading.Thread(target=db_auth_task, args=(db,))
      t.start()
      tasks.append(t)
    for db in readonly_dbs:
      t = threading.Thread(target=db_auth_task, args=(db,True))
      t.start()
      tasks.append(t)

    for t in tasks: t.join(timeout=15)
    logging.info(">>> db auth done")

def getDBConnection():
  return _C

app = Flask(__name__)

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True

# the following context processor inserts
#  * empty info={} dict variable
#  * body_class = ''
#  * bread = [...] for the default bread crumb hierarch
#  * title = 'test string'
@app.context_processor
def ctx_proc_userdata():
  # insert an empty info={} as default
  # set the body class to some default, blueprints should
  # overwrite it with their name, using @<blueprint_object>.context_processor
  # see http://flask.pocoo.org/docs/api/?highlight=context_processor#flask.Blueprint.context_processor
  vars = { 'info' : {}, 'body_class' : '' }

  # insert the default bread crumb hierarchy
  # overwrite this variable when you want to customize it
  vars['bread'] = None #[ ('Bread', '.'), ('Crumb', '.'), ('Hierarchy', '.')]
  
  # default title
  vars['title'] = r'LMFDB'
  # meta_description appears in the meta tag "description"
  import knowledge
  vars['meta_description'] = knowledge.knowl.Knowl("intro.description").content
  vars['shortthanks'] = r'This project is supported by <a href="%s">grants</a> from the National Science Foundation.'% (url_for('acknowledgment') + "#sponsors")
  vars['feedbackpage'] = r"https://docs.google.com/spreadsheet/viewform?formkey=dDJXYXBleU1BMTFERFFIdjVXVmJqdlE6MQ"
  vars['LINK_EXT'] = lambda a,b : '<a href="%s" target="_blank">%s</a>' % (b, a)

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

@app.template_filter('obfuscate_email')
def obfuscate_email(email):
    """
    obfuscating the email
    TODO: doesn't work yet
    """
    return u"%s…@…%s" % (email[:2],email[-2:])

@app.template_filter('urlencode')
def urlencode(kwargs):
  import urllib
  return urllib.urlencode(kwargs)

### start: link to google code at the bottom

def safe_url_link_from_hg(url, display_txt):
  try:
    from subprocess import Popen, PIPE
    hg_cmd = '''hg parent --template '<a href="%s">%s</a>' ''' % (url, display_txt)
    cmd_output = Popen([hg_cmd], shell=True, stdout=PIPE).communicate()[0]
  except e:
    cmd_output = ''
  return cmd_output
  
"""
Creates google code link to the source code at the most recent commit.
"""
_url_source = 'http://code.google.com/p/lmfdb/source/browse/?r={node}'
_txt_source = 'Source'
_current_source = safe_url_link_from_hg(_url_source, _txt_source)
"""
Creates google code link to the list of revisions on the master, where the most recent commit is on top.
"""
_url_changeset =  'http://code.google.com/p/lmfdb/source/list?r={node}'
_txt_changeset = '{date|isodate}'
_latest_changeset = safe_url_link_from_hg(_url_changeset, _txt_changeset)

@app.context_processor
def link_to_current_source():
  return {'current_source': _current_source, 'latest_changeset' : _latest_changeset }

### end: google code links


### for testing.py ###
import unittest
class LmfdbTest(unittest.TestCase):
  def setUp(self):
    app.config['TESTING'] = True
    self.app = app
    self.tc = app.test_client()
    import website
    self.C = getDBConnection()

