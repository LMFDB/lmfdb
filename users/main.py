# -*- encoding: utf-8 -*-
# this holds all the flask-login specific logic (+ url mapping an rendering templates)
# for the user management
# author: harald schilly <harald.schilly@univie.ac.at>

import pymongo
ASC = pymongo.ASCENDING
import flask
from functools import wraps
from base import app, getDBConnection
from flask import render_template, request, abort, Blueprint, url_for, make_response
from flaskext.login import login_required, login_user, current_user, logout_user

login_page = Blueprint("users", __name__, template_folder='templates')
import utils
logger = utils.make_logger(login_page)

import re
allowed_usernames = re.compile("^[a-zA-Z0-9._-]+$")

from flaskext.login import LoginManager
login_manager = LoginManager()

import pwdmanager
from pwdmanager import LmfdbUser, LmfdbAnonymousUser

# TODO update this url, needed for the user login token
base_url = "http://www.l-functions.org"

@login_manager.user_loader
def load_user(userid):
  from pwdmanager import LmfdbUser
  return LmfdbUser(userid) 

login_manager.login_view = "users.info"

# this anonymous user has the is_admin() method
login_manager.anonymous_user = LmfdbAnonymousUser

# globally define the user and username
@app.context_processor
def ctx_proc_userdata():
  userdata = {}
  userdata['username'] = 'Anonymous' if current_user.is_anonymous() else current_user.name
  userdata['user_is_authenticated'] =  current_user.is_authenticated()
  userdata['user_is_admin'] = current_user.is_admin()
  return userdata

# blueprint specific definition of the body_class variable
@login_page.context_processor
def body_class():
  return { 'body_class' : 'login' }

# the following doesn't work as it should, also depends on blinker python lib
# flask signal when a user logs in. we record the last logins in the user's data
# http://flask.pocoo.org/docs/signals/
#def log_login_callback(cur_app, user = None):
#  cur_user = user or current_user 
#  logger.info(">> curr_app: %s   user: %s" % (cur_app, cur_user))
#
#from flaskext.login import user_logged_in, user_login_confirmed
#user_logged_in.connect(log_login_callback)
#user_login_confirmed.connect(log_login_callback)


def base_bread():
  return [('Users', url_for(".list"))]

@login_page.route("/")
@login_required
def list():
  import pwdmanager
  users = pwdmanager.get_user_list()
  # trying to be smart and sorting by last name
  users = sorted(users, key=lambda x : x[1].split(" ")[-1].lower())
  bread = base_bread()
  return render_template("user-list.html", title="All Users", 
      users = users, bread = bread)

@login_page.route("/myself")
def info():
  info = {}
  info['login'] = url_for(".login")
  info['logout'] = url_for(".logout")
  info['user'] = current_user
  info['next'] = request.referrer
  return render_template("user-info.html", 
      info = info, title="Userinfo", 
      bread = base_bread() + [("Myself", url_for(".info"))])

# ./info again, but for POST!
@login_page.route("/info", methods = ['POST'])
@login_required
def set_info():
  for k,v in request.form.iteritems():
    setattr(current_user, k, v)
  current_user.save()
  flask.flash("Thank you for updating your details!")
  return flask.redirect(url_for(".info"))

@login_page.route("/profile/<userid>")
@login_required
def profile(userid):
  getDBConnection().knowledge.knowls.ensure_index('title')
  user = LmfdbUser(userid)
  bread = base_bread() + [(user.name, url_for('.profile', userid=user.get_id()))]
  userknowls = getDBConnection().knowledge.knowls.find({'authors' : userid}, fields=['title']).sort([('title', ASC)])
  userfiles = getDBConnection().upload.fs.files.find({'metadata.uploader_id' : userid, 'metadata.status': 'approved'})
  userfilesmod = getDBConnection().upload.fs.files.find({'metadata.uploader_id' : userid, 'metadata.status': 'unmoderated'})
  return render_template("user-detail.html", user=user, 
      title="%s" % user.name, bread= bread, userknowls = userknowls, userfiles = userfiles, userfilesmod = userfilesmod)

