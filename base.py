import sys
from flask import Flask, session, g, render_template, url_for, request, redirect
from pymongo import Connection
from sage.all import *
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

# Do not change this, it breaks everyone else.
C = Connection(port=37010)
db = C.mf
lfuncs = db.lfuncs

app = Flask('__main__')
