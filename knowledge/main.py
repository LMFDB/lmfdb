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
import string
import pymongo
import flask
from base import app, getDBConnection
from datetime import datetime
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from flaskext.login import login_required, current_user
from knowl import Knowl
from users import admin_required
import markdown
from knowledge import logger

ASC = pymongo.ASCENDING

import re
allowed_knowl_id = re.compile("^[A-Za-z0-9._-]+$")

# Tell markdown to not escape or format inside a given block
class IgnorePattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        return markdown.AtomicString(m.group(2))

class HashTagPattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
	el = markdown.etree.Element("a")
        el.set('href', url_for('.index')+'?search=%23'+m.group(2))
        el.text = '#' + markdown.AtomicString(m.group(2))
        return el


# Initialise the markdown converter, sending a wikilink [[topic]] to the L-functions wiki
md = markdown.Markdown(extensions=['wikilinks'],
    extension_configs = {'wikilinks': [('base_url', 'http://wiki.l-functions.org/')]})
# Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
md.inlinePatterns.add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
md.inlinePatterns.add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
md.inlinePatterns.add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
md.inlinePatterns.add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')

# Tell markdown to turn hashtags into search urls
hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
md.inlinePatterns.add('hashtag', HashTagPattern(hashtag_keywords_rex), '<escape')

# global (application wide) insertion of the variable "Knowl" to create
# lightweight Knowl objects inside the templates.
@app.context_processor
def ctx_knowledge():
  return {'Knowl' : Knowl}

@app.template_filter("render_knowl")
def render_knowl_in_template(knowl_content, **kwargs):
  """
  This function does the actual rendering, for render and the template_filter
  render_knowl_in_template (ultimately for KNOWL_INC)
  """
  render_me = u"""\
  {%% include "knowl-defs.html" %%}
  {%% from "knowl-defs.html" import KNOWL with context %%}
  {%% from "knowl-defs.html" import KNOWL_LINK with context %%}
  {%% from "knowl-defs.html" import KNOWL_INC with context %%}
  {%% from "knowl-defs.html" import TEXT_DATA with context %%}

  %(content)s
  """
  # markdown enabled
  render_me = render_me % {'content' : md.convert(knowl_content) }
  # Pass the text on to markdown.  Note, backslashes need to be escaped for this, but not for the javascript markdown parser
  return render_template_string(render_me, **kwargs)
  

# a jinja test for figuring out if this is a knowl or not
# usage: {% if K is knowl_type %} ... {% endif %}
def test_knowl_type(k):
  return isinstance(k, Knowl)
app.jinja_env.tests['knowl_type'] = test_knowl_type

from knowledge import knowledge_page

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
               title="Knowledge Test",
               k1 = Knowl("k1"))

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
  b = get_bread([('%s'%k.title, url_for('.show', ID=ID))])
  searchbox = u"""\
    <form id='knowl-search' action="%s" method="GET">
      <input name="search" />
    </form>""" % url_for(".index")
    
  return render_template("knowl-show.html",
         title = k.title,
         k = k,
         render = r,
         bread = b,
         navi_raw = searchbox)

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
  k.quality = request.form['quality']
  k.timestamp = datetime.now()
  k.save(who=current_user.get_id())
  return flask.redirect(url_for(".show", ID=ID))
  

@knowledge_page.route("/render/<ID>", methods = ["GET", "POST"])
def render(ID, footer=None, kwargs = None):
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

  #logger.debug("kwargs: %s", request.args)
  kwargs = kwargs or dict(((k, v) for k,v in request.args.iteritems()))
  #logger.debug("kwargs: %s" , kwargs)

  #this is a very simple template based on no other template to render one single Knowl
  #for inserting into a website via AJAX or for server-side operations.
  if request.method == "POST":
    con = request.form['content']
    foot = footer or request.form['footer']
  elif request.method == "GET":
    con = request.args.get("content", k.content)
    foot = footer or request.args.get("footer", "1") 

  authors = []
  for a in k.author_links():
    authors.append("<a href='%s'>%s</a>" % 
      (url_for('users.profile', userid=a['_id']), a['full_name'] or a['_id'] ))
  authors = ', '.join(authors)

  render_me = u"""\
  {%% include "knowl-defs.html" %%}
  {%% from "knowl-defs.html" import KNOWL with context %%}
  {%% from "knowl-defs.html" import KNOWL_LINK with context %%}
  {%% from "knowl-defs.html" import KNOWL_INC with context %%}
  {%% from "knowl-defs.html" import TEXT_DATA with context %%}

  <div class="knowl">
  <div class="knowl-content">%(content)s</div>"""
  if foot == "1": 
    render_me += """\
  <div class="knowl-footer">
    <a href="{{ url_for('.show', ID='%(ID)s') }}">permalink</a> 
    {%% if user_is_authenticated %%}
      &middot;
      <a href="{{ url_for('.edit', ID='%(ID)s') }}">edit</a> 
    {%% endif %%}
    &middot;
    Authors: %(authors)s
  </div>"""
  render_me += "</div>"
  # render_me = render_me % {'content' : con, 'ID' : k.id }
  # markdown enabled
  render_me = render_me % {'content' : md.convert(con), 'ID' : k.id, 'authors' : authors }
  # Pass the text on to markdown.  Note, backslashes need to be escaped for this, but not for the javascript markdown parser

  #logger.debug("rendering template string:\n%s" % render_me)

  # TODO wrap this string-rendering into a try/catch and return a proper error message
  # so that the user has a clue. Most likely, the {{ KNOWL('...') }} has the wrong syntax!
  logger.debug("kwargs: %s" % k.template_kwargs)
  return render_template_string(render_me, k = k, **kwargs)

@knowledge_page.route("/")
def index():
  # bypassing the Knowl objects to speed things up
  from knowl import get_knowls
  get_knowls().ensure_index('_keywords')
  keyword = request.args.get("search", "").lower()
  keywords = filter(lambda _:len(_) >= 3, keyword.split(" "))
  logger.debug("keywords: %s" % keywords)
  keyword_q = {'_keywords' : { "$all" : keywords}}
  s_query = keyword_q if keyword else {}
  knowls = get_knowls().find(s_query, fields=['title'])

  def first_char(k):
    t = k['title']
    if len(t) == 0: return "?"
    if t[0] not in string.ascii_letters: return "?"
    return t[0].upper()

  # way to additionally narrow down the search
  # def incl(knwl):
  #   if keyword in knwl['_id'].lower():   return True
  #   if keyword in knwl['title'].lower(): return True
  #   return False
  # if keyword: knowls = filter(incl, knowls)

  knowls = sorted(knowls, key = lambda x : x['title'].lower())
  from itertools import groupby
  knowls = groupby(knowls, first_char)
  return render_template("knowl-index.html", 
         title  = "Knowledge Database",
         bread  = get_bread(),
         knowls = knowls,
         search = keyword)


