# -*- encoding: utf-8 -*-

import sys
from flask import Flask, session, g, render_template, url_for, request, redirect
from pymongo import Connection
from sage.all import *
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

_C = None
 
def _init(dbport):
 global _C
 _C = Connection(port=dbport)

def getDBConnection():
  return _C

app = Flask(__name__)

# insert an empty info={} as default
@app.context_processor
def ctx_proc_userdata():
  return { 'info' : {} } 
