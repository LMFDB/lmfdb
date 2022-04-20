# -*- coding: utf-8 -*-
from .utils.config import get_secret_key
import os
from socket import gethostname
import time
from urllib.parse import urlparse, urlunparse

from flask import (
    Flask,
    abort,
    current_app,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import escape
from sage.env import SAGE_VERSION
from sage.all import cached_function
# acknowledgment page, reads info from CONTRIBUTORS.yaml

from .logger import logger_file_handler, critical
from .homepage import load_boxes, contribs

LMFDB_VERSION = "LMFDB Release 1.2.1"

############################
#         Main app         #
############################


class ReverseProxied():
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme

        return self.app(environ, start_response)

app = Flask(__name__)

app.wsgi_app = ReverseProxied(app.wsgi_app)

############################
# App attribute functions  #
############################


def is_debug_mode():
    return current_app.debug

# this is set here and is available for ctx_proc_userdata


@app.before_request
def set_beta_state():
    g.BETA = (os.getenv('BETA') == '1') or is_debug_mode()


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
        toolbar = DebugToolbarExtension(app)
    except ImportError:
        pass

# secret key, necessary for sessions, and sessions are
# in turn necessary for users to login
app.secret_key = get_secret_key()

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

    # debug mode?
    vars['DEBUG'] = is_debug_mode()
    vars['BETA'] = is_beta()

    def modify_url(**replace):
        urlparts = urlparse(request.url)
        urlparts = urlparts._replace(**replace)
        return urlunparse(urlparts)
    vars['modify_url'] = modify_url
    vars['zip'] = zip

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
    from .homepage import get_sidebar
    return dict(sidebar=get_sidebar())

##############################
# Bottom link to google code #
##############################


branch = "web"
if (os.getenv('BETA') == '1'):
    branch = "dev"


def git_infos():
    try:
        from subprocess import Popen, PIPE
        # cwd should be the root of git repo
        cwd = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
        commands = ['''git rev-parse HEAD''',
                    '''git show --format="%ci" -s HEAD''',
                    '''git branch --contains HEAD''',
                    '''git reflog -n5''',
                    '''git log --graph  -n 10''']
        kwdargs = {'shell': True, 'stdout': PIPE, 'cwd': cwd}
        kwdargs['encoding'] = 'utf-8'
        pairs = [(c, Popen(c, **kwdargs).communicate()[0]) for c in commands]
        rev = pairs[0][1]
        date = pairs[0][1]
        summary = "\n".join("$ %s\n%s" % p for p in pairs)
        return rev, date, summary
    except Exception:
        return '-', '-', '-'


git_rev, git_date, _ = git_infos()

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
    return s.replace('\n', '<br/>\n')

# You can use this formatter to encode a dictionary into a url string


@app.template_filter('urlencode')
def urlencode(kwargs):
    from urllib.parse import urlencode
    return urlencode(kwargs)

##############################
#    Redirects and errors    #
##############################


@app.before_request
def netloc_redirect():
    """
        Redirect lmfdb.org -> www.lmfdb.org
        Redirect {www, beta, }.lmfdb.com -> {www, beta, }.lmfdb.org
        Force https on www.lmfdb.org
        Redirect non-whitelisted routes from www.lmfdb.org to beta.lmfdb.org
    """
    from urllib.parse import urlparse, urlunparse

    urlparts = urlparse(request.url)

    if urlparts.netloc in ["lmfdb.org", "lmfdb.com", "www.lmfdb.com"]:
        replaced = urlparts._replace(netloc="www.lmfdb.org", scheme="https")
        return redirect(urlunparse(replaced), code=301)
    elif urlparts.netloc == "beta.lmfdb.com":
        replaced = urlparts._replace(netloc="beta.lmfdb.org", scheme="https")
        return redirect(urlunparse(replaced), code=301)
    elif (
        urlparts.netloc == "www.lmfdb.org"
        and request.headers.get("X-Forwarded-Proto", "http") != "https"
        and request.url.startswith("http://")
    ):
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)
    elif (
        urlparts.netloc == "www.lmfdb.org"
        and
        not white_listed(urlparts.path)
        and valid_bread(urlparts.path)
    ):
        replaced = urlparts._replace(netloc="beta.lmfdb.org", scheme="https")
        return redirect(urlunparse(replaced), code=302)


