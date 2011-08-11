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


#user_page = Blueprint("user_page", __name__, template_folder='templates')
user_page = flask.Module(__name__, 'user')

@app.context_processor
def ctx_proc_userdata():
  userdata = {'user' : current_user}
  userdata['username'] = 'Anonymous' if current_user.is_anonymous() else current_user.get_name()
  return userdata

def base_bread():
  return [('User', url_for("info"))]

@user_page.route("/info", methods = ['POST'])
def set_info():
  full_name = request.form['full_name']
  current_user.set_full_name(full_name)
  flask.flash("set your full_name to %s" % full_name)
  
  email = request.form['email']
  current_user.set_email(email)
  flask.flash("set your email to %s" % email)

  return flask.redirect(url_for("info"))


@user_page.route("/")
def info():
  info = {}
  info['login'] = url_for("login")
  info['logout'] = url_for("logout")
  info['user'] = current_user
  info['next'] = request.referrer
  return render_template("info.html", info = info, title="Userinfo", bread = base_bread())


@user_page.route("/login", methods = ["POST"])
def login(**kwargs):
  bread = base_bread() + [ ('Login', url_for('login')) ]
  # login and validate the user …
  # remember = True sets a cookie to remmeber the user
  name = request.form["name"]
  password = request.form["password"]
  next = request.form["next"]
  import pwdmanager
  user = pwdmanager.LmfdbUser.get(name)
  if user and user.authenticate(password):
    flask.flash("Hello %s, you login was successful!" % user.get_name())
    login_user(user, remember=True) 
    return flask.redirect(next or url_for("info"))
  flask.flash("Oops! Wrong username or password!", "error")
  return flask.redirect(url_for("info"))

@user_page.route("/register", methods = ['GET', 'POST'])
def register():
  info = {} 
  bread = base_bread() + [('Register', url_for("register"))]
  if request.method == 'POST':
    name = request.form['name']
    pw1 = request.form['password1']
    pw2 = request.form['password2']
    if pw1 != pw2:
      flask.flash("Oops, passwords do not match!", "error")
      return flask.redirect(url_for("register"))

    full_name = request.form['full_name']
    email = request.form['email']
    next = request.form["next"]

    import pwdmanager
    if pwdmanager.user_exists(name):
      flask.flash("Sorry, user '%s' already exists!" % name, "error")
      return flask.redirect(url_for("register"))

    newuser = pwdmanager.new_user(name, email, pw1)
    newuser.set_full_name(full_name)
    login_user(newuser, remember=True) 
    flask.flash("Hello %s! Congratulations, you are a new user!" % newuser.get_name())
    return flask.redirect(next or url_for("info"))

  info['next'] = request.referrer
  return render_template("register.html", title="Register", bread=bread, info=info)

@user_page.route("/logout")
@login_required
def logout():
  bread = base_bread() + [ ('Login', url_for('logout')) ]
  logout_user()
  flask.flash("You are logged out now. Have a nice day!")
  return flask.redirect(request.args.get("next") or request.referrer or url_for('info'))

