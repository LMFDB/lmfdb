# See views/emf_main.py, genus2_curves/main.py

from flask import render_template, url_for, redirect, abort, request
import re
from collections import defaultdict
from lmfdb.db_backend import db
from lmfdb.modular_forms.elliptic_modular_forms import emf
from lmfdb.search_parsing import parse_ints, parse_signed_ints, parse_bool, parse_nf_string, integer_options
from lmfdb.search_wrapper import search_wrap
from lmfdb.utils import flash_error
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.modular_forms.elliptic_modular_forms.web_newform import WebNewform
from lmfdb.modular_forms.elliptic_modular_forms.web_space import WebNewformSpace, WebGamma1Space, DimGrid, character_orbit_index
from sage.databases.cremona import class_to_int, cremona_letter_code

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
    info["mf_url"] = lambda mf: url_for_label(mf['label'])
    def nf_link(mf):
        nf_label = mf.get('nf_label')
        if nf_label:
            return '<a href="{0}"> {1} </a>'.format(url_for("number_fields.by_label", label=nf_label),
                                                    field_pretty(nf_label))
        else:
            return "Not in LMFDB"
    info["nf_link"] = nf_link
    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series'}

@emf.route("/")
def index():
    if len(request.args) > 0:
        if request.args.get('submit') == 'Dimensions':
            for key in newform_only_fields:
                if key in request.args:
                    return dimension_form_search(request.args)
            return dimension_space_search(request.args)
        else:
            return newform_search(request.args)
    info = {}
    newform_labels = ('1.12.a.a','11.2.a.a')
    info["newform_list"] = [ {'label':label,'url':url_for_label(label)} for label in newform_labels ]
    space_labels = ('20.5','60.2','55.3.d')
    info["space_list"] = [ {'label':label,'url':url_for_label(label)} for label in space_labels ]
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
    return redirect(url_for_label(label), 307)

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
    info = {'results':space.newforms, # so we can reuse search result code
            'CC_lown': 2,
            'CC_highn': 10,
            'CC_lowm': 0,
            'CC_highm': 10, # Actually may need min(10, number of embeddings)
            'CC_prec': 6}
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
    info={}
    set_info_funcs(info)
    return render_template("emf_full_gamma1_space.html",
                           info=info,
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

@emf.route("/<int:level>/<int:weight>/<int:conrey_label>/")
def by_url_space_conreylabel(level, weight, conrey_label):
    char_orbit = character_orbit_index(level, weight, conrey_label)
    label = str(level)+"."+str(weight)+"."+cremona_letter_code(char_orbit - 1)
    print label
    return redirect(url_for_label(label), code=301)

@emf.route("/<int:level>/<int:weight>/<char_orbit>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit, hecke_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit+"."+hecke_orbit
    return render_newform_webpage(label)

@emf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/")
def by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit):
    char_orbit = character_orbit_index(level, weight, conrey_label)
    label = str(level)+"."+str(weight)+"."+cremona_letter_code(char_orbit - 1)+"."+hecke_orbit
    return redirect(url_for_label(label), code=301)

@emf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/<int:embedding>")
def by_url_newform_conreylabel_with_embedding(level, weight, conrey_label, hecke_orbit, embedding):
    assert embedding > 0
    return by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit)



def url_for_label(label):
    slabel = label.split(".")
    if len(slabel) == 4:
        return url_for(".by_url_newform_label", level=slabel[0], weight=slabel[1], char_orbit=slabel[2], hecke_orbit=slabel[3])
    elif len(slabel) == 3:
        return url_for(".by_url_space_label", level=slabel[0], weight=slabel[1], char_orbit=slabel[2])
    elif len(slabel) == 2:
        return url_for(".by_url_full_gammma1_space_label", level=slabel[0], weight=slabel[1])
    elif len(slabel) == 1:
        return url_for(".by_url_level", level=slabel[0])
    else:
        raise ValueError("Invalid label")

def newform_jump(info):
    jump = info["jump"].strip()
    # TODO use LABEL_RE from web_newform
    if re.match(r'^\d+\.\d+\.[a-z]+\.[a-z]+$',jump):
        return redirect(url_for_label(jump), 301)
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

