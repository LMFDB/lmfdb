# -*- coding: utf-8 -*-
import os, time

from flask import Flask, g, render_template, request, make_response, redirect, url_for, current_app, abort
from sage.env import SAGE_VERSION
# acknowledgement page, reads info from CONTRIBUTORS.yaml

from lmfdb.logger import logger_file_handler, critical
from lmfdb.homepage import load_boxes, contribs

LMFDB_VERSION = "LMFDB Release 1.1"

############################
#         Main app         #
############################

app = Flask(__name__)

############################
# App attribute functions  #
############################

def is_debug_mode():
    from flask import current_app
    return current_app.debug

# this is set here and is available for ctx_proc_userdata
@app.before_request
def set_beta_state():
    g.BETA = (os.getenv('BETA')=='1') or is_debug_mode()

def is_beta():
    from flask import g
    return g.BETA

app.is_running = False
def set_running():
    app.is_running = True
def is_running():
    return app.is_running

############################
# Global app configuration #
############################

app.logger.addHandler(logger_file_handler())

# If the debug toolbar is installed then use it
if app.debug:
    try:
        from flask_debugtoolbar import DebugToolbarExtension
        app.config['SECRET_KEY'] = '''shh, it's a secret'''
        toolbar = DebugToolbarExtension(app)
    except ImportError:
        pass

# tell jinja to remove linebreaks
app.jinja_env.trim_blocks = True

# enable break and continue in jinja loops
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.jinja_env.add_extension('jinja2.ext.do')

# the following context processor inserts
#  * empty info={} dict variable
#  * body_class = ''
#  * bread = None for the default bread crumb hierarch
#  * title = 'LMFDB'
#  * meta_description, shortthanks, feedbackpage
#  * DEBUG and BETA variables storing whether running in each mode
@app.context_processor
def ctx_proc_userdata():
    # insert an empty info={} as default
    # set the body class to some default, blueprints should
    # overwrite it with their name, using @<blueprint_object>.context_processor
    # see http://flask.pocoo.org/docs/api/?highlight=context_processor#flask.Blueprint.context_processor
    vars = {'info': {}, 'body_class': ''}

    # insert the default bread crumb hierarchy
    # overwrite this variable when you want to customize it
    # For example, [ ('Bread', '.'), ('Crumb', '.'), ('Hierarchy', '.')]
    vars['bread'] = None

    # default title
    vars['title'] = r'LMFDB'

    # LMFDB version number displayed in footer
    vars['version'] = LMFDB_VERSION

    # meta_description appears in the meta tag "description"
    vars['meta_description'] = r'Welcome to the LMFDB, the database of L-functions, modular forms, and related objects. These pages are intended to be a modern handbook including tables, formulas, links, and references for L-functions and their underlying objects.'
    vars['shortthanks'] = r'This project is supported by <a href="%s">grants</a> from the US National Science Foundation, the UK Engineering and Physical Sciences Research Council, and the Simons Foundation.' % (url_for('acknowledgment') + "#sponsors")
    vars['feedbackpage'] = r"https://docs.google.com/spreadsheet/viewform?formkey=dDJXYXBleU1BMTFERFFIdjVXVmJqdlE6MQ"
    vars['LINK_EXT'] = lambda a, b: '<a href="%s" target="_blank">%s</a>' % (b, a)

    # debug mode?
    vars['DEBUG'] = is_debug_mode()
    vars['BETA'] = is_beta()

    return vars

# Harald suggested the following but it does not work
#
# create the sidebar from its yaml file and inject it into the jinja environment
#from lmfdb.homepage import get_sidebar
#app.jinja_env.globals['sidebar'] = get_sidebar()
#
# so instead we do this to ensure that the sidebar content is available to every page:
@app.context_processor
def inject_sidebar():
    from lmfdb.homepage import get_sidebar
    return dict(sidebar=get_sidebar())

##############################
# Bottom link to google code #
##############################

branch = "web"
if (os.getenv('BETA')=='1'):
    branch = "dev"

