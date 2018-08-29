
# See views/emf_main.py, genus2_curves/main.py

from flask import render_template, redirect, abort
from lmfdb.db_backend import db
from lmfdb.modular_forms.elliptic_modular_forms import emf
from lmfdb.search_parsing import parse_ints # and more
from lmfdb.search_wrapper import search_wrap
from lmfdb.modular_forms.elliptic_modular_forms.web_newform import WebNewform
from lmfdb.modular_forms.elliptic_modular_forms.web_space import WebModformSpace

def learnmore_list():
    # FIXME
    pass

def credit():
    # FIXME
    return "???"

@emf.route("/")
def index():
    info = {}
    bread = [] # Fix
    return render_template("browse.html",
                           info=info,
                           credit=credit_string,
                           title="Holomorphic Cusp Forms",
                           learnmore=learnmore_list(),
                           bread=bread)

@emf.route("/random")
def random_form():
    label = db.mf_newforms.random()
    return redirect(url_for_newform_label(label), 307)

# Add routing for specifying an initial segment of level, weight, etc.
# Also url_for_...

def render_newform_webpage(label):
    try:
        newform = WebNewform.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)
    return render_template("newform.html",
                           newform=newform,
                           properties=newform.properties,
                           credit=credit(),
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.title,
                           friends=newform.friends)

def render_space_webpage(label):
    try:
        space = WebModformSpace.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)
    return render_template("space.html",
                           space=space,
                           properties=space.properties,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

def newform_jump(info):
    # FIXME
    pass

def space_jump(info):
    # FIXME
    pass

def download_exact(info):
    # FIXME
    pass

@search_wrap(template="newform_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':newform_jump,
                        'download_exact':download_exact,
                        'download_complex':download_complex},
             bread=[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def newform_search(info, query):
    info['CC_lown'] = 2
    info['CC_highn'] = 10
    info['CC_lowm'] = 0
    info['CC_highm'] = 10 # Actually may need min(10, number of embeddings)
    info['CC_prec'] = 6
    parse_ints(info, query, 'weight')
    # ADD MORE

@search_wrap(template="space_search_results.html",
             table=db.mf_newspaces,
             title='Newform Space Search Results',
             err_title='Newform Space Search Input Error',
             shortcuts={'jump':space_jump},
             bread=[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def space_search(info, query):
    parse_ints(info, query, 'weight')
    # ADD MORE

@emf.route("/Completeness")
def completeness_page():
    # FIXME
    pass

@emf.route("/Source")
def how_computed_page():
    # FIXME
    pass

@emf.route("/Labels")
def labels_page():
    # FIXME
    pass
