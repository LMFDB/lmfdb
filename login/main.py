# -*- encoding: utf-8 -*-

from base import app, getDBConnection
from flask import render_template, request, abort, Blueprint, url_for
from jinja2 import TemplateNotFound
import pymongo
import flask

from flaskext.login import login_required, login_user

login_page = Blueprint("login_page", __name__, template_folder='templates')
app.register_blueprint(login_page, url_prefix="/user")


@login_page.route("/")
def info():
  return "<a href='%s'>login</a> or <a href='%s'>logout</a>" % (url_for('.login'), url_for('.logout'))

@login_page.route("/login", methods = ["GET", "POST"])
def login(**kwargs):
  form = LoginForm()
  if form.validate_on_submit():
    # login and validate the user …
    # remember = True sets a cookie to remmeber the user
    login_user(user, remember=True) 
    flash("Login successful!")
    return redirect(request.args.get("next") or "/")
  return render_template("login.html", form=form)

@login_page.route("/logout")
@login_required
def logout():
  logout_user()
  return redirect("/")