def git_infos():
    try:
        from subprocess import Popen, PIPE
        # cwd should be the root of git repo
        cwd = os.path.join(os.path.dirname(os.path.realpath(__file__)),"..")
        git_rev_cmd = '''git rev-parse HEAD'''
        git_date_cmd = '''git show --format="%ci" -s HEAD'''
        git_contains_cmd = '''git branch --contains HEAD'''
        git_reflog_cmd = '''git reflog -n5'''
        git_graphlog_cmd = '''git log --graph  -n 10'''
        rev = Popen([git_rev_cmd], shell=True, stdout=PIPE, cwd=cwd).communicate()[0]
        date = Popen([git_date_cmd], shell=True, stdout=PIPE, cwd=cwd).communicate()[0]
        contains = Popen([git_contains_cmd], shell=True, stdout=PIPE, cwd=cwd).communicate()[0]
        reflog = Popen([git_reflog_cmd], shell=True, stdout=PIPE, cwd=cwd).communicate()[0]
        graphlog = Popen([git_graphlog_cmd], shell=True, stdout=PIPE, cwd=cwd).communicate()[0]
        pairs = [[git_rev_cmd, rev],
                [git_date_cmd, date],
                [git_contains_cmd, contains],
                [git_reflog_cmd, reflog],
                [git_graphlog_cmd, graphlog]]
        summary = "\n".join([ "$ %s\n%s" % (c,o) for c, o in pairs] )
        cmd_output = rev, date,  summary
    except Exception:
        cmd_output = '-', '-', '-'
    return cmd_output

def git_summary():
    return "commit = %s\ndate = %s\ncontains = %s\nreflog = \n%s\n" % git_infos()

git_rev, git_date, _  = git_infos()

# Creates link to the source code at the most recent commit.
_url_source = 'https://github.com/LMFDB/lmfdb/tree/'
_current_source = '<a href="%s%s">%s</a>' % (_url_source, git_rev, "Source")

# Creates link to the list of revisions on the master, where the most recent commit is on top.
_url_changeset = 'https://github.com/LMFDB/lmfdb/commits/%s' % branch
_latest_changeset = '<a href="%s">%s</a>' % (_url_changeset, git_date)

@app.context_processor
def link_to_current_source():
    return {'current_source': _current_source,
            'latest_changeset': _latest_changeset,
            'sage_version': 'SageMath version %s' % SAGE_VERSION}

##############################
#      Jinja formatters      #
##############################

# you can pass in a datetime.datetime python object and via
# {{ <datetimeobject> | fmtdatetime }} you can format it inside a jinja template
# if you want to do more than just the default, use it for example this way:
# {{ <datetimeobject>|fmtdatetime('%H:%M:%S') }}
@app.template_filter("fmtdatetime")
def fmtdatetime(value, format='%Y-%m-%d %H:%M:%S'):
    import datetime
    if isinstance(value, datetime.datetime):
        return value.strftime(format)
    else:
        return "-"

# You can use this formatter to turn newlines in a string into HTML line breaks
@app.template_filter("nl2br")
def nl2br(s):
    return s.replace('\n', '<br>\n')

# You can use this formatter to encode a dictionary into a url string
@app.template_filter('urlencode')
def urlencode(kwargs):
    import urllib
    return urllib.urlencode(kwargs)

##############################
#    Redirects and errors    #
##############################

@app.before_request
def redirect_nonwww():
    """Redirect lmfdb.org requests to www.lmfdb.org"""
    from urlparse import urlparse, urlunparse
    urlparts = urlparse(request.url)
    if urlparts.netloc == 'lmfdb.org':
        replaced = urlparts._replace(netloc='www.lmfdb.org')
        return redirect(urlunparse(replaced), code=301)

def timestamp():
    return '[%s UTC]'%time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())

@app.errorhandler(404)
def not_found_404(error):
    app.logger.info('%s 404 error for URL %s %s'%(timestamp(),request.url,error.description))
    messages = error.description if isinstance(error.description,(list,tuple)) else (error.description,)
    return render_template("404.html", title='LMFDB Page Not Found', messages=messages), 404

@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s %s"%(timestamp(),request.url, error.args))
    return render_template("500.html", title='LMFDB Error'), 500

@app.errorhandler(503)
def not_found_503(error):
    return render_template("503.html"), 503