@login_page.route("/login", methods = ["POST"])
def login(**kwargs):
  bread = base_bread() + [ ('Login', url_for('.login')) ]
  # login and validate the user …
  # remember = True sets a cookie to remmeber the user
  name      = request.form["name"]
  password  = request.form["password"]
  next      = request.form["next"]
  remember  = True if request.form["remember"] == "on" else False
  user      = LmfdbUser(name)
  if user and user.authenticate(password):
    login_user(user, remember=remember) 
    flask.flash("Hello %s, your login was successful!" % user.name)
    logger.info("login: '%s' - '%s'" % (user.get_id(), user.name))
    return flask.redirect(next or url_for(".info"))
  flask.flash("Oops! Wrong username or password.", "error")
  return flask.redirect(url_for(".info"))

def admin_required(fn):
  """
  wrap this around those entry points where you need to be an admin.
  """
  @wraps(fn)
  @login_required
  def decorated_view(*args, **kwargs):
    logger.info("admin access attempt by %s" % current_user.get_id())
    if not current_user.is_admin():
      return flask.abort(403) # 401 = access denied
    return fn(*args, **kwargs)
  return decorated_view

def get_user_token_coll():
  return getDBConnection().userdb.tokens

@login_page.route("/register")
def register_new():
  q_admins = getDBConnection().userdb.users.find({'admin' : True})
  admins =', '.join((_['full_name'] or _['_id'] for _ in q_admins))
  return "You have to contact one of the Admins: %s" % admins

@login_page.route("/register/new")
@login_page.route("/register/new/<int:N>")
@admin_required
def register(N = 10):
  N = 100 if N > 100 else N
  from datetime import datetime, timedelta
  now    = datetime.utcnow()
  tdelta = timedelta(days=1)
  exp    = now + tdelta
  import random
  tokens = [ str(random.randrange(1e20,1e21)) for _ in range(N) ]
  for t in tokens:
    get_user_token_coll().save({'_id' : t, 'expire':exp})
  urls   = [ "%s%s" % (base_url, url_for(".register_token", token = _)) for _ in tokens ]
  resp = make_response('\n'.join(urls))
  resp.headers['Content-type'] = 'text/plain'
  return resp

def delete_old_tokens():
  from datetime import datetime, timedelta
  now    = datetime.utcnow()
  tdelta = timedelta(days=8)
  exp    = now + tdelta
  get_user_token_coll().remove({'expire': { '$gt' : exp}})

@login_page.route("/register/<token>", methods = ['GET', 'POST'])
def register_token(token):
  delete_old_tokens()
  token_exists = get_user_token_coll().find({'_id' : token}).count() == 1
  if not token_exists:
    flask.abort(401)
  bread = base_bread() + [('Register', url_for(".register_new"))]
  if request.method == "GET":
    return render_template("register.html", title="Register", bread=bread, next=request.referrer or "/", token=token)
  elif request.method == 'POST':
    name   = request.form['name']
    if not allowed_usernames.match(name):
      flask.flash("""Oops, usename '%s' is not allowed.
                  It must consist of lower/uppercase characters, 
                  no spaces, numbers or '.', '_' and '-'.""" % name, "error")
      return flask.redirect(url_for(".register_new"))
    
    pw1    = request.form['password1']
    pw2    = request.form['password2']
    if pw1 != pw2:
      flask.flash("Oops, passwords do not match!", "error")
      return flask.redirect(url_for(".register_new"))

    if len(pw1) <= 3:
      flask.flash("Oops, password too short. Minimum 4 characters please!", "error")
      return flask.redirect(url_for(".register_new"))

    full_name  = request.form['full_name']
    email      = request.form['email']
    next       = request.form["next"]

    if pwdmanager.user_exists(name):
      flask.flash("Sorry, user ID '%s' already exists!" % name, "error")
      return flask.redirect(url_for(".register_new"))

    newuser             = pwdmanager.new_user(name, pw1)
    newuser.full_name   = full_name
    newuser.email       = email
    newuser.save()
    login_user(newuser, remember=True) 
    flask.flash("Hello %s! Congratulations, you are a new user!" % newuser.name)
    get_user_token_coll().remove({'_id' : token})
    logger.debug("removed login token '%s'" % token)
    logger.info("new user: '%s' - '%s'" % (newuser.get_id(), newuser.name))
    return flask.redirect(next or url_for(".info"))


@login_page.route("/logout")
@login_required
def logout():
  bread = base_bread() + [ ('Login', url_for('.logout')) ]
  logout_user()
  flask.flash("You are logged out now. Have a nice day!")
  return flask.redirect(request.args.get("next") or request.referrer or url_for('.info'))

@login_page.route("/admin")
@login_required
@admin_required
def admin():
  return "success: only admins can read this!"

