# See views/emf_main.py, genus2_curves/main.py

from flask import render_template, url_for, redirect, abort, request
import re
from lmfdb.db_backend import db
from lmfdb.modular_forms.elliptic_modular_forms import emf
from lmfdb.search_parsing import parse_ints, parse_signed_ints, parse_bool, parse_nf_string
from lmfdb.search_wrapper import search_wrap
from lmfdb.utils import flash_error
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.modular_forms.elliptic_modular_forms.web_newform import WebNewform
from lmfdb.modular_forms.elliptic_modular_forms.web_space import WebNewformSpace, WebGamma1Space

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Holomorphic newform labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def credit():
    # FIXME
    return "???"

def set_info_funcs(info):
    info["mf_url"] = lambda mf: url_for_newform_label(mf['label'])
    def nf_link(mf):
        nf_label = mf.get('nf_label')
        if nf_label:
            return '<a href="{0}"> {1} </a>'.format(url_for("number_fields.by_label", label=nf_label),
                                                    field_pretty(nf_label))
        else:
            return "Not in LMFDB"
    info["nf_link"] = nf_link

@emf.route("/")
def index():
    if len(request.args) > 0:
        return newform_search(request.args)
    info = {}
    newform_labels = ('1.12.a.a','11.2.a.a')
    info["newform_list"] = [ {'label':label,'url':url_for_newform_label(label)} for label in newform_labels ]
    info["weight_list"] = ('2', '3-4', '5-9', '10-50')
    info["level_list"] = ('1', '2-9', '10-99', '100-1000')
    bread = [] # Fix
    return render_template("emf_browse.html",
                           info=info,
                           credit=credit(),
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
    return render_template("emf_newform.html",
                           newform=newform,
                           properties2=newform.properties,
                           credit=credit(),
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.title,
                           friends=newform.friends)

def render_space_webpage(label):
    try:
        space = WebNewformSpace.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info = {'results':space.newforms} # so we can reuse search result code
    set_info_funcs(info)
    return render_template("emf_space.html",
                           info=info,
                           space=space,
                           properties=space.properties,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

def render_full_gamma1_space_webpage(label):
    try:
        space = WebGamma1Space.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    return render_template("emf_full_gamma1_space.html",
                           space=space,
                           properties=space.properties,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@emf.route("/<int:level>/")
def by_url_level(level):
    return newform_search({'level' : level})

@emf.route("/<int:level>/<int:weight>/")
def by_url_full_gammma1_space_label(level, weight):
    label = str(level)+"."+str(weight)
    return render_full_gamma1_space_webpage(label)

@emf.route("/<int:level>/<int:weight>/<char_orbit>/")
def by_url_space_label(level, weight, char_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit
    return render_space_webpage(label)

@emf.route("/<int:level>/<int:weight>/<char_orbit>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit, hecke_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit+"."+hecke_orbit
    return render_newform_webpage(label)

def url_for_newform_label(label):
    slabel = label.split(".")
    return url_for(".by_url_newform_label", level=slabel[0], weight=slabel[1], char_orbit=slabel[2], hecke_orbit=slabel[3])

# TODO unused, will be for space_jump
def url_for_space_label(label):
    slabel = label.split(".")
    return url_for(".by_url_space_label", level=slabel[0], weight=slabel[1], char_orbit=slabel[2][1:])

def newform_jump(info):
    jump = info["jump"].strip()
    # TODO use LABEL_RE from web_newform
    if re.match(r'^\d+\.\d+\.[a-z]+\.[a-z]+$',jump):
        return redirect(url_for_newform_label(jump), 301)
    else:
        errmsg = "%s is not a valid newform orbit label"
    flash_error (errmsg, jump)
    return redirect(url_for(".index"))

def space_jump(info):
    # FIXME
    #if re.match(r'^\d+\.\d+\.\d+$',jump):
    #    return redirect(url_for_isogeny_class_label(jump), 301)
    #else:
    #    errmsg = "%s is not a valid newspace label"
    #flash_error (errmsg, jump)
    #return redirect(url_for(".index"))
    pass

def download_exact(info):
    # FIXME
    pass

def download_complex(info):
    # FIXME
    pass

@search_wrap(template="emf_newform_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':newform_jump,
                        'download_exact':download_exact,
                        'download_complex':download_complex},
             bread=lambda:[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def newform_search(info, query):
    info['CC_lown'] = 2
    info['CC_highn'] = 10
    info['CC_lowm'] = 0
    info['CC_highm'] = 10 # Actually may need min(10, number of embeddings)
    info['CC_prec'] = 6
    parse_ints(info, query, 'weight', name="Weight")
    parse_ints(info, query, 'level', name="Level")
    parse_ints(info, query, 'char_orbit', name="Character orbit label")
    parse_ints(info, query, 'dim', name="Coefficient field dimension")
    parse_nf_string(info, query,'nf_label', name="Field")
    parse_bool(info, query, 'is_cm',name='is CM') # TODO think more about provability here, should things when should we include things which are _possibly_ cm but probably not.
    #parse_signed_ints(info, query, 'cm_disc', name="CM disciminant")
    parse_ints(info, query, 'cm_disc', name="CM discriminant")
    parse_bool(info, query, 'is_twist_minimal',name='is twist minimal')
    parse_bool(info, query, 'inner_twist',name='has an inner twist')
    set_info_funcs(info)

@search_wrap(template="emf_space_search_results.html",
             table=db.mf_newspaces,
             title='Newform Space Search Results',
             err_title='Newform Space Search Input Error',
             shortcuts={'jump':space_jump},
             bread=lambda:[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def space_search(info, query):
    parse_ints(info, query, 'weight')
    # ADD MORE

@emf.route("/Completeness")
def completeness_page():
    t = 'Completeness of $\GL_2$ holomorphic newform data over $\Q$'
    bread = (('Holomorphic Newforms', url_for(".index")), ('Completeness',''))
    return render_template("single.html", kid='dq.mf.elliptic.extent',
                           credit=credit(), title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@emf.route("/Source")
def how_computed_page():
    t = 'Source of $\GL_2$ holomorphic newform data over $\Q$'
    bread = (('Holomorphic Newforms', url_for(".index")) ,('Source',''))
    return render_template("single.html", kid='dq.mf.elliptic.source',
                           credit=credit(), title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@emf.route("/Labels")
def labels_page():
    t = 'Labels for $\GL_2$ holomorphic newforms over $\Q$'
    bread = (('Holomorphic Newforms', url_for(".index")), ('Labels',''))
    return render_template("single.html", kid='mf.elliptic.label',
                           credit=credit(), title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
