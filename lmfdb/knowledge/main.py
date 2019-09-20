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
import json
import time
from lmfdb.app import app, is_beta
from datetime import datetime
from flask import abort, flash, jsonify, make_response,\
                  redirect, render_template, render_template_string,\
                  request, url_for
from markupsafe import Markup
from flask_login import login_required, current_user
from knowl import Knowl, knowldb, knowl_title, knowl_exists
from lmfdb.users import admin_required, knowl_reviewer_required
from lmfdb.users.pwdmanager import userdb
from lmfdb.utils import to_dict, code_snippet_knowl
import markdown
from lmfdb.knowledge import logger
from lmfdb.utils import datetime_to_timestamp_in_ms,\
                        timestamp_in_ms_to_datetime, flash_error

#ejust for those, who still use an older markdown
try:
    markdown.util.etree
except:
    logger.fatal("You need to update the markdown python utility:" +
                 "sage -sh -> easy_install -U markdown flask-markdown")
    exit()

_cache_time = 120


# know IDs are restricted by this regex
allowed_knowl_id = re.compile("^[a-z0-9._-]+$")
def allowed_id(ID):
    if ID.startswith('belyi') and\
            (ID.endswith('top') or ID.endswith('bottom')):
        for c in "[],T":
            ID = ID.replace(c,'')
    if not allowed_knowl_id.match(ID):
        flash_error("""Oops, knowl id '%s' is not allowed.
                  It must consist of lowercase characters,
                  no spaces, numbers or '.', '_' and '-'.""", ID)
        return False
    return True

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
# priority above escape (180), but below backtick (190)
# Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
md.inlinePatterns.register(IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), 'math$', 186)
md.inlinePatterns.register(IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), 'math$$', 185)
md.inlinePatterns.register(IgnorePattern(r'(\\\(.+?\\\))'), 'math\\(', 184)
md.inlinePatterns.register(IgnorePattern(r'(\\\[.+?\\\])'), 'math\\[', 183)

# Tell markdown to turn hashtags into search urls
hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
md.inlinePatterns.register(HashTagPattern(hashtag_keywords_rex), 'hashtag', 182)

# Tells markdown to process "wikistyle" knowls with optional title
# should cover [[[ KID ]]] and [[[ KID | title ]]]
knowltagtitle_regex = r'\[\[\[[ ]*([^\]]+)[ ]*\]\]\]'
md.inlinePatterns.register(KnowlTagPatternWithTitle(knowltagtitle_regex), 'knowltagtitle', 181)

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

    return '[' + ans + ']'  + everythingelse

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
    if not allowed_id(ID):
        return redirect(url_for(".index"))
    knowl = Knowl(ID, editing=True)
    for elt in knowl.edit_history:
        # We will be printing these within a javascript ` ` string
        # so need to escape backticks
        elt['content'] = json.dumps(elt['content'])
    author = knowl._last_author
    # Existing comments can only be edited by admins and the author
    if knowl.type == -2 and author and not (current_user.is_admin() or current_user.get_id() == author):
        flash_error("You can only edit your own comments")
        return redirect(url_for(".show", ID=knowl.source))

    lock = None
    if request.args.get("lock", "") != 'ignore':
        try:
            lock = knowldb.is_locked(knowl.id)
        except DatabaseError as e:
            logger.info("Oops, failed to get the lock. Error: %s" %e)
    author_edits = lock and lock['username'] == current_user.get_id()
    logger.debug(author_edits)
    if author_edits:
        lock = None
    if not lock:
        try:
            knowldb.set_locked(knowl, current_user.get_id())
        except DatabaseError as e:
            logger.info("Oops, failed to set the lock. Error: %s" %e)

    b = get_bread([("Edit '%s'" % ID, url_for('.edit', ID=ID))])
    if knowl.type == -2:
        title = "Comment on '%s'" % knowl.source
    elif knowl.type == 0:
        title = "Edit Knowl '%s'" % ID
    else:
        ann_type = 'Top' if knowl.type == 1 else 'Bottom'
        title = 'Edit %s Knowl for <a href="/%s">%s</a>' % (ann_type, knowl.source, knowl.source_name)
    return render_template("knowl-edit.html",
                           title=title,
                           k=knowl,
                           bread=b,
                           lock=lock)


