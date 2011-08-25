# -*- encoding: utf-8 -*-

import sys
import logging
from flask import Flask, session, g, render_template, url_for, request, redirect
from pymongo import Connection
from sage.all import *
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

_C = None
 
def _init(dbport):
  global _C
  # always re-connecting, there are those "AutoReconnect/Connection refused" problems.
  # maybe related?
  #
  #if not _C:
  #  logging.info("establishing db connection at port %s" % dbport)
  _C = Connection(port=dbport, network_timeout=1)

def getDBConnection():
  return _C

app = Flask(__name__)

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
  vars['bread'] = [ ('Bread', '.'), ('Crumb', '.'), ('Hierarchy', '.')]
  
  # default title
  vars['title'] = r'Title variable "title" has not been set. This is a test: \( \LaTeX \) and \( \frac{1}{1+x+x^2} \) and more ...'
  return vars


# datetime format in jinja templates
# you can now pass in a datetime.datetime python object and via
# {{ <datetimeobject>|fmtdatetime }} you can format it right inside the template
# if you want to do more than just the default, use it for example this way:
# {{ <datetimeobject>|fmtdatetime('%H:%M:%S') }}
@app.template_filter("fmtdatetime")
def fmtdatetime(value, format='%Y-%m-%d %H:%M:%S'):
    return value.strftime(format)

@app.template_filter('obfuscate_email')
def obfuscate_email(email):
    """
    obfuscating the email
    TODO: doesn't work yet
    """
    return u"%s…@…%s" % (email[:2],email[-2:])

