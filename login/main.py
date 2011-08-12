# -*- encoding: utf-8 -*-

import pymongo
import flask
from base import app, getDBConnection
from flask import render_template, request, abort, Blueprint, url_for

from jinja2 import TemplateNotFound

from flaskext.login import login_required, login_user, current_user, logout_user

"""
from flask import Blueprint
simple_page = Blueprint('simple_pages', __name__, template_folder="templates")
@simple_page.route("/")
def simple():
  return "simple2"

app.register_blueprint(simple_page, url_prefix="/users")
"""


login_page = Blueprint("login", __name__, template_folder='templates')
#login = flask.Module(__name__, 'login')

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

def base_bread():
  return [('User', url_for(".info"))]

@login_page.route("/info", methods = ['POST'])
@login_required
def set_info():
  from pwdmanager import LmfdbUser
  for f in LmfdbUser.properties:
   setattr(current_user, f, request.form[f])
  flask.flash("Thank you for updating your details!")
  return flask.redirect(url_for(".info"))


@login_page.route("/")
def info():
  info = {}
  info['login'] = url_for(".login")
  info['logout'] = url_for(".logout")
  info['user'] = current_user
  info['next'] = request.referrer
  return render_template("info.html", info = info, title="Userinfo", bread = base_bread())

@login_page.route("/<userid>")
def show_user(userid):
  return userid

@login_page.route("/login", methods = ["POST"])
def login(**kwargs):
  bread = base_bread() + [ ('Login', url_for('.login')) ]
  # login and validate the user …
  # remember = True sets a cookie to remmeber the user
  name      = request.form["name"]
  password  = request.form["password"]
  next      = request.form["next"]
  import pwdmanager
  user      = pwdmanager.LmfdbUser.get(name)
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
    flask.flash("Hello %s! Congratulations, you are a new user!" % newuser.get_name())
    return flask.redirect(next or url_for(".info"))

  return render_template("register.html", title="Register", bread=bread, next=request.referrer)

@login_page.route("/logout")
@login_required
def logout():
  bread = base_bread() + [ ('Login', url_for('.logout')) ]
  logout_user()
  flask.flash("You are logged out now. Have a nice day!")
  return flask.redirect(request.args.get("next") or request.referrer or url_for('.info'))