##############################
#           Cookies          #
##############################

@app.before_request
def get_menu_cookie():
    """
    sets cookie for show/hide sidebar
    """
    g.show_menu = str(request.cookies.get('showmenu')) != "False"

##############################
#       Top-level pages      #
##############################

@app.route("/")
def index():
    return render_template('index-boxes.html',
        titletag="The L-functions and modular forms database",
        title="LMFDB - The L-functions and Modular Forms Database",
        bread=None,
        boxes=load_boxes())

@app.route("/about")
def about():
    return render_template("about.html", title="About the LMFDB")

@app.route("/health")
@app.route("/alive")
def alive():
    """
    a basic health check
    """
    from lmfdb import db
    if db.is_alive():
        return "LMFDB!"
    else:
        abort(503)

@app.route("/statshealth")
def statshealth():
    """
    a health check on the stats pages
    """
    from lmfdb import db
    if db.is_alive():
        tc = app.test_client()
        for url in ['/NumberField/stats',
                    '/ModularForm/GL2/Q/holomorphic/stats',
                    '/EllipticCurve/Q/stats',
                    '/EllipticCurve/browse/2/',
                    '/EllipticCurve/browse/3/',
                    '/EllipticCurve/browse/4/',
                    '/EllipticCurve/browse/5/',
                    '/EllipticCurve/browse/6/',
                    '/Genus2Curve/Q/stats',
                    '/Belyi/stats',
                    '/HigherGenus/C/Aut/stats',
                    ]:
            try:
                if tc.get(url).status_code != 200:
                    abort(503)
            except Exception:
                abort(503)
        else:
            return "LMFDB stats are healthy!"
    else:
        abort(503)

@app.route("/info")
def info():
    from socket import gethostname
    output = ""
    output += "HOSTNAME = %s\n\n" % gethostname()
    output += "# PostgreSQL info\n";
    from lmfdb import db
    if not db.is_alive():
        output += "db is offline\n"
    else:
        conn_str = "%s" % db.conn
        output += "Connection: %s\n" % conn_str.replace("<","").replace(">","")
        output += "User: %s\n" % db._user
        output += "Read only: %s\n" % db._read_only
        output += "Read and write to userdb: %s\n" % db._read_and_write_userdb
        output += "Read and write to knowls: %s\n" % db._read_and_write_knowls
    output += "\n# GIT info\n";
    output += git_infos()[-1]
    output += "\n\n";
    
    return output.replace("\n", "<br>")

@app.route("/acknowledgment")
def acknowledgment():
    bread = [("Acknowledgments" , '')]
    return render_template("acknowledgment.html", title="Acknowledgments", contribs=contribs, bread=bread)

@app.route("/acknowledgment/activities")
def workshops():
    bread = [("Acknowledgments" , url_for('.acknowledgment')) , ("Activities", '')]
    return render_template("workshops.html", title="LMFDB Activities", contribs=contribs, bread=bread)

# google's CSE for www.lmfdb.org/* (and *only* those pages!)
@app.route("/search")
def search():
    return render_template("search.html", title="Search LMFDB", bread=[('Search', url_for("search"))])

@app.route('/L')
def l_functions():
    t = 'L-functions'
    b = [(t, url_for('l_functions'))]
    lm = [('History of L-functions', '/L/history'),('Completeness of the data',url_for('l_functions.completeness'))]
    return render_template('single.html', title=t, kid='lfunction.about', bread=b, learnmore=lm)

@app.route("/L/history")
def l_functions_history():
    t = 'L-functions'
    b = [(t, url_for('l_functions'))]
    b.append(('History', url_for("l_functions_history")))
    return render_template(_single_knowl, title="A Brief History of L-functions", kid='lfunction.history', body_class=_bc, bread=b)

@app.route('/ModularForm')
def modular_forms():
    t = 'Modular Forms'
    b = [(t, url_for('modular_forms'))]
    # lm = [('History of modular forms', '/ModularForm/history')]
    return render_template('single.html', title=t, kid='mf.about', bread=b) #, learnmore=lm)

