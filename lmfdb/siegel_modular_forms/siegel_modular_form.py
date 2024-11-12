# -*- coding: utf-8 -*-
from collections import defaultdict
import re
import os
import yaml

from flask import render_template, url_for, redirect, abort, request
from sage.all import (
    ZZ, next_prime, cartesian_product_iterator,
    cached_function, prime_range, prod, gcd, nth_prime)
from sage.databases.cremona import class_to_int, cremona_letter_code

from lmfdb import db
from lmfdb.utils import (
    parse_ints, parse_floats, parse_bool, parse_primes, parse_nf_string,
    parse_noop, parse_equality_constraints, integer_options, parse_subset,
    search_wrap, display_float, factor_base_factorization_latex,
    flash_error, to_dict, comma, display_knowl, bigint_knowl, num2letters,
    SearchArray, TextBox, TextBoxNoEg, SelectBox, TextBoxWithSelect, YesNoBox,
    DoubleSelectBox, BasicSpacer, RowSpacer, HiddenBox, SearchButtonWithSelect,
    SubsetBox, ParityMod, CountBox, SelectBoxNoEg,
    StatsDisplay, proportioners, totaler, integer_divisors,
    redirect_no_cache)
from psycodict.utils import range_formatter
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, FloatCol, CheckCol, ProcessedCol, MultiProcessedCol, ColGroup, SpacerCol
from lmfdb.api import datapage
from lmfdb.siegel_modular_forms.web_newform import (
    WebNewform, convert_newformlabel_from_conrey, LABEL_RE,
    quad_field_knowl, cyc_display, field_display_gen)
from lmfdb.siegel_modular_forms import smf
from lmfdb.siegel_modular_forms.web_space import (
    aut_rep_type_sort_key, family_str_to_char, family_char_to_str,
    WebNewformSpace, WebGamma1Space, DimGrid, convert_spacelabel_from_conrey,
    get_bread, get_search_bread, get_dim_bread, newform_search_link,
    ALdim_table, NEWLABEL_RE as NEWSPACE_RE, OLDLABEL_RE as OLD_SPACE_LABEL_RE)
from lmfdb.siegel_modular_forms.download import SMF_download
from lmfdb.sato_tate_groups.main import st_display_knowl

INT_RE = re.compile("^[0-9]*$")
POSINT_RE = re.compile("^[1-9][0-9]*$")
ALPHA_RE = re.compile("^[a-z]+$")
ALPHACAP_RE = re.compile("^[A-Z]+$")

_curdir = os.path.dirname(os.path.abspath(__file__))

@cached_function
def learnmore_list():
    """
    Return the learnmore list
    """
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Siegel modular form labels', url_for(".labels_page"))]


def learnmore_list_remove(matchstring):
    """
    Return the learnmore list with the matchstring entry removed
    """
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

@cached_function
def degree_bound():
    return db.smf_newforms.max('degree')

@cached_function
def weight_bound(wt_len=2, nontriv=None):
    if nontriv:
        wts = db.smf_newforms.search({'char_order':{'$ne':1}}, 'weight')
    else:
        wts = db.smf_newforms.search({}, 'weight')
    return max([w for w in wts if len(w) == wt_len])

@cached_function
def level_bound(nontriv=None):
    if nontriv:
        return db.smf_newforms.max('level',{'char_order':{'$ne':1}})
    else:
        return db.smf_newforms.max('level')

#############################################################################
# The following functions are used for processing columns in search results #
#############################################################################

def ALdims_knowl(al_dims, level, weight):
    dim_dict = {}
    for vec, dim, cnt in al_dims:
        dim_dict[tuple(ev for (p, ev) in vec)] = dim
    short = "+".join(r'\(%s\)'%dim_dict.get(vec,0) for vec in cartesian_product_iterator([[1,-1] for _ in range(len(al_dims[0][0]))]))
    # We erase plus_dim and minus_dim if they're obvious
    AL_table = ALdim_table(al_dims, level, weight)
    return r'<a title="[ALdims]" knowl="dynamic_show" kwargs="%s">%s</a>'%(AL_table, short)

def nf_link(m, d, is_real_cyc, nf_label, poly, disc):
    # args: ["field_poly_root_of_unity", "dim", "field_poly_is_real_cyclotomic", "nf_label", "field_poly", "field_disc_factorization"]
    if m and d != 2:
        return cyc_display(m, d, is_real_cyc)
    else:
        return field_display_gen(nf_label, poly, disc, truncate=16)

def display_AL(info):
    results = info["results"]
    if not results:
        return False
    N = results[0]['level']
    if not all(mf['level'] == N for mf in results):
        return False
    if N == 1:
        return False
    return all(mf['char_order'] == 1 for mf in results)

def display_Fricke(info):
    return any(mf['char_order'] == 1 for mf in info["results"])

# For spaces
def display_decomp(level, weight, char_orbit_label, hecke_orbit_dims):
    # input: ['level', 'weight', 'char_orbit_label', 'hecke_orbit_dims']
    if hecke_orbit_dims is None: # shouldn't happen
        return 'unknown'
    dim_dict = defaultdict(int)
    terms = []
    for dim in hecke_orbit_dims:
        dim_dict[dim] += 1
    for dim in sorted(dim_dict.keys()):
        count = dim_dict[dim]
        query = {'weight':weight,
                 'char_label':'%s.%s'%(level,char_orbit_label),
                 'cusp_dim':dim}
        if count > 3:
            short = r'\({0}\)+\(\cdots\)+\({0}\)'.format(dim)
            title = '%s newforms' % count
        else:
            short = '+'.join([r'\(%s\)'%dim]*count)
            title=None
        if count == 1:
            query['jump'] = 'yes'
        link = newform_search_link(short, title=title, **query)
        terms.append(link)
    return r'+'.join(terms)

def show_ALdims_col(info):
    return any(space.get('AL_dims') for space in info["results"])

def display_ALdims(level, weight, al_dims):
    if al_dims:
        return ALdims_knowl(al_dims, level, weight)
    else:
        return ''

def set_info_funcs(info):
    info["mf_url"] = lambda mf: url_for_label(mf['label'])

    # temporary, to see that it works
    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series',
                          'Q' : 'Klingen-Eisenstein series (Q)',
                          'F' : 'Siegel-Eisenstein series (F)',
                          'Y' : 'Yoshida lifts (Y)',
                          'P' : 'Saito-Kurokawa lifts (P)',
                          'G' : 'General type (G)'
    }

    info["subspace_type"] = {'M' : {'M' : ''},
                             'E' : {'Q' : 'Klingen-Eisenstein series (Q)',
                                    'F' : 'Siegel-Eisenstein series (F)'},
                             'S' : {'Y' : 'Yoshida lifts (Y)',
                                    'P' : 'Saito-Kurokawa lifts (P)',
                                    'G' : 'General type (G)'}
                             }
    info["subspace_num"] = { typ : len(info["subspace_type"][typ]) for typ in ['M', 'E', 'S']}

    info['download_spaces'] = lambda results: any(space['dim'] > 1 for space in results)
    info['bigint_knowl'] = bigint_knowl

@smf.route("/")
def index():
    # print("routed to index")
    info = to_dict(request.args, search_array=SMFSearchArray())
    if len(request.args) > 0:
        # hidden_search_type for prev/next buttons
        info['search_type'] = search_type = info.get('search_type', info.get('hst', 'List'))

        if search_type in ['List', 'Random']:
            return newform_search(info)
        elif search_type in ['Spaces', 'RandomSpace']:
            return space_search(info)
        elif search_type == 'Dimensions':
            return dimension_form_search(info)
        elif search_type == 'SpaceDimensions':
            bad_keys = [key for key in newform_only_fields if key in info]
            if bad_keys:
                flash_error("%s invalid for searching spaces", ", ".join(bad_keys))
            return dimension_space_search(info)
        elif search_type == 'Traces':
            return trace_search(info)
        elif search_type == 'SpaceTraces':
            return space_trace_search(info)
        else:
            flash_error("Invalid search type; if you did not enter it in the URL please report")
    info["stats"] = SMF_stats()
    # info["degree_list"] = ('2', '3-%d' % degree_bound())
    # info["degree_list"] = ('2')
    info["degree"] = 2
    info["weight_list"] = ('2', '3', '4', '5-8', '9-16', '17-%d' % weight_bound()[0] )
    info["vector_weight_list"] = ('(3,2)', '(4,2)', '(5,2)-(8,2)', '(9,2)-(16,2)', '(17,2)-(%d,%d)' % (weight_bound(2)[0], weight_bound(2)[1]) )
    info["level_list"] = ('1', '2-10', '11-100', '101-%d' % level_bound() )
    return render_template("smf_browse.html",
                           info=info,
                           title="Siegel modular forms",
                           learnmore=learnmore_list(),
                           bread=get_bread())

@smf.route("/random/")
@redirect_no_cache
def random_form():
    # print("routed to random")
    label = db.smf_newforms.random()
    return url_for_label(label)

@smf.route("/random_space/")
@redirect_no_cache
def random_space():
    # print("routed to random_space")
    label = db.smf_newspaces.random()
    return url_for_label(label)

@smf.route("/interesting_newforms")
def interesting_newforms():
    # print("routed to interesting_newforms")
    return interesting_knowls(
        "mf.siegel",
        db.smf_newforms,
        url_for_label,
        regex=LABEL_RE,
        title="Some interesting newforms",
        bread=get_bread(other="Interesting newforms"),
        learnmore=learnmore_list()
    )

@smf.route("/interesting_spaces")
def interesting_spaces():
    # print("routed to interesting_spaces")
    return interesting_knowls(
        "smf",
        db.smf_newspaces,
        url_for_label,
        regex=NEWSPACE_RE,
        title="Some interesting newspaces",
        bread=get_bread(other="Interesting newspaces"),
        learnmore=learnmore_list()
    )