def timestamp():
    return '[%s UTC]' % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


@app.errorhandler(404)
def not_found_404(error):
    app.logger.info('%s 404 error for URL %s %s' % (timestamp(), request.url, error.description))
    messages = error.description if isinstance(error.description, (list, tuple)) else (error.description,)
    return render_template("404.html", title='LMFDB Page Not Found', messages=messages), 404


@app.errorhandler(500)
def not_found_500(error):
    app.logger.error("%s 500 error on URL %s %s" % (timestamp(), request.url, error.args))
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
                           title="The L-functions and modular forms database (LMFDB)",
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
    from . import db
    if db.is_alive():
        return "LMFDB!"
    else:
        abort(503)


@app.route("/statshealth")
def statshealth():
    """
    a health check on the stats pages
    """
    from . import db
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
    output = ""
    output += "HOSTNAME = %s\n\n" % gethostname()
    output += "# PostgreSQL info\n"
    from . import db
    if not db.is_alive():
        output += "db is offline\n"
    else:
        conn_str = "%s" % db.conn
        output += "Connection: %s\n" % conn_str.replace("<", "").replace(">", "")
        output += "User: %s\n" % db._user
        output += "Read only: %s\n" % db._read_only
        output += "Read and write to userdb: %s\n" % db._read_and_write_userdb
        output += "Read and write to knowls: %s\n" % db._read_and_write_knowls
    output += "\n# GIT info\n"
    output += git_infos()[-1]
    output += "\n\n"
    return output.replace("\n", "<br>")


@app.route("/acknowledgment")
def acknowledgment():
    bread = [("Acknowledgments", '')]
    return render_template("acknowledgment.html", title="Acknowledgments", contribs=contribs, bread=bread)


@app.route("/acknowledgment/activities")
def workshops():
    bread = [("Acknowledgments", url_for('.acknowledgment')), ("Activities", '')]
    return render_template("workshops.html", title="LMFDB Activities", contribs=contribs, bread=bread)


@app.route("/lucant")
@app.route("/LuCaNT")
def lucant():
    bread = [("LuCaNT", '')]
    return render_template("lucant.html", title="LMFDB, Computation, and Number Theory (LuCaNT)", contribs=contribs, bread=bread)

# google's CSE for www.lmfdb.org/* (and *only* those pages!)


@app.route("/search")
def search():
    return render_template("search.html", title="Search LMFDB", bread=[('Search', url_for("search"))])


@app.route('/ModularForm')
@app.route('/ModularForm/')
def modular_forms():
    t = 'Modular forms'
    b = [(t, url_for('modular_forms'))]
    # lm = [('History of modular forms', '/ModularForm/history')]
    return render_template('single.html', title=t, kid='mf.about', bread=b)  # , learnmore=lm)

# @app.route("/ModularForm/history")


def modular_forms_history():
    t = 'Modular forms'
    b = [(t, url_for('modular_forms'))]
    b.append(('History', url_for("modular_forms_history")))
    return render_template(_single_knowl, title="A brief history of modular forms", kid='mf.gl2.history', body_class=_bc, bread=b)


@app.route('/Variety')
@app.route('/Variety/')
def varieties():
    t = 'Varieties'
    b = [(t, url_for('varieties'))]
    # lm = [('History of varieties', '/Variety/history')]
    return render_template('single.html', title=t, kid='varieties.about', bread=b)  # , learnmore=lm)

# @app.route("/Variety/history")


def varieties_history():
    t = 'Varieties'
    b = [(t, url_for('varieties'))]
    b.append(('History', url_for("varieties_history")))
    return render_template(_single_knowl, title="A brief history of varieties", kid='ag.variety.history', body_class=_bc, bread=b)


@app.route('/Field')
@app.route('/Field/')
def fields():
    t = 'Fields'
    b = [(t, url_for('fields'))]
    # lm = [('History of fields', '/Field/history')]
    return render_template('single.html', kid='field.about', title=t, body_class=_bc, bread=b)  # , learnmore=lm)

# @app.route("/Field/history")


def fields_history():
    t = 'Fields'
    b = [(t, url_for('fields'))]
    b.append(('History', url_for("fields_history")))
    return render_template(_single_knowl, title="A brief history of fields", kid='field.history', body_class=_bc, bread=b)


