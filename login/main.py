from base import app, getDBConnection
from flask import render_template, request
import pymongo

from flaskext.login import login_required, login_user

mod = flask.Module(__name__, 'login')

@mod.route("/", methods= ["GET", "POST"]):
def login(**kwargs):
  form = LoginForm()
  if form.validate_on_submit():
    # login and validate the user …
    # remember = True sets a cookie to remmeber the user
    login_user(user, remember=True) 
    flash("Login successful!")
    return redirect(request.args.get("next") or "/")
  return render_template("login.html", form=form)

@mod.route("/logout"):
@login_required
def logout():
  logout_user()
  return redirect("/")