# Add routing for specifying an initial segment of level, weight, etc.
# Also url_for_...

def parse_n(info, newform, primes_only):
    p, maxp = 2, 10
    if primes_only:
        while p <= maxp:
            if newform.level % p == 0:
                maxp = next_prime(maxp)
            p = next_prime(p)
    errs = []
    info['default_nrange'] = '2-%s' % maxp
    nrange = info.get('n', '2-%s' % maxp)
    try:
        info['CC_n'] = integer_options(nrange, newform.an_cc_bound)
    except (ValueError, TypeError) as err:
        info['CC_n'] = list(range(2, maxp + 1))
        if err.args and err.args[0] == 'Too many options':
            errs.append(r"Only \(a_n\) up to %s are available" % (newform.an_cc_bound))
        else:
            errs.append("<span style='color:black'>n</span> must be an integer, range of integers or comma separated list of integers")
    if min(info['CC_n']) < 1:
        errs.append(r"We only show \(a_n\) with n at least 1")
        info['CC_n'] = [n for n in info['CC_n'] if n >= 1]
    if max(info['CC_n']) > newform.an_cc_bound:
        errs.append(r"Only \(a_n\) up to %s are available; limiting to \(n \le %d\)" % (newform.an_cc_bound, newform.an_cc_bound))
        info['CC_n'] = [n for n in info['CC_n'] if n <= newform.an_cc_bound]
    if primes_only:
        info['CC_n'] = [n for n in info['CC_n'] if ZZ(n).is_prime() and newform.level % n != 0]
        if len(info['CC_n']) == 0:
            errs.append("No good primes within n range; resetting to default")
            info['CC_n'] = [n for n in prime_range(maxp+1) if newform.level % n != 0]
    elif len(info['CC_n']) == 0:
        errs.append("No n in specified range; resetting to default")
        info['CC_n'] = list(range(2, maxp + 1))
    return errs

def parse_m(info, newform):
    errs = []
    maxm = min(newform.dim, 20)
    info['default_mrange'] = '1-%s'%maxm
    mrange = info.get('m', '1-%s'%maxm)
    if '.' in mrange:
        # replace embedding codes with the corresponding integers
        # If error, need to replace 'm' by default
        try:
            mrange = re.sub(r'\d+\.\d+', newform.embedding_from_embedding_label, mrange)
        except ValueError:
            errs.append("Invalid embedding label")
            mrange = info['m'] = '1-%s'%maxm
    try:
        info['CC_m'] = integer_options(mrange, 1000)
    except (ValueError, TypeError) as err:
        info['CC_m'] = list(range(1, maxm + 1))
        if err.args and err.args[0] == 'Too many options':
            errs.append('Web interface only supports 1000 embeddings at a time.  Use download link to get more (may take some time).')
        else:
            errs.append("<span style='color:black'>Embeddings</span> must consist of integers or embedding codes")
    if max(info['CC_m']) > newform.dim:
        errs.append("Only %s embeddings exist" % newform.dim)
        info['CC_m'] = [m for m in info['CC_m'] if m <= newform.dim]
    elif min(info['CC_m']) < 1:
        errs.append("Embeddings are labeled by positive integers")
        info['CC_m'] = [m for m in info['CC_m'] if m >= 1]
    return errs

def parse_prec(info):
    try:
        info['emb_prec'] = int(info.get('prec',6))
        if info['emb_prec'] < 1 or info['emb_prec'] > 15:
            raise ValueError
    except (ValueError, TypeError):
        info['emb_prec'] = 6
        return ["<span style='color:black'>Precision</span> must be a positive integer, at most 15 (for higher precision, use the download button)"]
    return []


def render_newform_webpage(label):
    # print("in render_newform_webpage")
    try:
        newform = WebNewform.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)

    # print("parsing request")
    info = to_dict(request.args)
    info['display_float'] = display_float
    info['format'] = info.get('format', 'embed')

    errs = parse_n(info, newform, info['format'] in ['satake', 'satake_angle'])
    errs.extend(parse_m(info, newform))
    errs.extend(parse_prec(info))
    newform.setup_cc_data(info)
    if errs:
        flash_error("%s", "<br>".join(errs))
    # print("rendering template")
    return render_template("smf_newform.html",
                           info=info,
                           newform=newform,
                           properties=newform.properties,
                           downloads=newform.downloads,
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.title,
                           friends=newform.friends,
                           KNOWL_ID="mf.siegel.%s" % label)

def render_embedded_newform_webpage(newform_label, embedding_label):
    try:
        label = newform_label + "." + embedding_label
        newform = WebNewform.by_label(newform_label,
                                      embedding_label=embedding_label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)
    info = to_dict(request.args)
    info['display_float'] = display_float
    # errs = parse_n(info, newform, info['format'] in ['primes', 'all'])
    try:
        m = int(newform.embedding_from_embedding_label(embedding_label))
    except ValueError as err:
        return abort(404, err.args)
    info['CC_m'] = [m]
    info['CC_n'] = [0, 1000]
    # errs.extend(parse_prec(info))
    errs = parse_prec(info)
    newform.setup_cc_data(info)
    if errs:
        flash_error("%s", "<br>".join(errs))
    return render_template("smf_embedded_newform.html",
                           info=info,
                           newform=newform,
                           properties=newform.properties,
                           downloads=newform.downloads,
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.embedded_title(m),
                           friends=newform.friends,
                           KNOWL_ID="mf.siegel.%s" % label)

def render_space_webpage(label):
    try:
        space = WebNewformSpace.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info = {'results':space.newforms, # so we can reuse search result code
            'columns':newform_columns}
    set_info_funcs(info)
    return render_template("smf_space.html",
                           info=info,
                           space=space,
                           properties=space.properties,
                           downloads=space.downloads,
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends,
                           KNOWL_ID="mf.siegel.%s" % label)