@knowledge_page.route("/show/<ID>")
def show(ID):
    timestamp = request.args.get('timestamp')
    if timestamp is not None:
        timestamp = timestamp_in_ms_to_datetime(timestamp)
    k = Knowl(ID, timestamp=timestamp, showing=True)
    if k.exists():
        r = render_knowl(ID, footer="0", raw=True)
        title = k.title or "'%s'" % k.id
        if not is_beta():
            if k.status == 0:
                title += " (awaiting review)"
            else:
                title += " (reviewed)"
    else:
        if current_user.is_admin() and k.exists(allow_deleted=True):
            k = Knowl(ID, showing=True, allow_deleted=True)
            r = render_knowl(ID, footer="0", raw=True, allow_deleted=True)
            title = (k.title or "'%s'" % k.id) + " (DELETED)"
        else:
            return abort(404, "No knowl found with the given id")
    for elt in k.edit_history:
        # We will be printing these within a javascript ` ` string
        # so need to escape backticks
        elt['content'] = json.dumps(elt['content'])
    # Modify the comments list to add information on whether this user can delete
    if k.type != -2:
        for i, (cid, author, timestamp) in enumerate(k.comments):
            can_delete = (current_user.is_admin() or current_user.get_id() == author)
            author_name = userdb.lookup(author)["full_name"]
            k.comments[i] = (cid, author_name, timestamp, can_delete)
    b = get_bread([(k.category, url_for('.index', category=k.category)), ('%s' % title, url_for('.show', ID=ID))])

    return render_template(u"knowl-show.html",
                           title=title,
                           k=k,
                           cur_username=current_user.get_id(),
                           render=r,
                           bread=b)

@knowledge_page.route("/remove_author/<ID>")
@login_required
def remove_author(ID):
    k = Knowl(ID)
    uid = current_user.get_id()
    if uid not in k.authors:
        flash_error("You are not an author on %s", k.id)
    elif len(k.authors) == 1:
        flash_error("You cannot remove yourself unless there are other authors")
    else:
        knowldb.remove_author(ID, uid)
    return redirect(url_for(".show", ID=ID))

@knowledge_page.route("/content/<ID>/<int:timestamp>")
def content(ID, timestamp):
    if timestamp is not None:
        timestamp = timestamp_in_ms_to_datetime(timestamp)
    data = Knowl(ID, timestamp=timestamp).content
    resp = make_response(data)
    # cache and allow CORS
    resp.headers['Cache-Control'] = 'max-age=%d, public' % (_cache_time,)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp
@knowledge_page.route("/content/<ID>")
def raw_without_timestamp(ID):
    return content(ID, timestamp=None)

@knowledge_page.route("/raw/<ID>/<int:timestamp>")
def raw(ID):
    data = render_knowl(ID, footer="0", raw=True)
    resp = make_response(data)
    # cache  and allow CORS
    resp.headers['Cache-Control'] = 'max-age=%d, public' % (_cache_time,)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp



@knowledge_page.route("/history")
@knowledge_page.route("/history/<int:limit>")
def history(limit=25):
    h_items = knowldb.get_history(limit)
    bread = get_bread([("History", url_for('.history', limit=limit))])
    return render_template("knowl-history.html",
                           title="Knowledge History",
                           bread=bread,
                           history=h_items,
                           limit=limit)

@knowledge_page.route("/comment_history")
@knowledge_page.route("/comment_history/<int:limit>")
@login_required
def comment_history(limit=25):
    h_items = knowldb.get_comment_history(limit)
    bread = get_bread([("Comment History", url_for('.comment_history', limit=limit))])
    return render_template("knowl-comment-history.html",
                           title="Comment History",
                           bread=bread,
                           history=h_items,
                           limit=limit)

@knowledge_page.route("/delete/<ID>")
@admin_required
def delete(ID):
    k = Knowl(ID)
    k.delete()
    flash(Markup("Knowl %s has been deleted." % ID))
    return redirect(url_for(".index"))


@knowledge_page.route("/resurrect/<ID>")
@admin_required
def resurrect(ID):
    k = Knowl(ID)
    k.resurrect()
    flash(Markup("Knowl %s has been resurrected." % ID))
    return redirect(url_for(".show", ID=ID))

@knowledge_page.route("/review/<ID>/<int:timestamp>")
@knowl_reviewer_required
def review(ID, timestamp):
    timestamp = timestamp_in_ms_to_datetime(timestamp)
    k = Knowl(ID, timestamp=timestamp)
    k.review(who=current_user.get_id())
    flash(Markup("Knowl %s has been positively reviewed." % ID))
    return redirect(url_for(".show", ID=ID))

@knowledge_page.route("/demote/<ID>/<int:timestamp>")
@knowl_reviewer_required
def demote(ID, timestamp):
    timestamp = timestamp_in_ms_to_datetime(timestamp)
    k = Knowl(ID, timestamp=timestamp)
    k.review(who=current_user.get_id(), set_beta=True)
    flash(Markup("Knowl %s has been returned to beta." % ID))
    return redirect(url_for(".show", ID=ID))

