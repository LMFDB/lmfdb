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
import re
import flask
from lmfdb.base import app
from datetime import datetime
from flask import render_template, render_template_string, request, url_for, make_response
#from flask.ext.login import login_required, current_user
from flask_login import login_required, current_user
from knowl import Knowl, knowldb, knowl_title, knowl_exists
from lmfdb.users import admin_required, housekeeping
import markdown
from lmfdb.knowledge import logger

# just for those, who still use an older markdown
try:
    markdown.util.etree
except:
    logger.fatal("You need to update the markdown python utility: sage -sh -> easy_install -U markdown flask-markdown")
    exit()

# know IDs are restricted by this regex
allowed_knowl_id = re.compile("^[a-z0-9._-]+$")

# Tell markdown to not escape or format inside a given block


class IgnorePattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        return m.group(2)


class HashTagPattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        el = markdown.util.etree.Element("a")
        el.set('href', url_for('knowledge.index') + '?search=%23' + m.group(2))
        el.text = '#' + m.group(2)
        return el


class KnowlTagPatternWithTitle(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        tokens = m.group(2).split("|")
        kid = tokens[0].strip()
        if len(tokens) > 1:
            tit = ''.join(tokens[1:])
            return "{{ KNOWL('%s', title='%s') }}" % (kid, tit.strip())
        return "{{ KNOWL('%s') }}" % kid

# Initialise the markdown converter, sending a wikilink [[topic]] to the L-functions wiki
md = markdown.Markdown(extensions=['markdown.extensions.wikilinks'],
                       extension_configs={'wikilinks': [('base_url', 'http://wiki.l-functions.org/')]})
# Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
md.inlinePatterns.add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
md.inlinePatterns.add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
md.inlinePatterns.add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
md.inlinePatterns.add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')

# Tell markdown to turn hashtags into search urls
hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
md.inlinePatterns.add('hashtag', HashTagPattern(hashtag_keywords_rex), '<escape')

# Tells markdown to process "wikistyle" knowls with optional title
# should cover [[[ KID ]]] and [[[ KID | title ]]]
knowltagtitle_regex = r'\[\[\[[ ]*([^\]]+)[ ]*\]\]\]'
md.inlinePatterns.add('knowltagtitle', KnowlTagPatternWithTitle(knowltagtitle_regex), '<escape')

# global (application wide) insertion of the variable "Knowl" to create
# lightweight Knowl objects inside the templates.

def first_bracketed_string(text, depth=0, lbrack="{", rbrack="}"):
    """If text is of the form {A}B, return {A},B.

    Otherwise, return "",text.

    """

    thetext = text.strip()

    if not thetext:
        logger.error("empty string sent to first_bracketed_string()")
        return ""

    previouschar = ""
       # we need to keep track of the previous character becaause \{ does not
       # count as a bracket

    if depth == 0 and thetext[0] != lbrack:
        return "",thetext

    elif depth == 0:
        firstpart = lbrack
        depth = 1
        thetext = thetext[1:]
    else:
        firstpart = ""   # should be some number of brackets?

    while depth > 0 and thetext:
        currentchar = thetext[0]
        if currentchar == lbrack and previouschar != "\\":
            depth += 1
        elif currentchar == rbrack and previouschar != "\\":
            depth -= 1
        firstpart += currentchar
        if previouschar == "\\" and currentchar == "\\":
            previouschar = "\n"
        else:
            previouschar = currentchar

        thetext = thetext[1:]

    if depth == 0:
        return firstpart, thetext
    else:
        logger.error("no matching bracket %s in %s XX", lbrack, thetext)
        return "",firstpart[1:]   # firstpart should be everything
                                  # but take away the bracket that doesn't match

def ref_to_link(txt):
    """ Convert citations to links

        In a future version the bibliographic entry will be downloaded and saved.
    """
    text = txt.group(1)  # because it was a match in a regular expression

    thecite, everythingelse = first_bracketed_string(text)
    thecite = thecite[1:-1]    # strip curly brackets
    thecite = thecite.replace("\\","")  # \href --> href

    refs = thecite.split(",")
    ans = ""

    # print "refs",refs

    for ref in refs:
        ref = ref.strip()    # because \cite{A, B, C,D} can have spaces
        this_link = ""
        if ref.startswith("href"):
            the_link = re.sub(".*{([^}]+)}{.*", r"\1", ref)
            click_on = re.sub(".*}{([^}]+)}\s*", r"\1", ref)
            this_link = '{{ LINK_EXT("' + click_on + '","' + the_link + '") | safe}}'
        elif ref.startswith("doi"):
            ref = ref.replace(":","")  # could be doi:: or doi: or doi
            the_doi = ref[3:]    # remove the "doi"
            this_link = '{{ LINK_EXT("' + the_doi + '","https://doi.org/' + the_doi + '")| safe }}'
        elif ref.lower().startswith("mr"):
            ref = ref.replace(":","")
            the_mr = ref[2:]    # remove the "MR"
            this_link = '{{ LINK_EXT("' + 'MR:' + the_mr + '", '
            this_link += '"http://www.ams.org/mathscinet/search/publdoc.html?pg1=MR&s1='
            this_link += the_mr + '") | safe}}'
        elif ref.lower().startswith("arxiv"):
            ref = ref.replace(":","")
            the_arx = ref[5:]    # remove the "arXiv"
            this_link = '{{ LINK_EXT("' + 'arXiv:' + the_arx + '", '
            this_link += '"http://arxiv.org/abs/'
            this_link += the_arx + '")| safe}}'


        if this_link:
            if ans:
                ans += ", "
            ans += this_link

    return '[' + ans + ']' + " " + everythingelse

def md_latex_accents(text):
    """
    Convert \"o to &ouml; and similar TeX-style markup.
    """

    knowl_content = text

    knowl_content = re.sub(r'\\"([a-zA-Z])',r"&\1uml;",knowl_content)
    knowl_content = re.sub(r'\\"{([a-zA-Z])}',r"&\1uml;",knowl_content)
    knowl_content = re.sub(r"\\'([a-zA-Z])",r"&\1acute;",knowl_content)
    knowl_content = re.sub(r"\\'{([a-zA-Z])}",r"&\1acute;",knowl_content)
    knowl_content = re.sub(r"\\`([a-zA-Z])",r"&\1grave;",knowl_content)
    knowl_content = re.sub(r"\\`{([a-zA-Z])}",r"&\1grave;",knowl_content)
    knowl_content = re.sub(r"``(?P<a>[\S\s]*?)''", r"&ldquo;\1&rdquo;", knowl_content)

    return knowl_content

def md_preprocess(text):
    """
    Markdown preprocessor: html paragraph breaks before display math,
    \cite{MR:...} and \cite{arXiv:...} converted to links.
    """
    knowl_content = text

    # put a blank line above display equations so that knowls open in the correct location
    knowl_content = re.sub(r"([^\n])\n\\begin{eq",r"\1\n\n\\begin{eq",knowl_content)

    while "\\cite{" in knowl_content:
        knowl_content = re.sub(r"\\cite({.*)",ref_to_link,knowl_content,0,re.DOTALL)

    knowl_content = md_latex_accents(knowl_content)

    return knowl_content

@app.context_processor
def ctx_knowledge():
    return {'Knowl': Knowl, 'knowl_title': knowl_title, "KNOWL_EXISTS": knowl_exists}


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
    knowl_content = md_preprocess(knowl_content)

    # markdown enabled
    render_me = render_me % {'content': md.convert(knowl_content)}
    # Pass the text on to markdown.  Note, backslashes need to be escaped for
    # this, but not for the javascript markdown parser
    try:
        return render_template_string(render_me, **kwargs)
    except Exception, e:
        return "ERROR in the template: %s. Please edit it to resolve the problem." % e


# a jinja test for figuring out if this is a knowl or not
# usage: {% if K is knowl_type %} ... {% endif %}
def test_knowl_type(k):
    return isinstance(k, Knowl)
app.jinja_env.tests['knowl_type'] = test_knowl_type

from lmfdb.knowledge import knowledge_page

# blueprint specific definition of the body_class variable


@knowledge_page.context_processor
def body_class():
    return {'body_class': 'knowl'}


def get_bread(breads=[]):
    bc = [("Knowledge", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


def searchbox(q="", clear=False):
    """returns the searchbox"""
    searchbox = u"""\
    <form id='knowl-search' action="%s" method="GET">
      <input name="search" value="%s" />"""
    if clear:
        searchbox += '<a href="%s">clear</a>' % url_for(".index")
    searchbox += '<button type="submit">Go</button>'
    searchbox += "</form>"
    return searchbox % (url_for(".index"), q)


@knowledge_page.route("/test")
def test():
    """
    just a test page
    """
    logger.info("test")
    return render_template("knowl-test.html",
                           bread=get_bread([("Test", url_for(".test"))]),
                           title="Knowledge Test",
                           k1=Knowl("k1"))


@knowledge_page.route("/edit/<ID>")
@login_required
def edit(ID):
    from psycopg2 import DatabaseError
    if not allowed_knowl_id.match(ID):
        flask.flash("""Oops, knowl id '%s' is not allowed.
                  It must consist of lowercase characters,
                  no spaces, numbers or '.', '_' and '-'.""" % ID, "error")
        return flask.redirect(url_for(".index"))
    knowl = Knowl(ID)

    lock = None
    if request.args.get("lock", "") != 'ignore':
        try:
            lock = knowldb.is_locked(knowl.id)
        except DatabaseError as e:
            logger.info("Oops, failed to get the lock. Error: %s" %e)
    author_edits = lock and lock['who'] == current_user.get_id()
    logger.debug(author_edits)
    if author_edits:
        lock = None
    if not lock:
        try:
            knowldb.set_locked(knowl, current_user.get_id())
        except DatabaseError as e:
            logger.info("Oops, failed to set the lock. Error: %s" %e)

    b = get_bread([("Edit '%s'" % ID, url_for('.edit', ID=ID))])
    return render_template("knowl-edit.html",
                           title="Edit Knowl '%s'" % ID,
                           k=knowl,
                           bread=b,
                           lock=lock)


@knowledge_page.route("/show/<ID>")
def show(ID):
    try:
        k = Knowl(ID)
        r = render(ID, footer="0", raw=True)
        title = k.title or "'%s'" % k.id
        b = get_bread([('%s' % title, url_for('.show', ID=ID))])

        return render_template("knowl-show.html",
                           title=k.title,
                           k=k,
                           render=r,
                           bread=b)
    except Exception:
        flask.abort(404, "No knowl found with the given id");


@knowledge_page.route("/raw/<ID>")
def raw(ID):
    data = render(ID, footer="0", raw=True)
    resp = make_response(data)
    # cache 2 minutes and allow CORS
    resp.headers['Cache-Control'] = 'max-age=%s, public' % (2 * 60)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@knowledge_page.route("/history")
def history():
    h_items = knowldb.get_history()
    bread = get_bread([("History", url_for('.history'))])
    return render_template("knowl-history.html",
                           title="Knowledge History",
                           bread=bread,
                           history=h_items)


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
    knowldb.save_history(k, current_user.get_id())
    return flask.redirect(url_for(".show", ID=ID))


@knowledge_page.route("/render/<ID>", methods=["GET", "POST"])
def render(ID, footer=None, kwargs=None, raw=False):
    """
    this method renders the given Knowl (ID) to insert it
    dynamically in a website. It is intended to be used
    by an AJAX call, but should do a similar job server-side
    only, too.

    Note, that the used knowl-render.html template is *not*
    based on any globally defined website and just creates
    a small and simple html snippet!

    the keyword 'raw' is used in knowledge.show and knowl_inc to
    include *just* the string and not the response object.
    """
    try:
        k = Knowl(ID)
    except Exception:
        logger.critical("Failed to render knowl %s"%ID)
        errmsg = "Sorry, the knowledge database is currently unavailable."
        return errmsg if raw else make_response(errmsg)

    # logger.debug("kwargs: %s", request.args)
    kwargs = kwargs or dict(((k, v) for k, v in request.args.iteritems()))
    # logger.debug("kwargs: %s" , kwargs)

    # kw_params is inserted *verbatim* into the url_for(...) function inside the template
    # the idea is to pass the keyword arguments of the knowl further along the chain
    # of links, in this case the title and the permalink!
    # so, this kw_params should be plain python, e.g. "a=1, b='xyz'"
    kw_params = ', '.join(('%s="%s"' % (k, v) for k, v in kwargs.iteritems()))
    logger.debug("kw_params: %s" % kw_params)

    # this is a very simple template based on no other template to render one single Knowl
    # for inserting into a website via AJAX or for server-side operations.
    if request.method == "POST":
        con = request.form['content']
        foot = footer or request.form['footer']
    elif request.method == "GET":
        con = request.args.get("content", k.content)
        foot = footer or request.args.get("footer", "1")

    # authors = []
    # for a in k.author_links():
    #  authors.append("<a href='%s'>%s</a>" %
    #    (url_for('users.profile', userid=a['_id']), a['full_name'] or a['_id'] ))
    # authors = ', '.join(authors)

    render_me = u"""\
  {%% include "knowl-defs.html" %%}
  {%% from "knowl-defs.html" import KNOWL with context %%}
  {%% from "knowl-defs.html" import KNOWL_LINK with context %%}
  {%% from "knowl-defs.html" import KNOWL_INC with context %%}
  {%% from "knowl-defs.html" import TEXT_DATA with context %%}

  <div class="knowl">"""
    if foot == "1":
        render_me += """\
  <div class="knowl-header">
    <a href="{{ url_for('.show', ID='%(ID)s', %(kw_params)s ) }}">%(title)s</a>
  </div>""" % {'ID': k.id, 'title': (k.title or k.id), 'kw_params': kw_params}

    render_me += """<div><div class="knowl-content">%(content)s</div></div>"""

    if foot == "1":
        render_me += """\
  <div class="knowl-footer">
    <a href="{{ url_for('.show', ID='%(ID)s', %(kw_params)s) }}">permalink</a>
    {%% if user_is_authenticated %%}
      &middot;
      <a href="{{ url_for('.edit', ID='%(ID)s') }}">edit</a>
    {%% endif %%}
  </div>"""
    # """ &middot; Authors: %(authors)s """
    render_me += "</div>"
    # render_me = render_me % {'content' : con, 'ID' : k.id }
    con = md_preprocess(con)

    # markdown enabled
    render_me = render_me % {'content': md.convert(con), 'ID': k.id, 'kw_params': kw_params}
                                                    #, 'authors' : authors }
    # Pass the text on to markdown.  Note, backslashes need to be escaped for
    # this, but not for the javascript markdown parser

    # logger.debug("rendering template string:\n%s" % render_me)

    # TODO improve the error message
    # so that the user has a clue. Most likely, the {{ KNOWL('...') }} has the wrong syntax!
    try:
        data = render_template_string(render_me, k=k, **kwargs)
        if raw:
            # note, this is just internally for the .show method, raw rendering
            # doesn't exist right now and will wrap this into a make_reponse!
            return data
        resp = make_response(data)
        # cache 2 minutes if it is a usual GET
        if request.method == 'GET':
            resp.headers['Cache-Control'] = 'max-age=%s, public' % (2 * 60)
            resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception, e:
        return "ERROR in the template: %s. Please edit it to resolve the problem." % e


@knowledge_page.route("/_cleanup")
@housekeeping
def cleanup():
    """
    reindexes knowls, also the list of categories. prunes history.
    this is an internal task just for admins!
    """
    cats, reindex_count, prune_count = knowldb.cleanup()
    return "categories: %s <br/>reindexed %s knowls<br/>pruned %s histories" % (cats, reindex_count, prune_count)


@knowledge_page.route("/", methods=['GET', 'POST'])
def index():
    cur_cat = request.args.get("category", "")


    filtermode = request.args.get("filtered")
    from knowl import knowl_qualities
    if request.method == 'POST':
        qualities = [quality for quality in knowl_qualities if request.form.get(quality, "") == "on"]
    elif request.method == 'GET':
        qualities = request.args.getlist('qualities')

    if filtermode:
        filters = [ q for q in qualities if q in knowl_qualities ]
    else:
        filters = []

    search = request.args.get("search", "")
    knowls = knowldb.search(cur_cat, filters, search.lower())


    def first_char(k):
        t = k['title']
        if len(t) == 0 or t[0] not in string.ascii_letters:
            return "?"
        return t[0].upper()

    def knowl_sort_key(knowl):
        '''sort knowls, special chars at the end'''
        title = knowl['title']
        if title and title[0] in string.ascii_letters:
            return (0, title.lower())
        else:
            return (1, title.lower())

    knowls = sorted(knowls, key=knowl_sort_key)
    from itertools import groupby
    knowls = groupby(knowls, first_char)
    return render_template("knowl-index.html",
                           title="Knowledge Database",
                           bread=get_bread(),
                           knowls=knowls,
                           search=search,
                           searchbox=searchbox(search, bool(search)),
                           knowl_qualities=knowl_qualities,
                           searchmode=bool(search),
                           categories = knowldb.get_categories(),
                           cur_cat = cur_cat,
                           categorymode = bool(cur_cat),
                           filtermode = filtermode,
                           qualities = qualities)