def render_full_gamma1_space_webpage(label):
    try:
        space = WebGamma1Space.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info={}
    set_info_funcs(info)
    return render_template("smf_full_gamma1_space.html",
                           info=info,
                           space=space,
                           properties=space.properties,
                           downloads=space.downloads,
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@smf.route("/data/<label>")
def mf_data(label):
    # print("routed to mf_data")
    slabel = label.split(".")
    if (len(slabel) >= 8) and (slabel[-4][0].isalpha()):
        emb_label = label
        form_label = ".".join(slabel[:-2])
        space_label = ".".join(slabel[:-3])
        ocode = db.smf_newforms.lookup(form_label, "hecke_orbit_code")
        if ocode is None:
            return abort(404, f"{label} not in database")
        tables = ["smf_newforms", "smf_hecke_cc", "smf_newspaces", "smf_hecke_charpolys", "smf_hecke_traces"]
        labels = [form_label, emb_label, space_label, ocode, ocode]
        label_cols = ["label", "label", "label", "hecke_orbit_code", "hecke_orbit_code"]
        title = f"Embedded newform data - {label}"
    elif (len(slabel) >= 6) and (slabel[-2][0].isalpha()):
        form_label = label
        space_label = ".".join(slabel[:-1])
        ocode = db.smf_newforms.lookup(form_label, "hecke_orbit_code")
        if ocode is None:
            return abort(404, f"{label} not in database")
        tables = ["smf_newforms", "smf_hecke_nf", "smf_newspaces", "smf_hecke_charpolys", "smf_hecke_traces"]
        labels = [form_label, form_label, space_label, ocode, ocode]
        label_cols = ["label", "label", "label", "hecke_orbit_code", "hecke_orbit_code"]
        title = f"Newform data - {label}"
    elif (len(slabel) >= 5) and (slabel[-2][0].isdigit()):
#        ocode = db.smf_newspaces.lookup(label, "hecke_orbit_code")
#        if ocode is None:
#            return abort(404, f"{label} not in database")
        ret_id = db.smf_newspaces.lookup(label, "id")
        if ret_id is None:
             return abort(404, f"{label} not in database")
        #tables = ["smf_newspaces", "smf_subspaces", "smf_hecke_newspace_traces"]
        #labels = [label, label, ocode]
        #label_cols = ["label", "label", "hecke_orbit_code"]
        tables = ["smf_newspaces"]
        labels = [label]
        label_cols = ["label"]
        title = f"Newspace data - {label}"
    elif (len(slabel) >= 4) and (slabel[-1][0].isdigit()):
        tables = ["smf_allchars", "smf_allchars_subspaces"]
        labels = label
        label_cols = None
        title = fr"Newspace data - {label}"
    else:
        return abort(404, f"Invalid label {label}")
    bread = get_bread(other=[(label, url_for_label(label)), ("Data", " ")])
    return datapage(labels, tables, title=title, bread=bread, label_cols=label_cols)

def check_valid_family(family):
    if not family_char_to_str(family):
        return (False, "Invalid family label - {family}")
    return (True, "")

def check_valid_weight(weight, degree):
    if weight.count('.') >= degree:
        return (False, "Invalid weight: vector length should be at most the degree")
    weight_vec = weight.split('.')
    if not all([w.isdigit() for w in weight_vec]):
        return (False, "Invalid weight: not integers")
    return (True, "")

@smf.route("/<int:degree>/")
def by_url_degree(degree):
    # print("routed to by_url_degree")
    if not POSINT_RE.match(str(degree)):
        try:
            return redirect(url_for_label(degree), code=301)
        except ValueError:
            flash_error("%s is not a valid Siegel newform or space label", degree)
            return redirect(url_for(".index"))
    info = to_dict(request.args, search_array=SMFSearchArray())
    if 'degree' in info:
        return redirect(url_for('.index', **request.args), code=307)
    else:
        info['degree'] = degree
    return newform_search(info)

@smf.route("/<int:degree>/<family>/")
def by_url_family_label(degree, family):
    # print("routed to by_url_family_label")
    valid_family = check_valid_family(family)
    if not valid_family[0]:
        return abort(404, valid_family[1])
    label = str(degree)+"."+str(family)
    # currently we do not have a family webpage
    # return render_family_webpage(label)
    info = to_dict(request.args, search_array=SMFSearchArray())
    return newform_search(info)

@smf.route("/<int:degree>/<family>/<int:level>/")
def by_url_level(degree, family, level):
    # print("routed to by_url_level")
    valid_family = check_valid_family(family)
    if not valid_family[0]:
        return abort(404, valid_family[1])
    info = to_dict(request.args, search_array=SMFSearchArray())
    if ('degree' in info) or ('family' in info) or ('level' in info):
        return redirect(url_for('.index', **request.args), code=307)
    else:
        info['degree'] = degree
        info['family'] = family
        info['level'] = level
    return newform_search(info)

@smf.route("/<int:degree>/<family>/<int:level>/<weight>/")
def by_url_full_space_label(degree, family, level, weight):
    # print("routed to by_url_full_space_label")
    valid_family = check_valid_family(family)
    if not valid_family[0]:
        return abort(404, valid_family[1])
    valid_weight = check_valid_weight(weight, degree)
    if not valid_weight[0]:
        return abort(404, valid_weight[1])
    label = ".".join([str(w) for w in [degree, family, level, weight]])
    # At the moment we do not have full space webpages
    # return render_full_space_webpage(label)
    info = to_dict(request.args, search_array=SMFSearchArray())
    return newform_search(info)

@smf.route("/<int:degree>/<family>/<int:level>/<weight>/<char_orbit_label>/")
def by_url_space_label(degree, family, level, weight, char_orbit_label):
    # raise ValueError("routed to by_url_space_label")
    valid_weight = check_valid_weight(weight, degree)
    if not valid_weight[0]:
        return abort(404, valid_weight[1])
    label = ".".join([str(w) for w in [degree, family, level, weight, char_orbit_label]])
    return render_space_webpage(label)

@smf.route("/<int:degree>/<family>/<int:level>/<weight>/<char_orbit_label>/<hecke_orbit>/")
def by_url_newform_label(degree, family, level, weight, char_orbit_label, hecke_orbit):
    # print("routed to by_url_newform_label")
    valid_weight = check_valid_weight(weight, degree)
    if not valid_weight[0]:
        return abort(404, valid_weight[1])
    label = ".".join(map(str, [degree, family, level, weight, char_orbit_label, hecke_orbit]))
    return render_newform_webpage(label)

# Utility redirect for bread and links from embedding table
@smf.route("/<int:degree>/<family>/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<embedding_label>/")
def by_url_newform_conrey5(degree, family, level, weight, char_orbit_label, hecke_orbit, embedding_label):
    # print("routed to by_url_newform_conrey5")
    if embedding_label.count('.') != 1:
        return abort(404, "Invalid embedding label: periods")
    conrey_index, embedding = embedding_label.split('.')
    if not (conrey_index.isdigit() and embedding.isdigit()):
        return abort(404, "Invalid embedding label: not integers")
    return redirect(url_for("smf.by_url_embedded_newform_label", level=level, weight=weight, char_orbit_label=char_orbit_label, hecke_orbit=hecke_orbit, conrey_index=conrey_index, embedding=embedding), code=301)

# Embedded modular form
@smf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<int:conrey_index>/<int:embedding>/")
def by_url_embedded_newform_label(level, weight, char_orbit_label, hecke_orbit, conrey_index, embedding):
    # print("routed to by_url_embedded_newform_label")
    if conrey_index <= 0 or embedding <= 0:
        return abort(404, "Invalid embedding label: negative values")
    newform_label = ".".join(map(str, [level, weight, char_orbit_label, hecke_orbit]))
    embedding_label = ".".join(map(str, [conrey_index, embedding]))
    return render_embedded_newform_webpage(newform_label, embedding_label)

def url_for_label(label):
    if label == "random":
        return url_for("smf.random_form")
    if not label:
        return abort(404, "Invalid label")

    slabel = label.split(".")
    if (len(slabel) >= 8) and (slabel[-4].isalpha()):
        func = "smf.by_url_embedded_newform_label"
    elif (len(slabel) >= 6) and (slabel[-2].isalpha()):
        func = "smf.by_url_newform_label"
    elif (len(slabel) >= 5) and (slabel[-1].isalpha()):
        func = "smf.by_url_space_label"
    elif (len(slabel) >= 4) and (slabel[-1].isdigit()):
        func = "smf.by_url_full_space_label"
    elif len(slabel) == 3:
        func = "smf.by_url_level"
    elif len(slabel) == 2:
        func = "smf.by_url_family"
    elif len(slabel) == 1:
        func = "smf.by_url_degree"
    else:
        return abort(404, "Invalid label")
    keys = ['degree', 'family', 'level', 'weight', 'char_orbit_label', 'hecke_orbit', 'conrey_index', 'embedding']
    if not POSINT_RE.match(slabel[0]):
        raise ValueError("Invalid label")
    keytypes_start = [POSINT_RE, ALPHACAP_RE, POSINT_RE]
    keytypes_end = [ALPHA_RE, ALPHA_RE, POSINT_RE, POSINT_RE]
    if len(keytypes_start)+len(keytypes_end)+int(slabel[0]) < len(slabel):
        raise ValueError("Invalid label")
    for i in range (len(keytypes_start)):
        if not keytypes_start[i].match(slabel[i]):
            raise ValueError("Invalid label")
    idx = len(keytypes_start)
    while ((idx < len(slabel)) and INT_RE.match(slabel[idx])):
        idx += 1
    for i in range (len(slabel)-idx):
        if not keytypes_end[i].match(slabel[i+idx]):
            raise ValueError("Invalid label")
    slabel = slabel[:len(keytypes_start)] + ['.'.join(slabel[len(keytypes_start):idx])] + slabel[idx:]
    kwds = {keys[i]: val for i, val in enumerate(slabel)}
    return url_for(func, **kwds)

def jump_box(info):
    jump = info.pop("jump").strip()
    errmsg = None
    if OLD_SPACE_LABEL_RE.match(jump):
        jump = convert_spacelabel_from_conrey(jump)
    #handle direct trace_hash search
    if re.match(r'^\#\d+$', jump) and ZZ(jump[1:]) < 2**61:
        label = db.smf_newforms.lucky({'trace_hash': ZZ(jump[1:].strip())}, projection="label")
        if label:
            return redirect(url_for_label(label), 301)
        else:
            errmsg = "hash %s not found"
    elif jump == 'yes':
        query = {}
        newform_parse(info, query)
        jump = db.smf_newforms.lucky(query, 'label', sort = None)
        if jump is None:
            errmsg = "There are no newforms specified by the query %s"
            jump = query
    if errmsg is None:
        # Add feature for Drew
        if ':' in jump:
            jump = jump.split(':')
            if len(jump) > 2 and jump[2].isdigit():
                jump[2] = str(cremona_letter_code(int(jump[2])-1))
            if len(jump) > 3 and jump[3].isdigit():
                jump[3] = str(cremona_letter_code(int(jump[3])-1))
            jump = '.'.join(jump)
        try:
            return redirect(url_for_label(jump), 301)
        except ValueError:
            errmsg = "%s is not a valid newform or space label"
    flash_error(errmsg, jump)
    return redirect(url_for(".index"))

#@smf_page.route('/Sp4Z_j/<int:k>/<int:j>')
#@smf_page.route('/Sp4Z_j/<int:k>/<int:j>/')
#def Sp4Z_j_space(k,j):
#    bread = [("Modular forms", url_for('modular_forms')),
#             ('Siegel', url_for('.index')),
#             (r'$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z})$', url_for('.Sp4Z_j')),
#             (r'$M_{%s,%s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k,j), '')]
#    if j%2:
#        # redirect to general page for Sp4Z_j which will display an error message
#        return redirect(url_for(".Sp4Z_j",k=str(k),j=str(j)))
#    info = { 'args':{'k':str(k),'j':str(j)} }
#    try:
#        if j in [0,2]:
#            headers, table = dimensions._dimension_Sp4Z([k])
#            info['samples'] = find_samples('Sp4Z' if j==0 else 'Sp4Z_2', k)
#        else:
#            headers, table = dimensions._dimension_Gamma_2([k], j, group='Sp4(Z)')
#        info['headers'] = headers
#        info['subspace'] = table[k]
#    except NotImplementedError:
#        # redirect to general page for Sp4Z_j which will display an error message
#        return redirect(url_for(".Sp4Z_j",k=str(k),j=str(j)))
#    return render_template('ModularForm_GSp4_Q_full_level_space.html',
#                           title=r'$M_{%s, %s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k, j),
#                           bread=bread,
#                           info=info)

@smf.route("/download_qexp/<label>")
def download_qexp(label):
    # print("routed to download_qexp")
    return SMF_download().download_qexp(label, lang='sage')

@smf.route("/download_traces/<label>")
def download_traces(label):
    # print("routed to download_traces")
    return SMF_download().download_traces(label)

@smf.route("/download_newform_to_magma/<label>")
def download_newform_to_magma(label):
    # print("routed to download_newform_to_magma")
    return SMF_download().download_newform_to_magma(label)

@smf.route("/download_newform/<label>")
def download_newform(label):
    # print("routed to download_newform")
    return SMF_download().download_newform(label)

@smf.route("/download_embedded_newform/<label>")
def download_embedded_newform(label):
    # print("routed to download_embedded_newform")
    return SMF_download().download_embedding(label)


@smf.route("/download_newspace/<label>")
def download_newspace(label):
    # print("routed to download_newspace")
    return SMF_download().download_newspace(label)

# @smf_page.route('/Sp4Z_j')
# @smf_page.route('/Sp4Z_j/')
# def Sp4Z_j():
#    bread = [("Modular forms", url_for('modular_forms')),
#             ('Siegel', url_for('.index')),
#             (r'$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$', '')]
#    info={'args': request.args}
#    try:
#        dim_args = dimensions.parse_dim_args(request.args, {'k':'10-20','j':'0-30'})
#    except ValueError:
#        # error message is flashed in parse_dim_args
#        info['error'] = True
#    if not info.get('error'):
#        info['dim_args'] = dim_args
#        try:
#            info['table'] = dimensions.dimension_table_Sp4Z_j(dim_args['k_range'], dim_args['j_range'])
#        except NotImplementedError as err:
#            flash_error(err)
#            info['error'] = True
#    return render_template('ModularForm_GSp4_Q_Sp4Zj.html',
#                           title=r'$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$',
#                           bread=bread,
#                           info=info
#                           )

@smf.route("/download_full_space/<label>")
def download_full_space(label):
    # print("routed to download_full_space")
    return SMF_download().download_full_space(label)

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_character(inp, query, qfield, prim=False):
    # qfield will be set to something by the logic in SearchParser.__call__, but we want it determined by prim
    if prim:
        qfield = 'prim_orbit_index'
        level_field = 'char_conductor'
    else:
        qfield = 'char_orbit_index'
        level_field = 'level'
    pair = inp.split('.')
    if len(pair) != 2:
        raise ValueError("It must be of the form N.i")
    level, orbit = pair
    level = int(level)

    def contains_level(D):
        if D == level:
            return True
        if isinstance(D, dict):
            a = D.get('$gte')
            b = D.get('$lte')
            return (a is None or level >= a) and (b is None or level <= b)
    # Check that the provided constraint on level is consistent with the one
    # given by the character, and update level/$or
    if '$or' in query and all(level_field in D for D in query['$or']):
        if not any(contains_level(D) for D in query['$or']):
            raise ValueError("Inconsistent level")
        del query['$or']
    elif level_field in query:
        if not contains_level(query[level_field]):
            raise ValueError("Inconsistent level")
    query[level_field] = level
    if orbit.isalpha():
        orbit = class_to_int(orbit) + 1 # we don't store the prim_orbit_label
        if prim:
            if level > 10000:
                raise ValueError("The level is too large.")
            # Check that this character is actually primitive
            conductor = db.char_dir_orbits.lucky({'modulus':level, 'orbit_index': orbit}, 'conductor')
            if conductor is None:
                raise ValueError("No character orbit with this label exists.")
            if conductor != level:
                raise ValueError("It has level %d and is thus not primitive." % conductor)
        query[qfield] = orbit
    else:
        if prim:
            raise ValueError("You must use the orbit label when searching by primitive character")
        query['conrey_indexes'] = {'$contains': int(orbit)}

newform_only_fields = {
    'nf_label': 'Coefficient field',
    'cm': 'Self-twists',
    'rm': 'Self-twists',
    'cm_discs': 'CM discriminant',
    'rm_discs': 'RM discriminant',
    'inner_twist_count': 'Inner twist count',
    'analytic_rank': 'Analytic rank',
    'is_self_dual': 'Is self dual',
}

def parse_weight(info, query, qfield='weight', fname="Weight", braces="{}"):
    if qfield in info:
        if info[qfield][0] in ['(', '[']:
            if '-' in info[qfield]:
                wts = [braces[0] + w[1:-1] + braces[1] for w in info[qfield].split('-')]
                query[qfield] = { '$gte' : wts[0], '$lte' : wts[1] }
            else:
                query[qfield] = str(list(eval(info[qfield]))).replace('[',braces[0]).replace(']',braces[1])
        else:
            parse_ints(info, query, qfield, name=fname)
            if type(query[qfield]) == int:
                query[qfield] = (braces[:1] + ' %d, 0 ' + braces[1:]) % query[qfield]
            else:
                query[qfield] = { key : (braces[:1] + ' %d, 0 ' + braces[1:]) % query[qfield][key] for key in query[qfield].keys()}
    return 

def common_parse(info, query, na_check=False):
    parse_ints(info, query, 'degree', name="Degree")
    if 'degree' in info:
        info['degree'] = int(info['degree'])
    parse_ints(info, query, 'level', name="Level")
    parse_character(info, query, 'char_label', name='Character orbit', prim=False)
    parse_character(info, query, 'prim_label', name='Primitive character', prim=True)
    # parse_ints(info, query, 'weight', name="Weight")
    parse_weight(info, query, 'weight', fname="Weight")
    if 'family' in info:
        query['family'] = info['family']
        if (type(query['family']) == str) and (len(query['family']) > 1):
            query['family'] = family_str_to_char(info['family'])
    if 'weight_parity' in info:
        parity=info['weight_parity']
        if parity == 'even':
            query['weight_parity'] = 1
        elif parity == 'odd':
            query['weight_parity'] = -1
    if 'char_parity' in info:
        parity=info['char_parity']
        if parity == 'even':
            query['char_parity'] = 1
        elif parity == 'odd':
            query['char_parity'] = -1
    if info.get('level_type'):
        if info['level_type'] == 'divides':
            if not isinstance(query.get('level'), int):
                raise ValueError("You must specify a single level")
            else:
                query['level'] = {'$in': integer_divisors(ZZ(query['level']))}
        else:
            query['level_is_' + info['level_type']] = True
    parse_floats(info, query, 'analytic_conductor', name="Analytic conductor")
    parse_ints(info, query, 'Nk2', name=r"\(Nk^2\)")
    parse_ints(info, query, 'char_order', name="Character order")
    parse_primes(info, query, 'level_primes', name='Primes dividing level', mode=info.get('prime_quantifier'), radical='level_radical')

def parse_discriminant(d, sign = 0):
    d = int(d)
    if d*sign < 0:
        raise ValueError('%d %s 0' % (d, '<' if sign > 0 else '>'))
    if (d % 4) not in [0, 1]:
        raise ValueError('%d != 0 or 1 mod 4' % d)
    return d

def newform_parse(info, query):
    common_parse(info, query)
    parse_nf_string(info, query,'nf_label', name="Coefficient field")
    parse_bool(info, query, 'cm', qfield='is_cm', name='Self-twists')
    parse_bool(info, query, 'rm', qfield='is_rm', name='Self-twists')
    parse_subset(info, query, 'self_twist_discs', name="CM/RM discriminant", parse_singleton=parse_discriminant)
    parse_bool(info, query, 'is_twist_minimal')
    parse_ints(info, query, 'inner_twist_count')
    parse_ints(info, query, 'analytic_rank')
    parse_noop(info, query, 'atkin_lehner_string')
    parse_ints(info, query, 'fricke_eigenval')
    parse_bool(info, query, 'is_self_dual')
    parse_ints(info, query, 'hecke_ring_index')
    parse_ints(info, query, 'hecke_ring_generator_nbound')
    parse_noop(info, query, 'projective_image', func=str.upper)
    parse_noop(info, query, 'projective_image_type')
    parse_noop(info, query, 'aut_rep_type')
    parse_ints(info, query, 'artin_degree', name="Artin degree")
    if info.get('search_type') != 'SpaceDimensions':
        if info.get('dim_type') == 'rel':
            parse_ints(info, query, 'dim', qfield='relative_dim', name="Dimension")
        else:
            parse_ints(info, query, 'dim', name="Dimension")
    
def newspace_parse(info, query):
    for key, display in newform_only_fields.items():
        if key in info:
            msg = "%s not valid when searching for spaces"
            flash_error(msg, display)
            raise ValueError(msg  % display)
    if 'cusp_dim' not in info and 'hst' not in info:
        # When coming from browse page, add dim condition to only show non-empty spaces
        info['cusp_dim'] = '1-'
    if info.get('all_spaces') == 'yes' and 'num_forms' in query:
        msg = "Cannot specify number of newforms while requesting all spaces"
        flash_error(msg)
        raise ValueError(msg)
    common_parse(info, query)
    if info.get('search_type') != 'SpaceDimensions':
        if info.get('dim_type') == 'rel':
            parse_ints(info, query, 'cusp_dim', qfield='relative_dim', name="Cusp Dimension")
        else:
            parse_ints(info, query, 'cusp_dim', name="Cusp Dimension")
    if info['search_type'] != 'SpaceDimensions':
        parse_ints(info, query, 'num_forms', name='Number of newforms')
        if 'num_forms' not in query and info.get('all_spaces') != 'yes':
            # Don't show spaces that only include dimension data but no newforms (Nk2 > 4000, nontrivial character)
            query['num_forms'] = {'$exists':True}

def _trace_col(i):
    return ProcessedCol("traces", None, rf"$a_{{{nth_prime(i+1)}}}$", lambda tdisp:\
 "" if ((tdisp == '') or (tdisp[i] is None)) else bigint_knowl(tdisp[i], 12), orig="trace_lambda_p", align="right", default=True)
#    return ProcessedCol("traces", None, rf"$a_{{{nth_prime(i+1)}}}$", lambda tdisp: bigint_knowl(tdisp[i], 12), orig="trace_display", align="right", default=True)

def _AL_col(i, p):
    return ProcessedCol("atkin_lehner", None, str(p), lambda evs: "+" if evs[i][1] == 1 else "-", orig="atkin_lehner_eigenvals", align="center", mathmode=True, default=True)

newform_columns = SearchColumns([
    LinkCol("label", "mf.siegel.label", "Label", url_for_label, default=True),
    MathCol("level", "mf.siegel.level", "Level"),
    MathCol("degree", "mf.siegel.degree", "Degree"),
    # ProcessedCol("weight", "mf.siegel.weight", "Weight", lambda wt : '$(wt[0], wt[1])$' if wt[1] != 0 else wt[0],align="center"),
    ProcessedCol("weight", "mf.siegel.weight", "Weight", lambda wt : (wt[0], wt[1]),align="center"),
    # MathCol("weight", "mf.siegel.weight_k_j", "Weight"),
    MultiProcessedCol("character", "smf.character", "Char",
                      ["level", "char_orbit_label"],
                      lambda level, orb: display_knowl('character.dirichlet.orbit_data', title=f"{level}.{orb}", kwargs={"label":f"{level}.{orb}"}),
                      short_title="character"),
    MultiProcessedCol("prim", "character.dirichlet.primitive", "Prim",
                      ["char_conductor", "prim_orbit_index"],
                      lambda cond, ind: display_knowl('character.dirichlet.orbit_data', title=f"{cond}.{num2letters(ind)}", kwargs={"label":f"{cond}.{num2letters(ind)}"}),
                      short_title="primitive character"),
    MathCol("char_order", "character.dirichlet.order", "Char order", short_title="character order"),
    MathCol("dim", "mf.siegel.dimension", "Dim", default=True, align="right", short_title="dimension"),
    MathCol("relative_dim", "mf.siegel.relative_dimension", "Rel. Dim", align="right", short_title="relative dimension"),
#    FloatCol("analytic_conductor", "smf.analytic_conductor", r"$A$", default=True, align="center", short_title="analytic conductor"),
    MultiProcessedCol("field", "mf.siegel.coefficient_field", "Field", ["field_poly_root_of_unity", "dim", "field_poly_is_real_cyclotomic", "nf_label", "field_poly", "field_disc_factorization"], nf_link, default=True),
#    ProcessedCol("projective_image", "smf.projective_image", "Image",
#                 lambda img: ('' if img=='?' else '$%s_{%s}$' % (img[:1], img[1:])),
#                 contingent=lambda info: any(mf.get('weight') == 1 for mf in info["results"]),
#                 default=lambda info: all(mf.get('weight') == 1 for mf in info["results"]),
#                 align="center", short_title="projective image"),
#    MultiProcessedCol("cm", "smf.self_twist", "CM",
#                      ["is_cm", "cm_discs"],
#                      lambda is_cm, cm_discs: ", ".join(map(quad_field_knowl, cm_discs)) if is_cm else "None",
#                      short_title="CM",
#                      default=True),
#    MultiProcessedCol("rm", "smf.self_twist", "RM",
#                      ["is_rm", "rm_discs"],
#                      lambda is_rm, rm_discs: ", ".join(map(quad_field_knowl, rm_discs)) if is_rm else "None",
#                      contingent=lambda info: any(mf.get('weight') == 1 for mf in info["results"]),
#                      short_title="RM",
#                      default=True),
#    CheckCol("is_self_dual", "smf.selfdual", "Self-dual"),
#    MathCol("inner_twist_count", "smf.inner_twist_count", "Inner twists"),
#    MathCol("analytic_rank", "smf.analytic_rank", "Rank*"),
    ColGroup("traces", "mf.siegel.trace_form", "Traces",
             [_trace_col(i) for i in range(6)],
             default=True),
    SpacerCol("atkin_lehner", contingent=display_AL, default=True),
    ColGroup("atkin_lehner", "mf.siegel.atkin-lehner", "A-L signs",
             lambda info: [_AL_col(i, pair[0]) for i, pair in enumerate(info["results"][0]["atkin_lehner_eigenvals"])] if "atkin_lehner_eigenvals" in info["results"][0] else "",
             contingent=display_AL, default=True, orig=["atkin_lehner_eigenvals"]),
    ProcessedCol("fricke_eigenval", "mf.siegel.fricke", "Fricke sign",
                 lambda ev: "$+$" if ev == 1 else ("$-$" if ev else ""),
                 contingent=display_Fricke, default=lambda info: not display_AL(info), align="center"),
    ProcessedCol("hecke_ring_index_factorization", "mf.siegel.coefficient_ring", "Coefficient ring index",
                 lambda fac: "" if fac=="" else factor_base_factorization_latex(fac), mathmode=True, align="center"),
#    ProcessedCol("sato_tate_group", "smf.sato_tate", "Sato-Tate", st_display_knowl, short_title="Sato-Tate group"),
      ProcessedCol("aut_rep_type", "mf.siegel.automorphic_type", "Aut. Type", lambda x : r'\(\mathbf{(' + x + r')}\)' , align="center", default=True),
    ProcessedCol("aut_rep_type", "mf.siegel.automorphic_type", "Cusp", lambda x : "&#x2713;" if (x not in ['F', 'Q']) else "", align="center", default=True),
    MultiProcessedCol("qexp", "mf.siegel.q-expansion", "$q$-expansion", ["label", "qexp_display"],
                     lambda label, disp: fr'<a href="{url_for_label(label)}">\({disp}\)</a>' if disp else "",
                      default=True)
],
#    ['analytic_conductor', 'analytic_rank', 'atkin_lehner_eigenvals', 'char_conductor', 'char_orbit_label', 'char_order', 'cm_discs', 'dim', 'relative_dim', 'field_disc_factorization', 'field_poly', 'field_poly_is_real_cyclotomic', 'field_poly_root_of_unity', 'fricke_eigenval', 'hecke_ring_index_factorization', 'inner_twist_count', 'is_cm', 'is_rm', 'is_self_dual', 'label', 'level', 'nf_label', 'prim_orbit_index', 'projective_image', 'qexp_display', 'rm_discs', 'sato_tate_group', 'trace_display', 'weight'],
    ['degree', 'weight', 'family', 'field_disc', 'field_poly', 'label', 'qexp_display', 'char_orbit_label', 'char_order', 'char_conductor', 'dim', 'relative_dim', 'field_disc_factorization', 'nf_label', 'level', 'prim_orbit_index', 'field_poly_is_real_cyclotomic', 'field_poly_root_of_unity', 'trace_lambda_p', 'hecke_ring_index_factorization', 'aut_rep_type', 'atkin_lehner_eigenvals', 'fricke_eigenval'],
    tr_class=["middle bottomlined", ""])

@search_wrap(table=db.smf_newforms,
             title='Siegel newform search results',
             err_title='Siegel newform Search Input Error',
             columns=newform_columns,
             shortcuts={'jump':jump_box,
                        'download':SMF_download(),
                        #'download_exact':download_exact,
                        #'download_complex':download_complex
             },
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list)

def newform_search(info, query):
    query['__sort__'] = ['weight', 'level', 'aut_rep_type', 'dim']
    newform_parse(info, query)
    set_info_funcs(info)

def trace_postprocess(res, info, query, spaces=False):
    if res:
        if info.get('view_modp') == 'reductions':
            q = int(info['an_modulo'])
        else:
            q = None
        hecke_codes = [mf['hecke_orbit_code'] for mf in res]
        trace_dict = defaultdict(dict)
        table = db.smf_hecke_newspace_traces if spaces else db.smf_hecke_traces
        for rec in table.search({'n':{'$in': info['Tr_n']}, 'hecke_orbit_code':{'$in':hecke_codes}}, projection=['hecke_orbit_code', 'n', 'trace_an'], sort=[]):
            if q:
                trace_dict[rec['hecke_orbit_code']][rec['n']] = (rec['trace_an'] % q)
            else:
                trace_dict[rec['hecke_orbit_code']][rec['n']] = rec['trace_an']
        for mf in res:
            mf['tr_an'] = trace_dict[mf['hecke_orbit_code']]
    return res
def space_trace_postprocess(res, info, query):
    return trace_postprocess(res, info, query, True)
def process_an_constraints(info, query, qfield='traces', nshift=None):
    q = info.get('an_modulo','').strip()
    if q:
        try:
            q = int(q)
            if q <= 0:
                raise ValueError
        except (ValueError, TypeError):
            msg = "Modulo must be a positive integer"
            flash_error(msg)
            raise ValueError(msg)
        parse_equality_constraints(info, query, 'an_constraints', qfield=qfield,
                                   parse_singleton=(lambda x: {'$mod':[int(x),q]}),
                                   nshift=nshift)
    else:
        parse_equality_constraints(info, query, 'an_constraints', qfield=qfield)
        if info.get('view_modp') == 'reductions':
            msg = "Must set Modulo input in order to view reductions"
            flash_error(msg)
            raise ValueError(msg)
def set_Trn(info, query, limit=1000):
    ns = info.get('n', '1-40')
    n_primality = info['n_primality'] = info.get('n_primality', 'primes')
    Trn = integer_options(ns, 1000)
    if n_primality == 'primes':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime()]
    elif n_primality == 'prime_powers':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime_power()]
    else:
        Trn = [n for n in Trn if n > 1]
    if any(n > limit for n in Trn):
        msg = "Cannot display traces above 1000; more may be available by downloading individual forms"
        flash_error(msg)
        raise ValueError(msg)
    info['Tr_n'] = Trn
    info['download_limit'] = limit

