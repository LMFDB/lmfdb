# -*- coding: utf-8 -*-
# This Blueprint is about adding a Knowledge Base to the LMFDB website.
# referencing content, dynamically inserting information into the website, …
# 
# This is more than just a web of entries in a wiki, because content is "transcluded".
# Transclusion is an actual concept, you can read about it here:
# http://en.wikipedia.org/wiki/Transclusion
#
# a "Knowl" (see knowl.py) is our base class for any bit of "knowledge". we might
# subclass it into "theorem", "proof", "description", and much more if necessary
# (i.e. when it makes sense to add additional fields, e.g. for referencing each other)
#
# author: Harald Schilly <harald.schilly@univie.ac.at>

import pymongo
import flask
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from flaskext.login import login_required, current_user
from knowl import Knowl
from utils import make_logger
from users import admin_required
# from markdown import markdown

ASC = pymongo.ASCENDING

import re
allowed_knowl_id = re.compile("^[a-zA-Z0-9._-]+$")

# global (application wide) insertion of the variable "Knowl" to create
# lightweight Knowl objects inside the templates.
@app.context_processor
def ctx_knowledge():
  return {'Knowl' : Knowl}

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')
logger = make_logger(knowledge_page)

# blueprint specific definition of the body_class variable
@knowledge_page.context_processor
def body_class():
  return { 'body_class' : 'knowl' }

def get_bread(breads = []):
  bc = [("Knowledge", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

@knowledge_page.route("/test")
def test():
  """
  just a test page
  """
  logger.info("test")
  return render_template("knowl-test.html",
               bread=get_bread([("Test", url_for(".test"))]), 
               title="Knowledge Test")

@knowledge_page.route("/edit/<ID>")
@login_required
def edit(ID):
  if not allowed_knowl_id.match(ID):
      flask.flash("""Oops, knowl id '%s' is not allowed.
                  It must consist of lower/uppercase characters, 
                  no spaces, numbers or '.', '_' and '-'.""" % ID, "error")
      return flask.redirect(url_for(".index"))
  knowl = Knowl(ID)
  b = get_bread([("Edit '%s'"%ID, url_for('.edit', ID=ID))])
  return render_template("knowl-edit.html", 
         title="Edit Knowl '%s'" % ID,
         k = knowl,
         bread = b)

@knowledge_page.route("/show/<ID>")
def show(ID):
  k = Knowl(ID)
  r = render(ID, footer="0")
  return render_template("knowl-show.html",
         title = "Knowl '%s'" % k.id,
         k = k,
         render = r,
         bread = get_bread([('Show %s'%k.id, url_for('.show', ID=ID))]))

@knowledge_page.route("/delete/<ID>")
@admin_required
def delete(ID):
  k = Knowl(ID)
  k.delete()
  flask.flash("Snif! Knowl %s deleted and gone forever :-(" % ID)
  return flask.redirect(url_for(".index"))

@knowledge_page.route("/edit", methods=["POST"])
@login_required
def edit_form():
  ID = request.form['id']
  return flask.redirect(url_for(".edit", ID=ID))

@knowledge_page.route("/save", methods=["POST"])
@login_required
def save_form():
  ID = request.form['id']
  if not ID:
    raise Exception("no id")

  if not allowed_knowl_id.match(ID):
      flask.flash("""Oops, knowl id '%s' is not allowed.
                  It must consist of lower/uppercase characters, 
                  no spaces, numbers or '.', '_' and '-'.""" % ID, "error")
      return flask.redirect(url_for(".index"))

  k = Knowl(ID)
  k.title = request.form['title']
  k.content = request.form['content']
  k.save()
  return flask.redirect(url_for(".show", ID=ID))
  

@knowledge_page.route("/render/<ID>", methods = ["GET", "POST"])
def render(ID, footer=None):
  """
  this method renders the given Knowl (ID) to insert it
  dynamically in a website. It is intended to be used 
  by an AJAX call, but should do a similar job server-side
  only, too.

  Note, that the used knowl-render.html template is *not*
  based on any globally defined website and just creates
  a small and simple html snippet!
  """
  k = Knowl(ID)
  #this is a very simple template based on no other template to render one single Knowl
  #for inserting into a website via AJAX or for server-side operations.
  if 'content' in request.form:
    con = request.form['content']
  else:
    con = request.args.get("content", k.content)
  foot = footer or request.form['footer'] or request.args.get("footer", "1") 

  render_me = u"""\
  {%% include "knowl-defs.html" %%}
  {%% from "knowl-defs.html" import KNOWL with context %%}

  <div class="knowl">
  <div class="knowl-content">%(content)s</div>"""
  if foot == "1": 
    render_me += """\
  <div class="knowl-footer">
    <a href="{{ url_for('.show', ID='%(ID)s') }}">permalink</a> 
    {%% if user.is_authenticated() %%}
      &middot;
      <a href="{{ url_for('.edit', ID='%(ID)s') }}">edit</a> 
    {%% endif %%}
  </div>"""
  render_me += "</div>"
  render_me = render_me % {'content' : con, 'ID' : k.id }
  # markdown disabled
  # {'content' : markdown(k.content.replace("\\","\\\\"), ['wikilinks(base_url=http://wiki.l-functions.org/,end_url=)']), 'ID' : k.id }
  # Pass the text on to markdown.  Note, backslashes need to be escaped for this, but not for the javascript markdown parser

  #logger.debug("rendering template string:\n%s" % render_me)

  # TODO wrap this string-rendering into a try/catch and return a proper error message
  # so that the user has a clue. Most likely, the {{ KNOWL('...') }} has the wrong syntax!
  return render_template_string(render_me, k = k)

@knowledge_page.route("/")
def index():
  # bypassing the Knowl objects to speed things up
  from knowl import get_knowls
  knowls = get_knowls().find(fields=['title'], sort=[("title", ASC)])
  return render_template("knowl-index.html", 
         title="Knowledge Database",
         bread = get_bread(),
         knowls = knowls)


