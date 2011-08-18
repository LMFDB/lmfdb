# -*- encoding: utf-8 -*-
# this holds all the flask-login specific logic (+ url mapping an rendering templates)
# for the user management
# author: harald schilly <harald.schilly@univie.ac.at>

import logging
import pymongo
import flask
from base import app, getDBConnection
from flask import render_template, request, abort, Blueprint, url_for
from flaskext.login import login_required, login_user, current_user, logout_user

import pwdmanager
from pwdmanager import LmfdbUser

login_page = Blueprint("login", __name__, template_folder='templates')

from flaskext.login import LoginManager
login_manager = LoginManager()

@login_manager.user_loader
def load_user(userid):
  from pwdmanager import LmfdbUser
  return LmfdbUser.get(userid) 

login_manager.login_view = "login.info"

# globally define the user and username
@app.context_processor
def ctx_proc_userdata():
  userdata = {'user' : current_user}
  userdata['username'] = 'Anonymous' if current_user.is_anonymous() else current_user.name
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
#  logging.info(">> curr_app: %s   user: %s" % (cur_app, cur_user))
#
#from flaskext.login import user_logged_in, user_login_confirmed
#user_logged_in.connect(log_login_callback)
#user_login_confirmed.connect(log_login_callback)


def base_bread():
  return [('User', url_for(".info"))]

@login_page.route("/info", methods = ['POST'])
@login_required
def set_info():
  for f in LmfdbUser.properties:
   setattr(current_user, f, request.form[f])
  flask.flash("Thank you for updating your details!")
  return flask.redirect(url_for(".info"))

@login_page.route("/")
def list():
  import pwdmanager
  users = pwdmanager.get_user_list()
  users = sorted(users, key=lambda x : x[1])
  bread = base_bread() + [("List", url_for(".list"))]
  return render_template("user-list.html", title="All Users", 
      users = users, bread = bread)


@login_page.route("/info")
def info():
  info = {}
  info['login'] = url_for(".login")
  info['logout'] = url_for(".logout")
  info['user'] = current_user
  info['next'] = request.referrer
  return render_template("user-info.html", 
      info = info, title="Userinfo", bread = base_bread())

@login_page.route("/show/<userid>")
@login_required
def user_detail(userid):
  user = LmfdbUser.get(userid)
  bread = base_bread() + [(user.name, url_for('.user_detail', userid=user.get_id()))]
  return render_template("user-detail.html", user=user, 
      title="%s" % user.name, bread= bread)

@login_page.route("/login", methods = ["POST"])
def login(**kwargs):
  bread = base_bread() + [ ('Login', url_for('.login')) ]
  # login and validate the user …
  # remember = True sets a cookie to remmeber the user
  name      = request.form["name"]
  password  = request.form["password"]
  next      = request.form["next"]
  import pwdmanager
  user      = LmfdbUser.get(name)
  if user and user.authenticate(password):
    login_user(user, remember=True) 
    flask.flash("Hello %s, you login was successful!" % user.name)
    return flask.redirect(next or url_for(".info"))
  flask.flash("Oops! Wrong username or password!", "error")
  return flask.redirect(url_for(".info"))

@login_page.route("/register", methods = ['GET', 'POST'])
def register():
  bread = base_bread() + [('Register', url_for(".register"))]
  if request.method == 'POST':
    name   = request.form['name']
    pw1    = request.form['password1']
    pw2    = request.form['password2']
    if pw1 != pw2:
      flask.flash("Oops, passwords do not match!", "error")
      return flask.redirect(url_for(".register"))

    full_name  = request.form['full_name']
    email      = request.form['email']
    next       = request.form["next"]

    import pwdmanager
    if pwdmanager.user_exists(name):
      flask.flash("Sorry, user '%s' already exists!" % name, "error")
      return flask.redirect(url_for(".register"))

    newuser             = pwdmanager.new_user(name, pw1)
    newuser.full_name   = full_name
    newuser.email       = email
    login_user(newuser, remember=True) 
    flask.flash("Hello %s! Congratulations, you are a new user!" % newuser.name)
    return flask.redirect(next or url_for(".info"))

  return render_template("register.html", title="Register", bread=bread, next=request.referrer)

@login_page.route("/logout")
@login_required
def logout():
  bread = base_bread() + [ ('Login', url_for('.logout')) ]
  logout_user()
  flask.flash("You are logged out now. Have a nice day!")
  return flask.redirect(request.args.get("next") or request.referrer or url_for('.info'))