@search_wrap(template="smf_trace_search_results.html",
             table=db.smf_newforms,
             title='Newform search results',
             err_title='Newform search input error',
             shortcuts={'jump':jump_box,
                        'download':SMF_download().download_multiple_traces},
             projection=['label', 'dim', 'hecke_orbit_code', 'weight'],
             postprocess=trace_postprocess,
             bread=get_search_bread,
             learnmore=learnmore_list)
def trace_search(info, query):
    set_Trn(info, query)
    newform_parse(info, query)
    process_an_constraints(info, query)
    set_info_funcs(info)

@search_wrap(template="smf_space_trace_search_results.html",
             table=db.smf_newspaces,
             title='Newspace search results',
             err_title='Newspace search input error',
             shortcuts={'jump':jump_box,
                        'download':SMF_download().download_multiple_space_traces},
             projection=['label', 'cusp_dim', 'weight'],
             postprocess=space_trace_postprocess,
             bread=get_search_bread,
             learnmore=learnmore_list)
def space_trace_search(info, query):
    set_Trn(info, query)
    newspace_parse(info, query)
    process_an_constraints(info, query)
    set_info_funcs(info)

def set_rows_cols(info, query):
    """
    Sets weight_list and level_list, which are the row and column headers
    """
    info['degree'] = int(info['degree'])
    try:
        info['weight_list'] = integer_options(info['weight'], max_opts=200)
        wt_list = []
        for wt in info['weight_list']:
            subinfo = {'weight' : str(wt)}
            query = {}
            parse_weight(subinfo, query, 'weight',braces="()")
            wt_list.append(eval(query['weight']))
        info['weight_list'] = wt_list
    except ValueError:
        raise ValueError("Table too large: at most 200 options for weight")
    if 'weight_parity' in query:
        if query['weight_parity'] == -1:
            info['weight_list'] = [(k,j) for (k,j) in info['weight_list'] if j%2 == 1]
        else:
            info['weight_list'] = [(k,j) for (k,j) in info['weight_list'] if j%2 == 0]
    if 'char_orbit_index' in query:
        # Character was set, consistent with level
        info['level_list'] = [query['level']]
    else:
        try:
            info['level_list'] = integer_options(info['level'], max_opts=100000)
        except ValueError:
            raise ValueError("Table too large: at most 1000 options for level")
        if not info['level_list']:
            raise ValueError("Must include at least one level")
    if 'char_conductor' in query:
        info['level_list'] = [N for N in info['level_list'] if (N % query['char_conductor']) == 0]
    if info.get('prime_quantifier') == 'exactly':
        rad = query.get('level_radical')
        if rad:
            info['level_list'] = [N for N in info['level_list'] if ZZ(N).radical() == rad]
    else:
        primes = info.get('level_primes','').strip()
        if primes:
            try:
                rad = prod(ZZ(p) for p in primes.split(','))
                if info.get('prime_quantifier') in ['subset', 'subsets']: # subsets for backward compat in urls
                    info['level_list'] = [N for N in info['level_list'] if (rad % ZZ(N).radical()) == 0]
                elif info.get('prime_quantifier') in ['supset', 'append']: # append for backward compat in urls
                    info['level_list'] = [N for N in info['level_list'] if (N % rad) == 0]
                elif info.get('prime_quantifier') in ['complement']:
                    info['level_list'] = [N for N in info['level_list'] if gcd(N,rad) == 1]
                elif info.get('prime_quantifier') in ['exact']:
                    info['level_list'] = [N for N in info['level_list'] if (rad == ZZ(N).radical())]
            except (ValueError, TypeError):
                pass
    if not info['level_list']:
        raise ValueError("No valid levels consistent with specified characters and bad primes")
    if len(info['level_list']) > 1000:
        raise ValueError("Table too large: at most 1000 options for level")
    if len(info['weight_list']) * len(info['level_list']) > 10000:
        raise ValueError("Table too large: must have at most 10000 entries")