@knowledge_page.route("/review_recent/<int:days>/")
@knowl_reviewer_required
def review_recent(days):
    if len(request.args) > 0:
        try:
            info = to_dict(request.args)
            beta = None
            ID = info.get('review')
            if ID:
                beta = False
            else:
                ID = info.get('beta')
                if ID:
                    beta = True
            if beta is not None:
                k = Knowl(ID)
                k.review(who=current_user.get_id(), set_beta=beta)
                return jsonify({"success": 1})
            raise ValueError
        except Exception:
            return jsonify({"success": 0})
    knowls = knowldb.needs_review(days)
    for k in knowls:
        k.rendered = render_knowl(k.id, footer="0", raw=True, k=k)
        k.reviewed_content = json.dumps(k.reviewed_content)
        k.content = json.dumps(k.content)
    b = get_bread([("Reviewing Recent", url_for('.review_recent', days=days))])
    return render_template("knowl-review-recent.html",
                           title="Reviewing %s days of knowls" % days,
                           knowls=knowls,
                           bread=b)

@knowledge_page.route("/broken_links")
def broken_links():
    bad_knowls = knowldb.broken_links_knowls()
    bad_code = [(code_snippet_knowl(D[0]), D[1]) for D in knowldb.broken_links_code()]
    b = get_bread([("Broken links", url_for('.broken_links'))])
    return render_template("knowl-broken-links.html",
                           title="Broken knowl links",
                           bad_knowls=bad_knowls,
                           bad_code=bad_code,
                           bread=b)

@knowledge_page.route("/new_comment/<ID>")
def new_comment(ID):
    time = datetime_to_timestamp_in_ms(datetime.utcnow())
    cid = '%s.%s.comment' % (ID, time)
    return edit(ID=cid)

@knowledge_page.route("/delete_comment/<ID>")
def delete_comment(ID):
    try:
        comment = Knowl(ID)
        if comment.type != -2:
            raise ValueError
        # We allow admins and the original author to delete comments.
        if not (current_user.is_admin() or current_user.get_id() == comment.authors[0]):
            raise ValueError
        comment.delete()
    except ValueError:
        flash_error("Only admins and the original author can delete comments")
    return redirect(url_for(".show", ID=comment.source))

@knowledge_page.route("/edit", methods=["POST"])
@login_required
def edit_form():
    ID = request.form['id']
    return redirect(url_for(".edit", ID=ID))


@knowledge_page.route("/save", methods=["POST"])
@login_required
def save_form():
    ID = request.form['id']
    if not ID:
        raise Exception("no id")

    if not allowed_id(ID):
        return redirect(url_for(".index"))

    FINISH_RENAME = request.form.get('finish_rename', '')
    UNDO_RENAME = request.form.get('undo_rename', '')
    if FINISH_RENAME:
        k = Knowl(ID)
        k.actually_rename()
        flash(Markup("Renaming complete; the history of %s has been merged into %s" % (ID, k.source_name)))
        return redirect(url_for(".show", ID=k.source_name))
    elif UNDO_RENAME:
        k = Knowl(ID)
        k.undo_rename()
        flash(Markup("Renaming undone; the history of %s has been merged back into %s" % (k.source_name, ID)))
        return redirect(url_for(".show", ID=ID))
    NEWID = request.form.get('krename', '').strip()
    k = Knowl(ID, saving=True, renaming=bool(NEWID))
    new_title = request.form['title']
    new_content = request.form['content']
    who = current_user.get_id()
    if new_title != k.title or new_content != k.content:
        if not k.content and not k.title and k.exists(allow_deleted=True):
            # Creating a new knowl with the same id as one that had previously been deleted
            k.resurrect()
            flash(Markup("Knowl successfully created.  Note that a knowl with this id existed previously but was deleted; its history has been restored."))
        k.title = new_title
        k.content = new_content
        k.timestamp = datetime.now()
        k.status = 0
        k.save(who=who)
    if NEWID:
        if not current_user.is_admin():
            flash_error("You do not have permissions to rename knowl")
        elif not allowed_id(NEWID):
            pass
        else:
            try:
                if k.sed_safety == 0:
                    time.sleep(0.01)
                    k.actually_rename(NEWID)
                    flash(Markup("Knowl renamed to {0} successfully.".format(NEWID)))
                else:
                    k.start_rename(NEWID, who)
            except ValueError as err:
                flash_error(str(err), "error")
            else:
                if k.sed_safety == 1:
                    flash(Markup("Knowl rename process started. You can change code references using".format(NEWID)))
                    flash(Markup("git grep -l '{0}' | xargs sed -i '' -e 's/{0}/{1}/g' (Mac)".format(ID, NEWID)))
                    flash(Markup("git grep -l '{0}' | xargs sed -i 's/{0}/{1}/g' (Linux)".format(ID, NEWID)))
                elif k.sed_safety == -1:
                    flash(Markup("Knowl rename process started.  This knowl appears in the code (see references below), but cannot trivially be replaced with grep/sed".format(NEWID)))
                ID = NEWID
    if k.type == -2:
        return redirect(url_for(".show", ID=k.source))
    else:
        return redirect(url_for(".show", ID=ID))