@app.route('/Representation')
@app.route('/Representation/')
def representations():
    t = 'Representations'
    b = [(t, url_for('representations'))]
    # lm = [('History of representations', '/Representation/history')]
    return render_template('single.html', kid='repn.about', title=t, body_class=_bc, bread=b)  # , learnmore=lm)

# @app.route("/Representation/history")


def representations_history():
    t = 'Representations'
    b = [(t, url_for('representations'))]
    b.append(('History', url_for("representations_history")))
    return render_template(_single_knowl, title="A brief history of representations", kid='repn.history', body_class=_bc, bread=b)


@app.route('/Motive')
@app.route('/Motive/')
def motives():
    t = 'Motives'
    b = [(t, url_for('motives'))]
    # lm = [('History of motives', '/Motives/history')]
    return render_template('single.html', kid='motives.about', title=t, body_class=_bc, bread=b)  # , learnmore=lm)

# @app.route("/Motives/history")


def motives_history():
    t = 'Motives'
    b = [(t, url_for('motives'))]
    b.append(('History', url_for("motives_history")))
    return render_template(_single_knowl, title="A brief history of motives", kid='motives.history', body_class=_bc, bread=b)


@app.route('/Group')
@app.route('/Group/')
def groups():
    t = 'Groups'
    b = [(t, url_for('groups'))]
    # lm = [('History of groups', '/Group/history')]
    return render_template('single.html', kid='group.about', title=t, body_class=_bc, bread=b)  # , learnmore=lm)

# @app.route("/Group/history")


def groups_history():
    t = 'Groups'
    b = [(t, url_for('groups'))]
    b.append(('History', url_for("groups_history")))
    return render_template(_single_knowl, title="A brief history of groups", kid='group.history', body_class=_bc, bread=b)


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


@app.route("/contact")
def contact():
    t = "Contact and Feedback"
    b = [(t, url_for("contact"))]
    return render_template('contact.html', title=t, body_class='', bread=b)


def root_static_file(name):
    def static_fn():
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
        if os.path.exists(fn):
            return open(fn, "rb").read()
        critical("root_static_file: file %s not found!" % fn)
        return abort(404, 'static file %s not found.' % fn)
    app.add_url_rule('/%s' % name, 'static_%s' % name, static_fn)


for fn in ['favicon.ico']:
    root_static_file(fn)


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
    from .utils.color import all_color_schemes
    color = request.args.get('color')
    if color and color.isdigit():
        color = int(color)
    if color not in all_color_schemes:
        color = None
    if color is None:
        from flask_login import current_user
        userid = current_user.get_id()
        if userid is not None:
            from .users.pwdmanager import userdb
            color = userdb.lookup(userid).get('color_scheme')
        if color not in all_color_schemes:
            color = None
        if color is None:
            from .utils.config import Configuration
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
def intro_bread():
    return [('Intro', url_for("introduction"))]


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
    return render_template(_single_knowl, title="A tour of the Riemann zeta function", kid='intro.tutorial', body_class=_bc, bread=b)


@app.route("/bigpicture")
def bigpicture():
    b = [('Big picture', url_for('bigpicture'))]
    return render_template("bigpicture.html", title="A map of the LMFDB", body_class=_bc, bread=b)


@app.route("/universe")
def universe():
    b = [('LMFDB universe', url_for('universe'))]
    return render_template("universe.html", title="The LMFDB universe", body_class=_bc, bread=b)


@app.route("/news")
def news():
    t = "News"
    b = [(t, url_for('news'))]
    return render_template(_single_knowl, title="LMFDB in the news", kid='doc.news.in_the_news', body_class=_bc, bread=b)


###############################################
# White listing routes for www.lmfdb.org      #
###############################################

@cached_function
def routes():
    """
    Returns all routes
    """
    links = []
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if "GET" in rule.methods:  # and has_no_empty_params(rule):
            try:
                url = url_for(rule.endpoint, **(rule.defaults or {}))
            except Exception:
                url = None
            links.append((url, str(rule)))
    return sorted(links, key=lambda elt: elt[1])


@app.route("/sitemap")
def sitemap():
    """
    Listing all routes
    """
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><a href="{0}">{1}</a></li>'.format(url, endpoint)
                if url is not None
                else "<li>{0}</li>".format(endpoint)
                for url, endpoint in routes()
            ]
        )
        + "</ul>"
    )