na_msg_nontriv = '"n/a" means that not all modular forms of this weight and level are available, but those of trivial character may be; set character order to 1 to restrict to newforms of trivial character.'
na_msg_triv = '"n/a" means that no modular forms of this weight and level are available.'

def dimension_common_postprocess(info, query, cusp_types, newness_types, url_generator, pick_table, switch_text=None):
    set_rows_cols(info, query)
    set_info_funcs(info)
    info['level_width'] = min(2 + len(info['level_list']), 5)
    info['level_extra'] = 2 + len(info['level_list']) - info['level_width']
    info['pick_table'] = pick_table
    info['cusp_types'] = cusp_types
    info['newness_types'] = newness_types
    info['url_generator'] = url_generator
    if switch_text:
        info['switch_text'] = switch_text
    info['count'] = 50 # put count back in so that it doesn't show up as none in url
    if len(info['family']) > 1:
        info['family'] = family_str_to_char(info['family'])
    info['family'] = ord(info['family'])
    info['degree'] = int(info['degree'])

def delete_false(D):
    for key, val in list(D.items()): # for py3 compat: can't iterate over items while deleting
        if val is False:
            del D[key]

def dimension_space_postprocess(res, info, query):
    if ((query.get('weight_parity') == -1 and query.get('char_parity') == 1)
            or
        (query.get('weight_parity') == 1 and query.get('char_parity') == -1)):
        raise ValueError("Inconsistent parity for character and weight")
    urlgen_info = dict(info)
    #print(urlgen_info)
    urlgen_info['count'] = 50
    # Remove entries that are unused for dimension tables
    urlgen_info.pop('hidden_search_type', None)
    urlgen_info.pop('number', None)