@knowledge_page.route("/render/<ID>", methods=["GET", "POST"])
def render(ID):
    return render_knowl(ID)

def render_knowl(ID, footer=None, kwargs=None,
        raw=False, k=None, allow_deleted=False, timestamp=None):
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
    # logger.debug("kwargs: %s", request.args)
    kwargs = kwargs or dict(((k, v) for k, v in request.args.iteritems()))
    # logger.debug("kwargs: %s" , kwargs)
    if timestamp is None:
        # fetch and convert the ms timestamp to datetime
        try:
            timestamp = timestamp_in_ms_to_datetime(int(kwargs['timestamp']))
        except KeyError:
            pass

    if k is None:
        try:
            k = Knowl(ID, allow_deleted=allow_deleted, timestamp=timestamp)
        except Exception:
            logger.critical("Failed to render knowl %s"%ID)
            errmsg = "Sorry, the knowledge database is currently unavailable."
            return errmsg if raw else make_response(errmsg)

        # If we are rendering a reviewed knowl on nonbeta,
        # we always include the timestamp
        if timestamp is None and k.status == 1 and not is_beta():
            kwargs['timestamp'] = k.ms_timestamp;



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

    review_status = ""
    if foot == "1":
        render_me += """\
  <div class="knowl-footer">
    <a href="{{ url_for('.show', ID='%(ID)s', %(kw_params)s) }}">permalink</a>
    {%% if user_is_authenticated %%}
      &middot;
      <a href="{{ url_for('.edit', ID='%(ID)s') }}">edit</a>
    {%% endif %%}
    %(review_status)s
  </div>"""
        # """ &middot; Authors: %(authors)s """
        if k.status == 0 and k.type != -2:
            review_status = """&middot; (awaiting review)"""
    render_me += "</div>"
    # render_me = render_me % {'content' : con, 'ID' : k.id }
    con = md_preprocess(con)

    # markdown enabled
    render_me = render_me % {'content': md.convert(con), 'ID': k.id, 'review_status': review_status,
                             'kw_params': kw_params} #, 'authors' : authors }
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
        # cache if it is a usual GET
        if request.method == 'GET':
            resp.headers['Cache-Control'] = 'max-age=%d, public' % (_cache_time,)
            resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception, e:
        return "ERROR in the template: %s. Please edit it to resolve the problem." % e

@knowledge_page.route("/", methods=['GET', 'POST'])
def index():
    from psycopg2 import DataError
    cur_cat = request.args.get("category", "")

    filtermode = request.args.get("filtered")
    from knowl import knowl_status_code, knowl_type_code
    if request.method == 'POST':
        qualities = [quality for quality in knowl_status_code if request.form.get(quality, "") == "on"]
        types = [typ for typ in knowl_type_code if request.form.get(typ, "") == "on"]
    elif request.method == 'GET':
        qualities = request.args.getlist('qualities')
        types = request.args.getlist('types')

    if filtermode:
        filters = [ q for q in qualities if q in knowl_status_code ]
        types = [ typ for typ in types if typ in knowl_type_code ]
        # If "in progress" requested, should add author = current_user.get_id()
    else:
        filters = []
        types = ["normal"]

    search = request.args.get("search", "")
    regex = (request.args.get("regex", "") == "on")
    keywords = search if regex else search.lower()
    try:
        knowls = knowldb.search(category=cur_cat, filters=filters, types=types, keywords=keywords, regex=regex)
    except DataError as e:
        knowls = {}
        if regex and "invalid regular expression" in str(e):
	    flash_error("The string %s is not a valid regular expression", keywords)
        else:
            flash_error("Unexpected error %s occured during knowl search", str(e))

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
    knowl_qualities = ["reviewed", "beta"]
    #if current_user.is_authenticated:
    #    knowl_qualities.append("in progress")
    if current_user.is_admin():
        knowl_qualities.append("deleted")
    b = []
    if cur_cat:
        b = [(cur_cat, url_for('.index', category=cur_cat))]
    return render_template("knowl-index.html",
                           title="Knowledge Database",
                           bread=get_bread(b),
                           knowls=knowls,
                           search=search,
                           searchbox=searchbox(search, bool(search)),
                           knowl_qualities=knowl_qualities,
                           qualities = qualities,
                           searchmode=bool(search),
                           use_regex=regex,
                           categories = knowldb.get_categories(),
                           cur_cat = cur_cat,
                           categorymode = bool(cur_cat),
                           filtermode = filtermode,
                           knowl_types=knowl_type_code.keys(),
                           types=types)