@cached_function
def WhiteListedRoutes():
    return [
        'ArtinRepresentation',
        'Character/Dirichlet',
        'Character/calc-gauss/Dirichlet',
        'Character/calc-jacobi/Dirichlet',
        'Character/calc-kloosterman/Dirichlet',
        'Character/calc-value/Dirichlet',
        'EllipticCurve',
        'Field',
        'GaloisGroup',
        'Genus2Curve/Q',
        'Group/foo', # allows /Group but not /Groups/*
        'HigherGenus/C/Aut',
        'L/Completeness',
        'L/CuspForms',
        'L/Labels',
        'L/Lhash',
        'L/Plot',
        'L/Riemann',
        'L/SymmetricPower',
        'L/contents',
        'L/degree',
        'L/download',
        'L/history',
        'L/interesting',
        'L/lhash',
        'L/rational',
        'L/tracehash',
        'L/download',
        'LocalNumberField',
        'LuCaNT',
        'ModularForm/GL2/ImaginaryQuadratic',
        'ModularForm/GL2/Q/Maass',
        'ModularForm/GL2/Q/holomorphic',
        'ModularForm/GL2/TotallyReal',
        'NumberField',
        'Representation/foo',  # allows /Representation but not /Representation/Galois/ModL/
        'SatoTateGroup',
        'Variety/Abelian/Fq',
        'about',
        'acknowledgment',
        'alive',
        'api',
        #'api2',
        'bigpicture',
        'callback_ajax',
        'citation',
        'contact',
        'editorial-board',
        'favicon.ico',
        'features',
        'forcebetasitemap',
        'health',
        'humans.txt',
        'info',
        'intro',
        'knowledge',
        'lucant',
        'management',
        'padicField',
        'news',
        'not_yet_implemented',
        'random',
        'robots.txt',
        'search',
        'sitemap',
        'static',
        'statshealth',
        'style.css',
        'universe',
        'users',
        'whitelistedsitemap',
        'zeros/zeta'
    ]


@cached_function
def WhiteListedBreads():
    res = set()
    for elt in WhiteListedRoutes():
        bread = ''
        for s in elt.split('/'):
            if bread:
                bread += '/' + s
            else:
                bread = s
            res.add(bread)
    return res


@cached_function
def white_listed(url):
    url = url.rstrip("/").lstrip("/")
    if not url:
        return True
    if (
        any(url.startswith(elt) for elt in WhiteListedRoutes())
        # check if is an allowed bread
        or url in WhiteListedBreads()
    ):
        return True
    # check if it starts with an L
    elif url[:2] == "L/":
        # if the origin is allowed
        # or if it is a L-function with a label
        return white_listed(url[1:]) or len(url) == 2 or url[2].isdigit()
    else:
        return False


@cached_function
def NotWhiteListedBreads():
    res = set()
    for _, endpoint in routes():
        if not white_listed(endpoint):
            res.add(endpoint.lstrip("/").split('/', 1)[0])
    res.remove('L') # all the valid breads are whitelisted
    return res


@cached_function
def valid_bread(url):
    url = url.lstrip("/")
    return url.split('/', 1)[0] in NotWhiteListedBreads()


@app.route("/forcebetasitemap")
def forcebetasitemap():
    """
    Listing routes that are not allowed on www.lmfdb.org
    """
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><a href="{0}">{1}</a></li>'.format(escape(url), escape(endpoint))
                if url is not None
                else "<li>{0}</li>".format(escape(endpoint))
                for url, endpoint in routes()
                if not white_listed(endpoint) and valid_bread(endpoint)
            ]
        )
        + "</ul>" + str(NotWhiteListedBreads())
    )


@app.route("/whitelistedsitemap")
def whitelistedsitemap():
    """
    Listing routes that are allowed on www.lmfdb.org
    """
    return (
        "<ul>"
        + "\n".join(
            [
                '<li><href="{0}">{1}</a></li>'.format(escape(url), escape(endpoint))
                if url is not None
                else "<li>{0}</li>".format(escape(endpoint))
                for url, endpoint in routes()
                if white_listed(endpoint)
            ]
        )
        + "</ul>"
    )