#    urlgen_info.pop('numforms', None)
    urlgen_info.pop('cusp_dim', None)
    urlgen_info.pop('search_array', None)

    def url_generator_list(g, F, N, k):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'Spaces'
        info_copy['degree'] = str(g)
        info_copy['family'] = chr(F)
        info_copy['level'] = str(N)
        info_copy['weight'] = '.'.join([str(kk) for kk in k])
        return url_for(".index", **info_copy)
    if 'char_orbit_index' in query or 'prim_orbit_index' in query:
        url_generator = url_generator_list
    elif query.get('char_order') == 1:
        def url_generator(g, F, N, k):
            return url_for(".by_url_space_label", degree=g, family=chr(F), level=N,
                           weight= '.'.join([str(kk) for kk in k]), char_orbit_label="a")
    elif 'char_order' in query:
        url_generator = url_generator_list
    else:
        def url_generator(g, F, N, k):
            return url_for(".by_url_full_gammma1_space_label", degree=g, family=chr(F), level=N,
                           weight= '.'.join([str(kk) for kk in k]))

    def pick_table(entry, X, typ):
        return entry[X][typ]

    def switch_text(X, typ):
        space_type = {'M': ' modular forms',
                      'S': ' cusp forms',
                      'E': ' Eisenstein series',
                      'Q' : 'Klingen-Eisenstein series (Q)',
                      'F' : 'Siegel-Eisenstein series (F)',
                      'Y' : 'Yoshida lifts (Y)',
                      'P' : 'Saito-Kurokawa lifts (P)',
                      'G' : 'General type (G)'
        }
        return typ.capitalize() + space_type[X]

    dimension_common_postprocess(info, query, ['M', 'S', 'E'], ['all', 'new', 'old'],
                                 url_generator, pick_table, switch_text)
    dim_dict = {}
    for space in res:
        g = int(space['degree'])
        F = ord(space['family'])
        N = space['level']
        k = tuple(space['weight'])
        dims = DimGrid.from_db(space)
       # if space.get('num_forms') is None:
        #    dim_dict[g,F,N,k] = False
        if (g,F,N,k) not in dim_dict:
            dim_dict[g,F,N,k] = dims
        elif dim_dict[g,F,N,k] is not False:
            dim_dict[g,F,N,k] += dims
    delete_false(dim_dict)
    return dim_dict

def dimension_form_postprocess(res, info, query):
    urlgen_info = dict(info)
    urlgen_info['count'] = 50
    # Remove entries that are unused for dimension tables
    urlgen_info.pop('hidden_search_type', None)
    urlgen_info.pop('number', None)
    urlgen_info.pop('search_array', None)

    def url_generator(g, F, N, k):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'List'
        info_copy['degree'] = str(g)
        info_copy['family'] = chr(F)
        info_copy['level'] = str(N)
        info_copy['weight'] = str(k)
        return url_for(".index", **info_copy)

    def pick_table(entry, X, typ):
        # Only support one table
        return entry

    dimension_common_postprocess(info, query, ['S'], ['new'], url_generator, pick_table)
    # Determine which entries should have an "n/a"
    na_query = {}
    common_parse(info, na_query, na_check=True)
    na_query['family'] = chr(info['family'])
    dim_dict = {}
    for rec in db.smf_newspaces.search(na_query, ['degree', 'family', 'level', 'weight', 'num_forms']):
        g = int(rec['degree'])
        F = ord(rec['family'])
        N = rec['level']
        k = tuple(rec['weight'])
        if (g,F,N,k) not in dim_dict:
            dim_dict[g,F,N,k] = 0
        if rec.get('num_forms') is None:
            dim_dict[g,F,N,k] = False
    delete_false(dim_dict)
    for form in res:
        g = int(form['degree'])
        F = ord(form['family'])
        N = form['level']
        k = tuple(form['weight'])
        if (g,F,N,k) in dim_dict:
            dim_dict[g,F,N,k] += form['dim']
    return dim_dict

@search_wrap(template="smf_dimension_search_results.html",
             table=db.smf_newforms,
             title='Dimension search results',
             err_title='Dimension search input error',
             per_page=None,
             projection=['level', 'weight', 'dim', 'degree', 'family'],
             postprocess=dimension_form_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list)
def dimension_form_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'degree' not in info:
        info['degree'] = 2
    info['degree'] = int(info['degree'])
    if 'family' not in info:
        info['family'] = 'paramodular'
    if len(info['family']) > 1:
        info['family'] = family_str_to_char(info['family'])
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    newform_parse(info, query)
    # We don't need to sort, since the dimensions are just getting added up
    query['__sort__'] = []

@search_wrap(template="smf_dimension_space_search_results.html",
             table=db.smf_newspaces,
             title='Dimension search results',
             err_title='Dimension search input error',
             per_page=None,
#             projection=['label', 'analytic_conductor', 'level', 'weight', 'conrey_indexes', 'dim', 'hecke_orbit_dims', 'AL_dims', 'char_conductor','eis_dim','eis_new_dim','cusp_dim', 'mf_dim', 'mf_new_dim', 'plus_dim', 'num_forms'],
             projection=['label', 'level', 'weight', 'degree', 'family', 'num_forms',
                         'total_dim',
                         'cusp_dim',
                         'eis_dim',
                         'eis_Q_dim',
                         'eis_F_dim',
                         'cusp_Y_dim',
                         'cusp_P_dim',
                         'cusp_G_dim',
                         'new_total_dim',
                         'new_cusp_dim',
                         'new_eis_dim',
                         'new_eis_Q_dim',
                         'new_eis_F_dim',
                         'new_cusp_Y_dim',
                         'new_cusp_P_dim',
                         'new_cusp_G_dim',
                         'old_total_dim',
                         'old_cusp_dim',
                         'old_eis_dim',
                         'old_eis_Q_dim',
                         'old_eis_F_dim',
                         'old_cusp_Y_dim',
                         'old_cusp_P_dim',
                         'old_cusp_G_dim'],
             postprocess=dimension_space_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list)
