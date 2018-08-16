# -*- coding: utf-8 -*-
import os
from base import app
from flask import render_template, url_for, abort

@app.route("/about")
def about():
    return render_template("about.html", title="About the LMFDB")

# acknowledgement page, reads info from CONTRIBUTORS.yaml
try:
  import yaml
except:
  print "You have to install pyyaml"
  exit(0)

# reading and sorting list of contributors once at startup
_curdir = os.path.dirname(os.path.abspath(__file__))
contribs = yaml.load_all(open(os.path.join(_curdir, "..", "CONTRIBUTORS.yaml")))
contribs = sorted(contribs, key = lambda x : x['name'].split()[-1])

# basic health check
@app.route("/health")
@app.route("/alive")
def alive():
    from lmfdb.db_backend import db
    if db.is_alive():
        return "LMFDB!"
    else:
        abort(503)

@app.route("/info")
def info():
    from base import git_infos
    output = "# GIT info\n";
    output += git_infos()[-1]
    output += "\n\n";
    from lmfdb.db_backend import db
    if not db.is_alive():
        output += "offline\n"
        return output
    output += "# PostgreSQL info\n";
    conn_str = "%s" % db.conn
    output += "Connection: %s\n" % conn_str.replace("<","").replace(">","")
    output += "User: %s\n" % db._user
    output += "Read only: %s\n" % db._read_only
    output += "Read/write to userdb: %s\n" % db._read_and_write_userdb
    output += "Read/write to knowls: %s\n" % db._read_and_write_knowls
    return output.replace("\n", "<br>")

@app.route("/acknowledgment")
def acknowledgment():
    bread = [("Acknowledgments" , '')]
    return render_template("acknowledgment.html", title="Acknowledgments", contribs = contribs, bread = bread)

@app.route("/acknowledgment/activities")
def workshops():
    bread = [("Acknowledgments" , url_for('.acknowledgment')) , ("Activities", '')]
    return render_template("workshops.html", title="LMFDB Activities", contribs = contribs, bread = bread)


class Box(object):
    def __init__(self, title):
        self.title = title
        self.content = None
        self.links = []
        self.target = "/"
        self.img = None

    def add_link(self, title, href):
        self.links.append((title, href))

the_boxes = None

def load_boxes():
    boxes = []
    listboxes = yaml.load_all(open(os.path.join(_curdir, "index_boxes.yaml")))
    for b in listboxes:
        B = Box(b['title'])
        B.content = b['content']
        if 'image' in b:
            B.img = url_for('static', filename='images/'+b['image']+'.png')
        for title, url in b['links']:
            B.add_link(title, url)
        boxes.append(B)
    return boxes

@app.route("/")
def index():
    global the_boxes
    if the_boxes is None:
        the_boxes = load_boxes()
    boxes = the_boxes
    tmpl = "index-boxes.html"
    bread = None
    # We used to have an old version of the home page:
    # tmpl = "index-boxes.html" if g.BETA else "index.html"

    return render_template(tmpl,
        titletag="The L-functions and modular forms database",
        title="LMFDB - The L-functions and Modular Forms Database",
        bread=bread,
        boxes = boxes)

# Harald suggested putting the following in base.pybut it does not work either there or here!
#
# create the sidebar from its yaml file and inject it into the jinja environment
#from sidebar import get_sidebar
#app.jinja_env.globals['sidebar'] = get_sidebar()
#
# so instead we do this to ensure that the sidebar content is available to every page:
@app.context_processor
def inject_sidebar():
    from sidebar import get_sidebar
    return dict(sidebar=get_sidebar())


# geeky pages have humans.txt
@app.route("/humans.txt")
def humans_txt():
    return render_template("acknowledgment.html", title="Acknowledgments")

# google's CSE for www.lmfdb.org/* (and *only* those pages!)
@app.route("/search")
def search():
    return render_template("search.html", title="Search LMFDB", bread=[('Search', url_for("search"))])

##
## INTRO PAGES
##

# common base class
_bc = 'intro'

bread = lambda: [('Intro', url_for("introduction"))]

# template displaying just one single knowl as an KNOWL_INC
_single_knowl = 'single.html'


@app.route("/intro")
def introduction():
    b = bread()
    return render_template(_single_knowl, title="Introduction", kid='intro', body_class=_bc, bread=b)


@app.route("/intro/features")
def introduction_features():
    b = bread()
    b.append(('Features', url_for("introduction_features")))
    return render_template(_single_knowl, title="Features", kid='intro.features', body_class=_bc, bread=b)


@app.route("/intro/zetatour")
def introduction_zetatour():
    b = bread()
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


@app.route("/roadmap")
def roadmap():
    t = "Future Plans"
    b = [(t, url_for('roadmap'))]
    return render_template('roadmap.html', title=t, body_class=_bc, bread=b)

@app.route("/news")
def news():
    t = "News"
    b = [(t, url_for('news'))]
    return render_template(_single_knowl, title="LMFDB in the News", kid='doc.news.in_the_news', body_class=_bc, bread=b)

## INTRO PAGES END

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
    return render_template(_single_knowl, title="A brief history of varieties", kid='ag.variety.history', body_class=_bc, bread=b)


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
    return render_template(_single_knowl, title="A Brief History of Fields", kid='f.history', body_class=_bc, bread=b)


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
    return render_template(_single_knowl, title="A brief History of Representations", kid='rep.history', body_class=_bc, bread=b)



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
    return render_template(_single_knowl, title="A brief History of Groups", kid='g.history', body_class=_bc, bread=b)

@app.route("/editorial-board")
@app.route("/management-board")
@app.route("/management")
def management_board():
    t = "Management Board"
    b = [(t, url_for("management_board"))]
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
    return render_template(_single_knowl, title=t, kid='content.how-to-cite', body_class='', bread=b)

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