newform_only_fields = ['dim','nf_label','is_cm','cm_disc','is_twist_minimal','has_inner_twist']
def common_parse(info, query):
    parse_ints(info, query, 'weight', name="Weight")
    parse_ints(info, query, 'level', name="Level")
    parse_ints(info, query, 'char_orbit', name="Character orbit label")
    parse_ints(info, query, 'dim', name="Coefficient field dimension")
    parse_nf_string(info, query,'nf_label', name="Field")
    parse_bool(info, query, 'is_cm',name='is CM') # TODO think more about provability here, should things when should we include things which are _possibly_ cm but probably not.
    #parse_signed_ints(info, query, 'cm_disc', name="CM disciminant")
    parse_ints(info, query, 'cm_disc', name="CM discriminant")
    parse_bool(info, query, 'is_twist_minimal',name='is twist minimal')
    if 'has_inner_twist' in info:
        hit = info['has_inner_twist']
        if hit == 'yes':
            query['has_inner_twist'] = 1
        elif hit == 'not_no':
            query['has_inner_twist'] = {'$gt' : -1}
        elif hit == 'not_yes':
            query['has_inner_twist'] = {'$lt' : 1}
        elif hit == 'no':
            query['has_inner_twist'] = -1

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
    common_parse(info, query)
    set_info_funcs(info)

def set_rows_cols(info, query):
    """
    Sets weight_list and level_list, which are the row and column headers
    """
    info['weight_list'] = integer_options(info['weight'], max_opts=100)
    if 'odd_weight' in query:
        if query['odd_weight']:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 1]
        else:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 0]
    info['level_list'] = integer_options(info['level'], max_opts=2000)
    if len(info['weight_list']) * len(info['level_list']) > 10000:
        raise ValueError("Table too large")

def has_data(N, k):
    return k > 1 and N*k*k <= 500
def dimension_space_postprocess(res, info, query):
    set_rows_cols(info, query)
    dim_dict = {(N,k):DimGrid() for N in info['level_list'] for k in info['weight_list'] if has_data(N,k)}
    for space in res:
        dims = DimGrid.from_db(space)
        N = space['level']
        k = space['weight']
        dim_dict[N,k] += dims
    if query.get('char_order') == 1:
        def url_generator(N, k):
            return url_for(".by_url_space_label", level=N, weight=k, char_orbit="a")
    else:
        def url_generator(N, k):
            return url_for(".by_url_full_gammma1_space_label", level=N, weight=k)
    def pick_table(entry, X, typ):
        return entry[X][typ]
    def switch_text(X, typ):
        space_type = {'M':' modular forms',
                      'S':' cusp forms',
                      'E':' Eisenstein series'}
        return typ.capitalize() + space_type[X]
    info['pick_table'] = pick_table
    info['cusp_types'] = ['M','S','E']
    info['newness_types'] = ['all','new','old']
    info['one_type'] = False
    info['switch_text'] = switch_text
    info['url_generator'] = url_generator
    info['has_data'] = has_data
    return dim_dict
def dimension_form_postprocess(res, info, query):
    urlgen_info = dict(info)
    urlgen_info['count'] = 50
    set_rows_cols(info, query)
    dim_dict = {(N,k):0 for N in info['level_list'] for k in info['weight_list'] if has_data(N,k)}
    for form in res:
        N = form['level']
        k = form['weight']
        dim_dict[N,k] += form['dim']
    def url_generator(N, k):
        info_copy = dict(urlgen_info)
        info_copy['submit'] = 'Search'
        info_copy['level'] = str(N)
        info_copy['weight'] = str(k)
        return url_for(".index", **info_copy)
    def pick_table(entry, X, typ):
        # Only support one table
        return entry
    info['pick_table'] = pick_table
    info['cusp_types'] = ['S']
    info['newness_types'] = ['new']
    info['one_type'] = True
    info['url_generator'] = url_generator
    info['has_data'] = has_data
    return dim_dict

@search_wrap(template="emf_dimension_search_results.html",
             table=db.mf_newforms,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_form_postprocess,
             bread=lambda:[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def dimension_form_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    common_parse(info, query)

@search_wrap(template="emf_dimension_search_results.html",
             table=db.mf_newspaces,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_space_postprocess,
             bread=lambda:[], # FIXME
             learnmore=learnmore_list,
             credit=credit)
def dimension_space_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    common_parse(info, query)

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