def dimension_space_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'degree' not in info:
        info['degree'] = 2
    info['degree'] = int(info['degree'])
    if 'family' not in info:
        info['family'] = 'paramodular'
    if len(info['family']) > 1:
        info['family'] = family_str_to_char(info['family'])
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    
    newspace_parse(info, query)
    # We don't need to sort, since the dimensions are just getting added up
    query['__sort__'] = []

space_columns = SearchColumns([
    LinkCol("label", "mf.siegel.label", "Label", url_for_label, default=True),
#    FloatCol("analytic_conductor", "smf.analytic_conductor", r"$A$", default=True, short_title="analytic conductor", align="left"),
    MultiProcessedCol("character", "mf.siegel.character", r"$\chi$", ["level", "conrey_indexes"],
                      lambda level,indexes: r'<a href="%s">\( \chi_{%s}(%s, \cdot) \)</a>' % (url_for("characters.render_Dirichletwebpage", modulus=level, number=indexes[0]), level, indexes[0]),
                      short_title="character", default=True),
    MathCol("char_order", "character.dirichlet.order", r"$\operatorname{ord}(\chi)$", short_title="character order", default=True),
    MathCol("cusp_dim", "smf.display_dim", "Cusp Dim", short_title="cuspidal dimension", default=True),
    MultiProcessedCol("decomp", "mf.siegel.dim_decomposition", "Decomp.", ["level", "weight", "char_orbit_label", "hecke_orbit_dims"], display_decomp, default=True, align="center", short_title="decomposition", td_class=" nowrap"),
    MultiProcessedCol("al_dims", "mf.siegel.atkin_lehner_dims", "AL-dims.", ["level", "weight", "ALdims"], display_ALdims, contingent=show_ALdims_col, default=True, short_title="Atkin-Lehner dimensions", align="center", td_class=" nowrap")])

@search_wrap(table=db.smf_newspaces,
             title='Newspace search results',
             err_title='Newspace search input error',
             columns=space_columns,
             shortcuts={'jump':jump_box,
                        'download':SMF_download().download_spaces},
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list)
def space_search(info, query):
    newspace_parse(info, query)
    print(info)
    set_info_funcs(info)

@smf.route("/Source")
def how_computed_page():
    # print("routed to how_computed_page")
    t = 'Source of Siegel modular form data'
    return render_template("multi.html", kids=['rcs.source.mf.siegel',
                           'rcs.ack.mf.siegel',
                           'rcs.cite.mf.siegel'], title=t,
                           bread=get_bread(other='Source'),
                           learnmore=learnmore_list_remove('Source'))

@smf.route("/Completeness")
def completeness_page():
    # print("routed to completeness_page")
    t = 'Completeness of Siegel modular form data'
    return render_template("single.html", kid='rcs.cande.mf.siegel', title=t,
                           bread=get_bread(other='Completeness'),
                           learnmore=learnmore_list_remove('Completeness'))

@smf.route("/Labels")
def labels_page():
    # print("routed to labels_page")
    t = 'Labels for Siegel modular forms'
    return render_template("single.html", kid='mf.siegel.label', title=t,
                           bread=get_bread(other='Labels'),
                           learnmore=learnmore_list_remove('labels'))

@smf.route("/Reliability")
def reliability_page():
    # print("routed to reliability_page")
    t = 'Reliability of Siegel modular form data'
    return render_template("single.html", kid='rcs.rigor.mf.siegel', title=t,
                           bread=get_bread(other='Reliability'),
                           learnmore=learnmore_list_remove('Reliability'))

def rel_dim_formatter(x):
    return 'dim=%s&dim_type=rel' % range_formatter(x)

def level_primes_formatter(x):
    subset = x.get('$containedin')
    if subset:
        return 'level_primes=%s&prime_quantifier=subset' % (','.join(map(str, subset)))
    supset = x.get('$contains')
    if supset:
        return 'level_primes=%s&prime_quantifier=supset' % (','.join(map(str, supset)))
    raise ValueError

def level_radical_formatter(x):
    # Hopefully people won't enter multiple large primes....
    factors = [p for p,e in ZZ(x).factor()]
    return 'level_primes=%s' % (','.join(map(str, factors)))

