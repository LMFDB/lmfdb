# -*- coding: utf-8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import os
from flask import Flask, g, url_for

# logfocus
logfocus = None

def set_logfocus(lf):
    global logfocus
    logfocus = lf


def get_logfocus():
    return logfocus

def _init():
    # creates PostgresSQL connection
    from lmfdb.db_backend import db
    assert db

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

branch = "web"
if (os.getenv('BETA')=='1'):
    branch = "dev"

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
    vars['shortthanks'] = r'This project is supported by <a href="%s">grants</a> from the US National Science Foundation, the UK Engineering and Physical Sciences Research Council, and the Simons Foundation.' % (url_for('acknowledgment') + "#sponsors")
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
        git_contains_cmd = '''git branch --contains HEAD'''
        git_reflog_cmd = '''git reflog -n5'''
        rev = Popen([git_rev_cmd], shell=True, stdout=PIPE).communicate()[0]
        date = Popen([git_date_cmd], shell=True, stdout=PIPE).communicate()[0]
        contains = Popen([git_contains_cmd], shell=True, stdout=PIPE).communicate()[0]
        reflog = Popen([git_reflog_cmd], shell=True, stdout=PIPE).communicate()[0]
        pairs = [[git_rev_cmd, rev],
                [git_date_cmd, date],
                [git_contains_cmd, contains],
                [git_reflog_cmd, reflog]]
        summary = "\n".join([ "$ %s\n%s" % (c,o) for c, o in pairs] )
        cmd_output = rev, date,  summary
    except Exception:
        cmd_output = '-', '-', '-'
    return cmd_output

def git_summary():
    return "commit = %s\ndate = %s\ncontains = %s\nreflog = \n%s\n" % git_infos()


git_rev, git_date, _  = git_infos()
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
        from lmfdb.db_backend import db
        self.db = db