@app.route("/ModularForm/history")
def modular_forms_history():
    t = 'Modular Forms'
    b = [(t, url_for('modular forms'))]
    b.append(('History', url_for("modular_forms_history")))
    return render_template(_single_knowl, title="A Brief History of Modular Forms", kid='mf.gl2.history', body_class=_bc, bread=b)

@app.route('/Variety')
def varieties():
    t = 'Varieties'
    b = [(t, url_for('varieties'))]
    # lm = [('History of varieties', '/Variety/history')]
    return render_template('single.html', title=t, kid='varieties.about', bread=b) #, learnmore=lm)

@app.route("/Variety/history")
def varieties_history():
    t = 'Varieties'
    b = [(t, url_for('varieties'))]
    b.append(('History', url_for("varieties_history")))
    return render_template(_single_knowl, title="A Brief History of Varieties", kid='ag.variety.history', body_class=_bc, bread=b)

@app.route('/Field')
def fields():
    t = 'Fields'
    b = [(t, url_for('fields'))]
    # lm = [('History of fields', '/Field/history')]
    return render_template('single.html', kid='field.about', title=t, body_class=_bc, bread=b) #, learnmore=lm)

@app.route("/Field/history")
def fields_history():
    t = 'Fields'
    b = [(t, url_for('fields'))]
    b.append(('History', url_for("fields_history")))
    return render_template(_single_knowl, title="A Brief History of Fields", kid='field.history', body_class=_bc, bread=b)

@app.route('/Representation')
def representations():
    t = 'Representations'
    b = [(t, url_for('representations'))]
    # lm = [('History of representations', '/Representation/history')]
    return render_template('single.html', kid='repn.about', title=t, body_class=_bc, bread=b) #, learnmore=lm)

@app.route("/Representation/history")
def representations_history():
    t = 'Representations'
    b = [(t, url_for('representations'))]
    b.append(('History', url_for("representations_history")))
    return render_template(_single_knowl, title="A Brief History of Representations", kid='repn.history', body_class=_bc, bread=b)

@app.route('/Motives')
def motives():
    t = 'Motives'
    b = [(t, url_for('motives'))]
    # lm = [('History of motives', '/Motives/history')]
    return render_template('single.html', kid='motives.about', title=t, body_class=_bc, bread=b) #, learnmore=lm)

@app.route("/Motives/history")
def motives_history():
    t = 'Motives'
    b = [(t, url_for('motives'))]
    b.append(('History', url_for("motives_history")))
    return render_template(_single_knowl, title="A Brief History of Motives", kid='motives.history', body_class=_bc, bread=b)

@app.route('/Group')
def groups():
    t = 'Groups'
    b = [(t, url_for('groups'))]
    # lm = [('History of groups', '/Group/history')]
    return render_template('single.html', kid='group.about', title=t, body_class=_bc, bread=b) #, learnmore=lm)

@app.route("/Group/history")
def groups_history():
    t = 'Groups'
    b = [(t, url_for('groups'))]
    b.append(('History', url_for("groups_history")))
    return render_template(_single_knowl, title="A Brief History of Groups", kid='group.history', body_class=_bc, bread=b)

@app.route("/editorial-board")
@app.route("/management-board")
@app.route("/management")
def editorial_board():
    t = "Editorial Board"
    b = [(t, url_for("editorial_board"))]
    return render_template('management.html', title=t, bread=b)

@app.route("/citation")
def citation():
    t = "Citing the LMFDB"
    b = [(t, url_for("citation"))]
    return render_template('citation.html', title=t, body_class='', bread=b)

@app.route("/citation/citing")
def citing():
    t = "How to Cite LMFDB"
    b = [("Citing the LMFDB", url_for("citation")), (t, url_for("citing"))]
    return render_template(_single_knowl, title=t, kid='content.how_to_cite', body_class='', bread=b)

@app.route("/citation/citations")
def citations():
    t = "LMFDB Citations"
    b = [("Citing the LMFDB", url_for("citation")), (t, url_for("citations"))]
    return render_template('citations.html', title=t, body_class='', bread=b)

@app.route("/citation/citations_bib")
def citations_bib():
    t = "LMFDB Citations (BiBTeX Entries)"
    return render_template('citations_content_bib.html', title=t, body_class='')