class SMF_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for Siegel modular forms
    """
    def __init__(self):
        self.nforms = comma(db.smf_newforms.count())
        #self.nspaces = comma(db.smf_newspaces.count({'num_forms':{'$gt':0}}))
        self.nspaces = comma(db.smf_newspaces.count({'cusp_dim':{'$gt':0}}))
        #self.ndim = comma(db.mf_hecke_cc.count())
        # !!! WARNING : at the moment not too long, but we do not want to
        # retain this
        self.ndim = comma(sum([f['dim'] for f in db.smf_newforms.search()]))
        self.weight_knowl = display_knowl('mf.siegel.weight_k_j', title='weight')
        self.level_knowl = display_knowl('mf.siegel.level', title='level')
        self.newform_knowl = display_knowl('mf.siegel.newform', title='newforms')
        self.newspace_knowl = display_knowl('mf.siegel.newspace', title='newspaces')
        stats_url = url_for(".statistics")

    @property
    def short_summary(self):
        return r'The database currently contains %s (Galois orbits of) %s, corresponding to %s Siegel modular forms over the complex numbers.  You can <a href="%s">browse further statistics</a> or <a href="%s">create your own</a>.' % (self.nforms, self.newform_knowl, self.ndim, url_for(".statistics"), url_for(".dynamic_statistics"))

    @property
    def summary(self):
        return r"The database currently contains %s (Galois orbits of) %s and %s nonzero %s, corresponding to %s Siegel modular forms over the complex numbers.  In addition to the statistics below, you can also <a href='%s'>create your own</a>." % (self.nforms, self.newform_knowl, self.nspaces, self.newspace_knowl, self.ndim, url_for(".dynamic_statistics"))

    extent_knowl = 'mf.siegel.statistics_extent'
    table = db.smf_newforms
    baseurl_func = ".index"
    # right now we don't have all these columns in our database.
    # we stick to what we have
    buckets = {'level':['1-100','101-300','301-600', '601-%d'%level_bound()],
               'degree':['2', '3-%d'%degree_bound()],
               'weight' : ['(3,2)', '(4,2)', '(5,2)-(8,2)', '(9,2)-(16,2)', '(17,2)-(%d,%d)' % (weight_bound(2)[0], weight_bound(2)[1])],
               'dim':['1','2','3','4','5','6-10','11-20','21-100','101-1000'],
                'char_order':['1','2','3','4','5','6-10','11-20','21-100','101-1000'],
               'char_degree':['1','2','3','4','5','6-10','11-20','21-100','101-1000']
    }
    reverses = {}
    sort_keys = { 'aut_rep_type' : aut_rep_type_sort_key }
    knowls = {'level': 'mf.siegel.level',
              'weight': 'mf.siegel.weight_k_j',
              'degree' : 'mf.siegel.degree',
              'dim' : 'mf.siegel.dimension',
              'char_order': 'character.dirichlet.order',
              'char_degree': 'character.dirichlet.degree',
              'num_forms': 'mf.siegel.galois_orbit' }
    
    top_titles = {
        'dim' : 'absolute dimension'
    }
    short_display = {'char_order': 'character order',
                     'char_degree': 'character degree',
                     'num_forms': 'newforms',
                     'dim' : 'abs. dimension'
    }

    formatters = {
#                  'char_parity': (lambda t: 'odd' if t in [-1,'-1'] else 'even')
        }

    query_formatters = {
        'level_primes': level_primes_formatter,
        'level_radical': level_radical_formatter
    }

    split_lists = {}

    stat_list = [

        {'cols': ['level', 'dim'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()}
        
# For some reason we do not have stats for num_forms. Maybe we don't have num_forms for all of them?
#        {'cols':'num_forms',
#         'table':db.smf_newspaces,
#         'top_title': [('number of newforms', 'mf.siegel.galois_orbit'), (r'in \(S_{k,j}^{\text{new}}(K(N))\)',# None)],
#        'url_extras': 'search_type=Spaces&'},

    ]
    # Used for dynamic stats
    dynamic_parse = staticmethod(newform_parse)
    dynamic_parent_page = "smf_refine_search.html"
    # right now we don't have all these columns in our database.
    # we stick to what we have
    dynamic_cols = ['level', 'weight', 'dim']

@smf.route("/stats")
def statistics():
    # print("routed to statistics")
    title = 'Siegel modular forms: Statistics'
    return render_template("display_stats.html", info=SMF_stats(), title=title, bread=get_bread(other='Statistics'), learnmore=learnmore_list())

@smf.route("/dynamic_stats")
def dynamic_statistics():
    # print("routed to dynamic_statistics")
    info = to_dict(request.args, search_array=SMFSearchArray())
    SMF_stats().dynamic_setup(info)
    title = 'Siegel modular forms: Dynamic statistics'
    return render_template("dynamic_stats.html", info=info, title=title, bread=get_bread(other='Dynamic Statistics'), learnmore=learnmore_list())

class SMFSearchArray(SearchArray):
    sort_knowl = 'smf.sort_order'
    _sort = [
        ('level', 'level', ['level', 'weight']),
        ('weight', 'weight', ['weight', 'level']),
        ('family', 'family', ['family', 'level']),
        ('degree', 'degree', ['degree', 'level']),
        ('character', 'character', ['level', 'char_orbit_index', 'weight']),
        ('prim', 'primitive character', ['char_conductor', 'prim_orbit_index', 'level', 'weight']),
        ('char_order', 'character order', ['char_order', 'level', 'char_orbit_index', 'weight']),
        ('Nk2', 'N(2k+j-2)^2', ['Nk2', 'level']),
        ('dim', 'dimension', ['dim', 'level', 'weight']),
        ('relative_dim', 'relative dimension', ['relative_dim', 'level', 'weight']),
        ('analytic_rank', 'analytic rank', ['analytic_rank', 'level', 'weight']),
        ('hecke_ring_index_factorization', 'coeff ring index', ['hecke_ring_index', 'level', 'weight']),
    ]
    for name, disp, sord in _sort:
        if 'char_orbit_index' not in sord:
            sord.append('char_orbit_index')
    _sort_spaces = _sort[:-4]
    _sort_spaces += [('cusp_dim', 'dim. cusp', ['cusp_dim','level'])]
    _sort_forms = [(name, disp, sord + ['dim', 'hecke_orbit']) for (name, disp, sord) in _sort]
    sorts = {'List': _sort_forms,
             'Traces': _sort_forms,
             'Spaces': _sort_spaces,
             'SpaceTraces': _sort_spaces}
    jump_example="2.S.1.12.0.a"
    jump_egspan="e.g. 2.S.1.12.0.a.a or 2.S.1.12.0.a"
    jump_knowl="mf.siegel.search_input"
    jump_prompt="Label"
    null_column_explanations = { # No need to display warnings for these
        'is_polredabs': False,
        'projective_image': False,
        'projective_image_type': False,
        'a4_dim': False,
        'a5_dim': False,
        's4_dim': False,
        'dihedral_dim': False,
        'hecke_ring_index': "coefficient ring index not computed when dimension larger than 20",
        'hecke_ring_generator_nbound': "coefficient ring generators not computed when dimension larger than 20",
        'nf_label': "coefficient field not computed when dimension larger than 20",
    }
    def __init__(self):

        degree = TextBox(
            name='degree',
            label='Degree',
            knowl='mf.siegel.degree',
            example='2',
            example_span='2, 1-4')

        family = SelectBox(
            name='family',
            label='Family',
            knowl='mf.siegel.family',
            options=[('paramodular', 'paramodular'),
                     ('Siegel', 'Siegel'),
                     ('principal', 'principal')],
            )

        level_quantifier = SelectBox(
            name='level_type',
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'prime power'),
                     ('square', 'square'),
                     ('squarefree', 'squarefree'),
                     ('divides','divides'),
                     ],
            min_width=110)
        level = TextBoxWithSelect(
            name='level',
            label='Level',
            knowl='mf.siegel.level',
            example='4',
            example_span='4, 1-20',
            select_box=level_quantifier)

        weight_quantifier = ParityMod(
            name='weight_parity',
            extra=['class="simult_select"', 'onchange="simult_change(event);"'])

        weight = TextBoxWithSelect(
            name='weight',
            label='Weight',
            knowl='mf.siegel.weight_k_j',
            example='2',
            example_span='2, 4-8',
            select_box=weight_quantifier)

        character_quantifier = ParityMod(
            name='char_parity',
            extra=['class="simult_select"', 'onchange="simult_change(event);"'])

        character = TextBoxWithSelect(
            name='char_label',
            knowl='mf.siegel.character',
            label='Character',
            short_label='Char.',
            example='20.d',
            example_span='20.d',
            select_box=character_quantifier)

        prime_quantifier = SubsetBox(
            name="prime_quantifier",
            min_width=110)
        level_primes = TextBoxWithSelect(
            name='level_primes',
            knowl='mf.bad_prime',
            label=r'Bad \(p\)',
            example='2,3',
            example_span='2,3',
            select_box=prime_quantifier)

        char_order = TextBox(
            name='char_order',
            label='Character order',
            knowl='character.dirichlet.order',
            example='1',
            example_span='1, 2-4')
        char_primitive = TextBox(
            name='prim_label',
            knowl='character.dirichlet.primitive',
            label='Primitive character',
            example='1.a',
            example_span='1.a')

        dim_quantifier = SelectBox(
            name='dim_type',
            options=[('', 'absolute'), ('rel', 'relative')],
            min_width=110)

        dim = TextBoxWithSelect(
            name='dim',
            label='Dim.',
            knowl='mf.siegel.dimension',
            example='1',
            example_span='2, 1-6',
            select_box=dim_quantifier)
        hdim = HiddenBox(
            name='dim',
            label='')

        space_dim = TextBox(
            name='cusp_dim',
            knowl='',
            label='Cusp Dim',
            example='1',
            example_span='1-5')
            
            
        coefficient_field = TextBox(
            name='nf_label',
            knowl='mf.siegel.coefficient_field',
            label='Coefficient field',
            example='1.1.1.1',
            example_span='4.0.144.1, Qsqrt5')

        aut_type = SelectBox(
            name='aut_rep_type',
            knowl='mf.siegel.automorphic_type',
            label='Automorphic type',
            options=[('', 'any type'), ('G', '(G)'), ('Y', '(Y)'),
                     ('P', '(P)'), ('Q', '(Q)'), ('B', '(B)'), ('F', '(F)')],
            )

        Nk2 = TextBox(
            name='Nk2',
            knowl='mf.siegel.nk2',
            label=r'\(N(2k+j-2)^2\)',
            example='40-100',
            example_span='40-100')

        coefficient_ring_index = TextBox(
            name='hecke_ring_index',
            label='Coefficient ring index',
            knowl='mf.siegel.coefficient_ring',
            example='1',
            example_span='1, 2-4')

        hecke_ring_generator_nbound = TextBox(
            name='hecke_ring_generator_nbound',
            label='Coefficient ring gens.',
            knowl='mf.siegel.hecke_ring_generators',
            example='20',
            example_span='7, 1-10')

        num_newforms = TextBox(
            name='num_forms',
            label='Num. ' + display_knowl("mf.siegel.newform", "newforms"),
            width=160,
            example='3')
        hnum_newforms = HiddenBox(
            name='num_forms',
            label='')

        results = CountBox()

        trace_coldisplay = TextBox(
            name='n',
            label='Columns to display',
            example='1-40',
            example_span='3,7,19, 40-90')

        trace_primality = SelectBox(
            name='n_primality',
            label='Show',
            options=[('', 'primes only'),
                     ('prime_powers', 'prime powers'),
                     ('all', 'all')])

        trace_an_constraints = TextBox(
            name='an_constraints',
            label='Trace constraints',
            example='a3=2,a5=0',
            example_span='a17=1, a8=0')

        trace_an_moduli = TextBox(
            name='an_modulo',
            label='Modulo',
            example_span='5, 16')

        trace_view = SelectBox(
            name='view_modp',
            label='View',
            options=[('', 'integers'),
                     ('reductions', 'reductions')])

        self.browse_array = [
            [degree, family],
            [level, weight],
            [level_primes, character],
            [char_order, char_primitive],
            [dim, coefficient_field],
            [coefficient_ring_index, hecke_ring_generator_nbound],
            [results, Nk2],
            [aut_type]
]
        self.refine_array = [
            [degree, family, level, weight],
            [level_primes, character, char_primitive, char_order, coefficient_field],
            [coefficient_ring_index, hecke_ring_generator_nbound, Nk2, dim, aut_type]
        ]
        self.space_array = [
            [degree, family, level, weight, Nk2],
            [level_primes, character, char_primitive, char_order, space_dim]
        ]

        self.sd_array = [
            [degree, family, level, weight, Nk2, hdim],
            [level_primes, character, char_primitive, char_order]
        ]

        self.traces_array = [
            RowSpacer(22),
            [trace_coldisplay, trace_primality],
            [trace_an_constraints, trace_an_moduli, trace_view]]

    def hidden(self, info):
        ans = [("start", "start"), ("count", "count"), ("hst", "search_type")]
        if self._st(info) == 'SpaceDimensions':
            ans.append(("all_spaces", "all_spaces"))
        return ans

    def main_array(self, info):
        if info is None:
            return self.browse_array
        search_type = info.get('search_type', info.get('hst', 'List'))
        if search_type in ['Spaces', 'SpaceTraces']:
            return self.space_array
        elif search_type == 'SpaceDimensions':
            return self.sd_array
        else:
            # search_type in ['List', 'Dimensions', 'Traces', 'DynStats']:
            return self.refine_array

    def search_types(self, info):
        basic = [('List', 'List of forms'),
                 ('Dimensions', 'Dimension table'),
                 ('Traces', 'Traces table'),
                 ('Random', 'Random form')]
        spaces = [('Spaces', 'List of spaces'),
                  ('SpaceDimensions', 'Dimension table'),
                  ('SpaceTraces', 'Traces table'),
                  ('RandomSpace', 'Random')]
        if info is None:
            return basic
        st = self._st(info)
        if st in ["List", "Dimensions", "Traces"]:
            return self._search_again(info, basic)
        elif st == "SpaceDimensions":
            return self._search_again(info, spaces)
        else:
            select_box = SelectBox(
                name="all_spaces",
                options=[("", "split spaces"),
                         ("yes", "all spaces")],
                width=None)
            search_again = SearchButtonWithSelect(
                value=st,
                description="Search again",
                select_box=select_box,
                label="Scope",
                knowl="mf.siegel.include_all_spaces")
            return [search_again] + [(v, d) for v, d in spaces if v != st]

    def html(self, info=None):
        # We need to override html to add the trace inputs
        layout = [self.hidden_inputs(info), self.main_table(info), self.buttons(info)]
        st = self._st(info)
        if st in ["Traces", "SpaceTraces"]:
            trace_table = self._print_table(self.traces_array, info, layout_type="box")
            layout.append(trace_table)
        return "\n".join(layout)