@app.route("/contact")
def contact():
    t = "Contact and Feedback"
    b = [(t, url_for("contact"))]
    return render_template('contact.html', title=t, body_class='', bread=b)

def root_static_file(name):
    def static_fn():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
        if os.path.exists(fn):
            return open(fn).read()
        critical("root_static_file: file %s not found!" % fn)
        return abort(404, 'static file %s not found.' % fn)
    app.add_url_rule('/%s' % name, 'static_%s' % name, static_fn)
map(root_static_file, ['favicon.ico'])


@app.route("/robots.txt")
def robots_txt():
    if "www.lmfdb.org".lower() in request.url_root.lower():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    # not running on www.lmfdb.org
    else:
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "default_robots.txt")
        if os.path.exists(fn):
            return open(fn).read()
    return "User-agent: *\nDisallow: / \n"

# geeky pages have humans.txt
@app.route("/humans.txt")
def humans_txt():
    return render_template("acknowledgment.html", title="Acknowledgments")

@app.context_processor
def add_colors():
    # FIXME:
    # - the template should use global variable g.color
    # - try to get the color from
    #       - the cookie
    #       - from the config file
    # - remove cookie at logout (see line 307 of users/main)
    # - add cookie at login or when a color change happens (see line 175 of users/main)
    from lmfdb.utils.color import all_color_schemes
    color = request.args.get('color')
    if color and color.isdigit():
        color = int(color)
    if color not in all_color_schemes:
        color = None
    if color is None:
        from flask_login import current_user
        userid = current_user.get_id()
        if userid is not None:
            from lmfdb.users.pwdmanager import userdb
            color = userdb.lookup(userid).get('color_scheme')
        if color not in all_color_schemes:
            color = None
        if color is None:
            from lmfdb.utils.config import Configuration
            color = Configuration().get_color()
    return dict(color=all_color_schemes[color].dict())

@app.route("/style.css")
def css():
    response = make_response(render_template("style.css"))
    response.headers['Content-type'] = 'text/css'
    # don't cache css file, if in debug mode.
    if current_app.debug:
        response.headers['Cache-Control'] = 'no-cache, no-store'
    else:
        response.headers['Cache-Control'] = 'public, max-age=600'
    return response

@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html", title="Not Yet Implemented")

# the checklist is used for human testing on a high-level, supplements test.sh

@app.route("/checklist-list")
def checklist_list():
    return render_template("checklist.html", body_class="checklist")

@app.route("/checklist")
def checklist():
    return render_template("checklist-fs.html")

##############################
#         Intro pages        #
##############################

# common base class and bread
_bc = 'intro'
intro_bread = lambda: [('Intro', url_for("introduction"))]

# template displaying just one single knowl as an KNOWL_INC
_single_knowl = 'single.html'


@app.route("/intro")
def introduction():
    b = intro_bread()
    return render_template(_single_knowl, title="Introduction", kid='intro', body_class=_bc, bread=b)

@app.route("/intro/features")
def introduction_features():
    b = intro_bread()
    b.append(('Features', url_for("introduction_features")))
    return render_template(_single_knowl, title="Features", kid='intro.features', body_class=_bc, bread=b)


@app.route("/intro/zetatour")
def introduction_zetatour():
    b = intro_bread()
    b.append(('Tutorial', url_for("introduction_zetatour")))
    return render_template(_single_knowl, title="A Tour of the Riemann Zeta Function", kid='intro.tutorial', body_class=_bc, bread=b)

@app.route("/bigpicture")
def bigpicture():
    b = [('Big Picture', url_for('bigpicture'))]
    return render_template("bigpicture.html", title="A Map of the LMFDB", body_class=_bc, bread=b)

@app.route("/universe")
def universe():
    b = [('LMFDB Universe', url_for('universe'))]
    return render_template("universe.html", title="The LMFDB Universe", body_class=_bc, bread=b)

@app.route("/news")
def news():
    t = "News"
    b = [(t, url_for('news'))]
    return render_template(_single_knowl, title="LMFDB in the News", kid='doc.news.in_the_news', body_class=_bc, bread=b)
