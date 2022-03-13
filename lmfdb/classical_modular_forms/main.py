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
from lmfdb.backend.utils import range_formatter
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, FloatCol, CheckCol, ProcessedCol, MultiProcessedCol, ColGroup, SpacerCol
from lmfdb.api import datapage
from lmfdb.classical_modular_forms import cmf
from lmfdb.classical_modular_forms.web_newform import (
    WebNewform, convert_newformlabel_from_conrey, LABEL_RE,
    quad_field_knowl, cyc_display, field_display_gen)
from lmfdb.classical_modular_forms.web_space import (
    WebNewformSpace, WebGamma1Space, DimGrid, convert_spacelabel_from_conrey,
    get_bread, get_search_bread, get_dim_bread, newform_search_link,
    ALdim_table, NEWLABEL_RE as NEWSPACE_RE, OLDLABEL_RE as OLD_SPACE_LABEL_RE)
from lmfdb.classical_modular_forms.download import CMF_download
from lmfdb.sato_tate_groups.main import st_display_knowl

POSINT_RE = re.compile("^[1-9][0-9]*$")
ALPHA_RE = re.compile("^[a-z]+$")


_curdir = os.path.dirname(os.path.abspath(__file__))
ETAQUOTIENTS = yaml.load(open(os.path.join(_curdir, "eta.yaml")),
                         Loader=yaml.FullLoader)

@cached_function
def learnmore_list():
    """
    Return the learnmore list
    """
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Classical modular form labels', url_for(".labels_page"))]


def learnmore_list_remove(matchstring):
    """
    Return the learnmore list with the matchstring entry removed
    """
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

@cached_function
def Nk2_bound(nontriv=None):
    if nontriv:
        return db.mf_newforms.max('Nk2',{'char_order':{'$ne':1}})
    else:
        return db.mf_newforms.max('Nk2')
@cached_function
def weight_bound(nontriv=None):
    if nontriv:
        return db.mf_newforms.max('weight',{'char_order':{'$ne':1}})
    else:
        return db.mf_newforms.max('weight')

@cached_function
def level_bound(nontriv=None):
    if nontriv:
        return db.mf_newforms.max('level',{'char_order':{'$ne':1}})
    else:
        return db.mf_newforms.max('level')

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
                 'dim':dim}
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

    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series'}

    info['download_spaces'] = lambda results: any(space['dim'] > 1 for space in results)
    info['bigint_knowl'] = bigint_knowl

@cmf.route("/")
def index():
    info = to_dict(request.args, search_array=CMFSearchArray())
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
    info["stats"] = CMF_stats()
    info["weight_list"] = ('1', '2', '3', '4', '5-8', '9-16', '17-32', '33-64', '65-%d' % weight_bound() )
    info["level_list"] = ('1', '2-10', '11-100', '101-1000', '1001-2000', '2001-4000', '4001-6000', '6001-8000', '8001-%d' % level_bound() )
    return render_template("cmf_browse.html",
                           info=info,
                           title="Classical modular forms",
                           learnmore=learnmore_list(),
                           bread=get_bread())

@cmf.route("/random/")
@redirect_no_cache
def random_form():
    label = db.mf_newforms.random()
    return url_for_label(label)

@cmf.route("/random_space/")
@redirect_no_cache
def random_space():
    label = db.mf_newspaces.random()
    return url_for_label(label)

@cmf.route("/interesting_newforms")
def interesting_newforms():
    return interesting_knowls(
        "cmf",
        db.mf_newforms,
        url_for_label,
        regex=LABEL_RE,
        title="Some interesting newforms",
        bread=get_bread(other="Interesting newforms"),
        learnmore=learnmore_list()
    )

@cmf.route("/interesting_spaces")
def interesting_spaces():
    return interesting_knowls(
        "cmf",
        db.mf_newspaces,
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


def eta_quotient_texstring(etadata):
    r"""
    Returns a latex string representing an eta quotient.

    etadata should be a dictionary as returned from parsing `eta.yaml`.

    IMPLEMENTATION NOTE:
      numerstr and denomstr together form a texstring of the form
      \eta(Az)^B \eta(Cz)^D, potentially in fraction form.

      str will be a string representing something like
      q^A \prod_{n} (1 - q^{Bn})^C (1 - q^{Dn})^E
    """
    numerstr = ''
    denomstr = ''
    innerqstr = ''
    qfirstexp = 0  # compute A in the qstr representation
    for key, value in etadata.items():
        _texstr = '\\eta({}z)'.format(key if key != 1 else '')
        qfirstexp += key * value
        if value > 0:
            numerstr += _texstr
            if value != 1:
                numerstr += '^{%s}' % (value)
        else:
            denomstr += _texstr
            if value != -1:
                denomstr += '^{%s}' % (-value)
        innerqstr += '(1 - q^{%sn})^{%s}' % (key if key != 1 else '',
                                             value if value != 1 else '')
    if denomstr == '':
        etastr = numerstr
    else:
        etastr = '\\dfrac{%s}{%s}' % (numerstr, denomstr)

    qfirstexp = qfirstexp // 24
    etastr += '=q'
    if qfirstexp != 1:
        etastr += '^{%s}' % (qfirstexp)
    etastr += '\\prod_{n=1}^\\infty' + innerqstr
    return etastr


def render_newform_webpage(label):
    try:
        newform = WebNewform.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)

    info = to_dict(request.args)
    info['display_float'] = display_float
    info['format'] = info.get('format', 'embed')

    if label in ETAQUOTIENTS:
        info['eta_quotient'] = eta_quotient_texstring(ETAQUOTIENTS[label])

    errs = parse_n(info, newform, info['format'] in ['satake', 'satake_angle'])
    errs.extend(parse_m(info, newform))
    errs.extend(parse_prec(info))
    newform.setup_cc_data(info)
    if errs:
        flash_error("%s", "<br>".join(errs))
    return render_template("cmf_newform.html",
                           info=info,
                           newform=newform,
                           properties=newform.properties,
                           downloads=newform.downloads,
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.title,
                           friends=newform.friends,
                           KNOWL_ID="cmf.%s" % label)

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
    return render_template("cmf_embedded_newform.html",
                           info=info,
                           newform=newform,
                           properties=newform.properties,
                           downloads=newform.downloads,
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.embedded_title(m),
                           friends=newform.friends,
                           KNOWL_ID="cmf.%s" % label)

def render_space_webpage(label):
    try:
        space = WebNewformSpace.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info = {'results':space.newforms, # so we can reuse search result code
            'columns':newform_columns}
    set_info_funcs(info)
    return render_template("cmf_space.html",
                           info=info,
                           space=space,
                           properties=space.properties,
                           downloads=space.downloads,
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends,
                           KNOWL_ID="cmf.%s" % label)

def render_full_gamma1_space_webpage(label):
    try:
        space = WebGamma1Space.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info={}
    set_info_funcs(info)
    return render_template("cmf_full_gamma1_space.html",
                           info=info,
                           space=space,
                           properties=space.properties,
                           downloads=space.downloads,
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@cmf.route("/data/<label>")
def mf_data(label):
    slabel = label.split(".")
    if len(slabel) == 6:
        emb_label = label
        form_label = ".".join(slabel[:4])
        space_label = ".".join(slabel[:3])
        ocode = db.mf_newforms.lookup(form_label, "hecke_orbit_code")
        if ocode is None:
            return abort(404, f"{label} not in database")
        tables = ["mf_newforms", "mf_hecke_cc", "mf_newspaces", "mf_twists_cc", "mf_hecke_charpolys", "mf_newform_portraits", "mf_hecke_traces"]
        labels = [form_label, emb_label, space_label, emb_label, ocode, form_label, ocode]
        label_cols = ["label", "label", "label", "source_label", "hecke_orbit_code", "label", "hecke_orbit_code"]
        title = f"Embedded newform data - {label}"
    elif len(slabel) == 4:
        form_label = label
        space_label = ".".join(slabel[:3])
        ocode = db.mf_newforms.lookup(form_label, "hecke_orbit_code")
        if ocode is None:
            return abort(404, f"{label} not in database")
        tables = ["mf_newforms", "mf_hecke_nf", "mf_newspaces", "mf_twists_nf", "mf_hecke_charpolys", "mf_newform_portraits", "mf_hecke_traces"]
        labels = [form_label, form_label, space_label, form_label, ocode, form_label, ocode]
        label_cols = ["label", "label", "label", "source_label", "hecke_orbit_code", "label", "hecke_orbit_code"]
        title = f"Newform data - {label}"
    elif len(slabel) == 3:
        ocode = db.mf_newspaces.lookup(label, "hecke_orbit_code")
        if ocode is None:
            return abort(404, f"{label} not in database")
        tables = ["mf_newspaces", "mf_subspaces", "mf_newspace_portraits", "mf_hecke_newspace_traces"]
        labels = [label, label, label, ocode]
        label_cols = ["label", "label", "label", "hecke_orbit_code"]
        title = f"Newspace data - {label}"
    elif len(slabel) == 2:
        tables = ["mf_gamma1", "mf_gamma1_subspaces", "mf_gamma1_portraits"]
        labels = label
        label_cols = None
        title = fr"$\Gamma_1$ data - {label}"
    else:
        return abort(404, f"Invalid label {label}")
    bread = get_bread(other=[(label, url_for_label(label)), ("Data", " ")])
    return datapage(labels, tables, title=title, bread=bread, label_cols=label_cols)


@cmf.route("/<level>/")
def by_url_level(level):
    if not POSINT_RE.match(level):
        try:
            return redirect(url_for_label(level), code=301)
        except ValueError:
            flash_error("%s is not a valid newform or space label", level)
            return redirect(url_for(".index"))
    info = to_dict(request.args, search_array=CMFSearchArray())
    if 'level' in info:
        return redirect(url_for('.index', **request.args), code=307)
    else:
        info['level'] = level
    return newform_search(info)

@cmf.route("/<int:level>/<int:weight>/")
def by_url_full_gammma1_space_label(level, weight):
    label = str(level)+"."+str(weight)
    return render_full_gamma1_space_webpage(label)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/")
def by_url_space_label(level, weight, char_orbit_label):
    label = str(level)+"."+str(weight)+"."+char_orbit_label
    return render_space_webpage(label)

# Backward compatibility from before 2018
@cmf.route("/<int:level>/<int:weight>/<int:conrey_index>/")
def by_url_space_conreylabel(level, weight, conrey_index):
    label = convert_spacelabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_index))
    return redirect(url_for_label(label), code=301)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit_label, hecke_orbit):
    label = ".".join(map(str, [level, weight, char_orbit_label, hecke_orbit]))
    return render_newform_webpage(label)

# Backward compatibility from before 2018
@cmf.route("/<int:level>/<int:weight>/<int:conrey_index>/<hecke_orbit>/")
def by_url_newform_conreylabel(level, weight, conrey_index, hecke_orbit):
    label = convert_newformlabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_index)+"."+hecke_orbit)
    return redirect(url_for_label(label), code=301)

# Utility redirect for bread and links from embedding table
@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<embedding_label>/")
def by_url_newform_conrey5(level, weight, char_orbit_label, hecke_orbit, embedding_label):
    if embedding_label.count('.') != 1:
        return abort(404, "Invalid embedding label: periods")
    conrey_index, embedding = embedding_label.split('.')
    if not (conrey_index.isdigit() and embedding.isdigit()):
        return abort(404, "Invalid embedding label: not integers")
    return redirect(url_for("cmf.by_url_embedded_newform_label", level=level, weight=weight, char_orbit_label=char_orbit_label, hecke_orbit=hecke_orbit, conrey_index=conrey_index, embedding=embedding), code=301)

# Embedded modular form
@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<int:conrey_index>/<int:embedding>/")
def by_url_embedded_newform_label(level, weight, char_orbit_label, hecke_orbit, conrey_index, embedding):
    if conrey_index <= 0 or embedding <= 0:
        return abort(404, "Invalid embedding label: negative values")
    newform_label = ".".join(map(str, [level, weight, char_orbit_label, hecke_orbit]))
    embedding_label = ".".join(map(str, [conrey_index, embedding]))
    return render_embedded_newform_webpage(newform_label, embedding_label)

def url_for_label(label):
    if label == "random":
        return url_for("cmf.random_form")
    if not label:
        return abort(404, "Invalid label")

    slabel = label.split(".")
    if len(slabel) == 6:
        func = "cmf.by_url_embedded_newform_label"
    elif len(slabel) == 4:
        func = "cmf.by_url_newform_label"
    elif len(slabel) == 3:
        func = "cmf.by_url_space_label"
    elif len(slabel) == 2:
        func = "cmf.by_url_full_gammma1_space_label"
    elif len(slabel) == 1:
        func = "cmf.by_url_level"
    else:
        return abort(404, "Invalid label")
    keys = ['level', 'weight', 'char_orbit_label', 'hecke_orbit', 'conrey_index', 'embedding']
    keytypes = [POSINT_RE, POSINT_RE, ALPHA_RE, ALPHA_RE, POSINT_RE, POSINT_RE]
    for i in range (len(slabel)):
        if not keytypes[i].match(slabel[i]):
            raise ValueError("Invalid label")
    kwds = {keys[i]: val for i, val in enumerate(slabel)}
    return url_for(func, **kwds)

def jump_box(info):
    jump = info.pop("jump").strip()
    errmsg = None
    if OLD_SPACE_LABEL_RE.match(jump):
        jump = convert_spacelabel_from_conrey(jump)
    #handle direct trace_hash search
    if re.match(r'^\#\d+$', jump) and ZZ(jump[1:]) < 2**61:
        label = db.mf_newforms.lucky({'trace_hash': ZZ(jump[1:].strip())}, projection="label")
        if label:
            return redirect(url_for_label(label), 301)
        else:
            errmsg = "hash %s not found"
    elif jump == 'yes':
        query = {}
        newform_parse(info, query)
        jump = db.mf_newforms.lucky(query, 'label', sort = None)
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


@cmf.route("/download_qexp/<label>")
def download_qexp(label):
    return CMF_download().download_qexp(label, lang='sage')

@cmf.route("/download_traces/<label>")
def download_traces(label):
    return CMF_download().download_traces(label)

@cmf.route("/download_newform_to_magma/<label>")
def download_newform_to_magma(label):
    return CMF_download().download_newform_to_magma(label)

@cmf.route("/download_newform/<label>")
def download_newform(label):
    return CMF_download().download_newform(label)

@cmf.route("/download_embedded_newform/<label>")
def download_embedded_newform(label):
    return CMF_download().download_embedding(label)

@cmf.route("/download_newspace/<label>")
def download_newspace(label):
    return CMF_download().download_newspace(label)

@cmf.route("/download_full_space/<label>")
def download_full_space(label):
    return CMF_download().download_full_space(label)

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
def common_parse(info, query, na_check=False):
    parse_ints(info, query, 'level', name="Level")
    parse_character(info, query, 'char_label', name='Character orbit', prim=False)
    parse_character(info, query, 'prim_label', name='Primitive character', prim=True)
    parse_ints(info, query, 'weight', name="Weight")
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
    if not na_check and info.get('search_type') != 'SpaceDimensions':
        if info.get('dim_type') == 'rel':
            parse_ints(info, query, 'dim', qfield='relative_dim', name="Dimension")
        else:
            parse_ints(info, query, 'dim', name="Dimension")


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
    parse_ints(info, query, 'artin_degree', name="Artin degree")

def newspace_parse(info, query):
    for key, display in newform_only_fields.items():
        if key in info:
            msg = "%s not valid when searching for spaces"
            flash_error(msg, display)
            raise ValueError(msg  % display)
    if 'dim' not in info and 'hst' not in info:
        # When coming from browse page, add dim condition to only show non-empty spaces
        info['dim'] = '1-'
    if info.get('all_spaces') == 'yes' and 'num_forms' in query:
        msg = "Cannot specify number of newforms while requesting all spaces"
        flash_error(msg)
        raise ValueError(msg)
    common_parse(info, query)
    if info['search_type'] != 'SpaceDimensions':
        parse_ints(info, query, 'num_forms', name='Number of newforms')
        if 'num_forms' not in query and info.get('all_spaces') != 'yes':
            # Don't show spaces that only include dimension data but no newforms (Nk2 > 4000, nontrivial character)
            query['num_forms'] = {'$exists':True}

def _trace_col(i):
    return ProcessedCol("traces", None, rf"$a_{{{nth_prime(i+1)}}}$", lambda tdisp: bigint_knowl(tdisp[i], 12), orig="trace_display", align="right", default=True)

def _AL_col(i, p):
    return ProcessedCol("atkin_lehner", None, str(p), lambda evs: "+" if evs[i][1] == 1 else "-", orig="atkin_lehner_eigenvals", align="center", mathmode=True, default=True)

newform_columns = SearchColumns([
    LinkCol("label", "cmf.label", "Label", url_for_label, default=True),
    MathCol("level", "cmf.level", "Level"),
    MathCol("weight", "cmf.weight", "Weight"),
    MultiProcessedCol("character", "cmf.character", "Char",
                      ["level", "char_orbit_label"],
                      lambda level, orb: display_knowl('character.dirichlet.orbit_data', title=f"{level}.{orb}", kwargs={"label":f"{level}.{orb}"}),
                      short_title="character"),
    MultiProcessedCol("prim", "character.dirichlet.primitive", "Prim",
                      ["char_conductor", "prim_orbit_index"],
                      lambda cond, ind: display_knowl('character.dirichlet.orbit_data', title=f"{cond}.{num2letters(ind)}", kwargs={"label":f"{cond}.{num2letters(ind)}"}),
                      short_title="primitive character"),
    MathCol("char_order", "character.dirichlet.order", "Char order", short_title="character order"),
    MathCol("dim", "cmf.dimension", "Dim", default=True, align="right", short_title="dimension"),
    MathCol("relative_dim", "cmf.relative_dimension", "Rel. Dim", align="right", short_title="relative dimension"),
    FloatCol("analytic_conductor", "cmf.analytic_conductor", r"$A$", default=True, align="center", short_title="analytic conductor"),
    MultiProcessedCol("field", "cmf.coefficient_field", "Field", ["field_poly_root_of_unity", "dim", "field_poly_is_real_cyclotomic", "nf_label", "field_poly", "field_disc_factorization"], nf_link, default=True),
    ProcessedCol("projective_image", "cmf.projective_image", "Image",
                 lambda img: ('' if img=='?' else '$%s_{%s}$' % (img[:1], img[1:])),
                 contingent=lambda info: any(mf.get('weight') == 1 for mf in info["results"]),
                 default=lambda info: all(mf.get('weight') == 1 for mf in info["results"]),
                 align="center", short_title="projective image"),
    MultiProcessedCol("cm", "cmf.self_twist", "CM",
                      ["is_cm", "cm_discs"],
                      lambda is_cm, cm_discs: ", ".join(map(quad_field_knowl, cm_discs)) if is_cm else "None",
                      short_title="CM",
                      default=True),
    MultiProcessedCol("rm", "cmf.self_twist", "RM",
                      ["is_rm", "rm_discs"],
                      lambda is_rm, rm_discs: ", ".join(map(quad_field_knowl, rm_discs)) if is_rm else "None",
                      contingent=lambda info: any(mf.get('weight') == 1 for mf in info["results"]),
                      short_title="RM",
                      default=True),
    CheckCol("is_self_dual", "cmf.selfdual", "Self-dual"),
    MathCol("inner_twist_count", "cmf.inner_twist_count", "Inner twists"),
    MathCol("analytic_rank", "cmf.analytic_rank", "Rank*"),
    ColGroup("traces", "cmf.trace_form", "Traces",
             [_trace_col(i) for i in range(4)],
             default=True),
    SpacerCol("atkin_lehner", contingent=display_AL, default=True),
    ColGroup("atkin_lehner", "cmf.atkin-lehner", "A-L signs",
             lambda info: [_AL_col(i, pair[0]) for i, pair in enumerate(info["results"][0]["atkin_lehner_eigenvals"])],
             contingent=display_AL, default=True, orig=["atkin_lehner_eigenvals"]),
    ProcessedCol("fricke_eigenval", "cmf.fricke", "Fricke sign",
                 lambda ev: "$+$" if ev == 1 else ("$-$" if ev else ""),
                 contingent=display_Fricke, default=lambda info: not display_AL(info), align="center"),
    ProcessedCol("hecke_ring_index_factorization", "cmf.coefficient_ring", "Coefficient ring index",
                 lambda fac: "" if fac=="" else factor_base_factorization_latex(fac), mathmode=True, align="center"),
    ProcessedCol("sato_tate_group", "cmf.sato_tate", "Sato-Tate", st_display_knowl, short_title="Sato-Tate group"),
    MultiProcessedCol("qexp", "cmf.q-expansion", "$q$-expansion", ["label", "qexp_display"],
                      lambda label, disp: fr'<a href="{url_for_label(label)}">\({disp}\)</a>' if disp else "",
                      default=True)],
    ['analytic_conductor', 'analytic_rank', 'atkin_lehner_eigenvals', 'char_conductor', 'char_orbit_label', 'char_order', 'cm_discs', 'dim', 'relative_dim', 'field_disc_factorization', 'field_poly', 'field_poly_is_real_cyclotomic', 'field_poly_root_of_unity', 'fricke_eigenval', 'hecke_ring_index_factorization', 'inner_twist_count', 'is_cm', 'is_rm', 'is_self_dual', 'label', 'level', 'nf_label', 'prim_orbit_index', 'projective_image', 'qexp_display', 'rm_discs', 'sato_tate_group', 'trace_display', 'weight'],
    tr_class=["middle bottomlined", ""])

@search_wrap(table=db.mf_newforms,
             title='Newform search results',
             err_title='Newform Search Input Error',
             columns=newform_columns,
             shortcuts={'jump':jump_box,
                        'download':CMF_download(),
                        #'download_exact':download_exact,
                        #'download_complex':download_complex
             },
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list)
def newform_search(info, query):
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
        table = db.mf_hecke_newspace_traces if spaces else db.mf_hecke_traces
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

@search_wrap(template="cmf_trace_search_results.html",
             table=db.mf_newforms,
             title='Newform search results',
             err_title='Newform search input error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download().download_multiple_traces},
             projection=['label', 'dim', 'hecke_orbit_code', 'weight'],
             postprocess=trace_postprocess,
             bread=get_search_bread,
             learnmore=learnmore_list)
def trace_search(info, query):
    set_Trn(info, query)
    newform_parse(info, query)
    process_an_constraints(info, query)
    set_info_funcs(info)

@search_wrap(template="cmf_space_trace_search_results.html",
             table=db.mf_newspaces,
             title='Newspace search results',
             err_title='Newspace search input error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download().download_multiple_space_traces},
             projection=['label', 'dim', 'hecke_orbit_code', 'weight'],
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
    try:
        info['weight_list'] = integer_options(info['weight'], max_opts=200)
    except ValueError:
        raise ValueError("Table too large: at most 200 options for weight")
    if 'weight_parity' in query:
        if query['weight_parity'] == -1:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 1]
        else:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 0]
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
    urlgen_info['count'] = 50
    # Remove entries that are unused for dimension tables
    urlgen_info.pop('hidden_search_type', None)
    urlgen_info.pop('number', None)
    urlgen_info.pop('numforms', None)
    urlgen_info.pop('dim', None)
    urlgen_info.pop('search_array', None)
    def url_generator_list(N, k):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'Spaces'
        info_copy['level'] = str(N)
        info_copy['weight'] = str(k)
        return url_for(".index", **info_copy)
    if 'char_orbit_index' in query or 'prim_orbit_index' in query:
        url_generator = url_generator_list
    elif query.get('char_order') == 1:
        def url_generator(N, k):
            return url_for(".by_url_space_label", level=N, weight=k, char_orbit_label="a")
    elif 'char_order' in query:
        url_generator = url_generator_list
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
    dimension_common_postprocess(info, query, ['M', 'S', 'E'], ['all', 'new', 'old'],
                                 url_generator, pick_table, switch_text)
    dim_dict = {}
    for space in res:
        N = space['level']
        k = space['weight']
        dims = DimGrid.from_db(space)
        if space.get('num_forms') is None:
            dim_dict[N,k] = False
        elif (N,k) not in dim_dict:
            dim_dict[N,k] = dims
        elif dim_dict[N,k] is not False:
            dim_dict[N,k] += dims
    delete_false(dim_dict)
    return dim_dict

def dimension_form_postprocess(res, info, query):
    urlgen_info = dict(info)
    urlgen_info['count'] = 50
    # Remove entries that are unused for dimension tables
    urlgen_info.pop('hidden_search_type', None)
    urlgen_info.pop('number', None)
    urlgen_info.pop('search_array', None)
    def url_generator(N, k):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'List'
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
    dim_dict = {}
    for rec in db.mf_newspaces.search(na_query, ['level', 'weight', 'num_forms']):
        N = rec['level']
        k = rec['weight']
        if (N,k) not in dim_dict:
            dim_dict[N,k] = 0
        if rec.get('num_forms') is None:
            dim_dict[N,k] = False
    delete_false(dim_dict)
    for form in res:
        N = form['level']
        k = form['weight']
        if (N,k) in dim_dict:
            dim_dict[N,k] += form['dim']
    return dim_dict

@search_wrap(template="cmf_dimension_search_results.html",
             table=db.mf_newforms,
             title='Dimension search results',
             err_title='Dimension search input error',
             per_page=None,
             projection=['level', 'weight', 'dim'],
             postprocess=dimension_form_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list)
def dimension_form_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    newform_parse(info, query)
    # We don't need to sort, since the dimensions are just getting added up
    query['__sort__'] = []

@search_wrap(template="cmf_dimension_space_search_results.html",
             table=db.mf_newspaces,
             title='Dimension search results',
             err_title='Dimension search input error',
             per_page=None,
             projection=['label', 'analytic_conductor', 'level', 'weight', 'conrey_indexes', 'dim', 'hecke_orbit_dims', 'AL_dims', 'char_conductor','eis_dim','eis_new_dim','cusp_dim', 'mf_dim', 'mf_new_dim', 'plus_dim', 'num_forms'],
             postprocess=dimension_space_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list)
def dimension_space_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    newspace_parse(info, query)
    # We don't need to sort, since the dimensions are just getting added up
    query['__sort__'] = []

space_columns = SearchColumns([
    LinkCol("label", "cmf.label", "Label", url_for_label, default=True),
    FloatCol("analytic_conductor", "cmf.analytic_conductor", r"$A$", default=True, short_title="analytic conductor", align="left"),
    MultiProcessedCol("character", "cmf.character", r"$\chi$", ["level", "conrey_indexes"],
                      lambda level,indexes: r'<a href="%s">\( \chi_{%s}(%s, \cdot) \)</a>' % (url_for("characters.render_Dirichletwebpage", modulus=level, number=indexes[0]), level, indexes[0]),
                      short_title="character", default=True),
    MathCol("char_order", "character.dirichlet.order", r"$\operatorname{ord}(\chi)$", short_title="character order", default=True),
    MathCol("dim", "cmf.display_dim", "Dim.", short_title="dimension", default=True),
    MultiProcessedCol("decomp", "cmf.dim_decomposition", "Decomp.", ["level", "weight", "char_orbit_label", "hecke_orbit_dims"], display_decomp, default=True, align="center", short_title="decomposition", td_class=" nowrap"),
    MultiProcessedCol("al_dims", "cmf.atkin_lehner_dims", "AL-dims.", ["level", "weight", "AL_dims"], display_ALdims, contingent=show_ALdims_col, default=True, short_title="Atkin-Lehner dimensions", align="center", td_class=" nowrap")])

@search_wrap(table=db.mf_newspaces,
             title='Newspace search results',
             err_title='Newspace search input error',
             columns=space_columns,
             shortcuts={'jump':jump_box,
                        'download':CMF_download().download_spaces},
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list)
def space_search(info, query):
    newspace_parse(info, query)
    set_info_funcs(info)

@cmf.route("/Source")
def how_computed_page():
    t = 'Source of classical modular form data'
    return render_template("multi.html", kids=['rcs.source.cmf',
                           'rcs.ack.cmf',
                           'rcs.cite.cmf'], title=t,
                           bread=get_bread(other='Source'),
                           learnmore=learnmore_list_remove('Source'))

@cmf.route("/Completeness")
def completeness_page():
    t = 'Completeness of classical modular form data'
    return render_template("single.html", kid='rcs.cande.cmf', title=t,
                           bread=get_bread(other='Completeness'),
                           learnmore=learnmore_list_remove('Completeness'))

@cmf.route("/Labels")
def labels_page():
    t = 'Labels for classical modular forms'
    return render_template("single.html", kid='cmf.label', title=t,
                           bread=get_bread(other='Labels'),
                           learnmore=learnmore_list_remove('labels'))

@cmf.route("/Reliability")
def reliability_page():
    t = 'Reliability of classical modular form data'
    return render_template("single.html", kid='rcs.rigor.cmf', title=t,
                           bread=get_bread(other='Reliability'),
                           learnmore=learnmore_list_remove('Reliability'))


def projective_image_sort_key(im_type):
    if im_type == 'A4':
        return -3
    elif im_type == 'S4':
        return -2
    elif im_type == 'A5':
        return -1
    elif im_type is None:
        return 10000
    else:
        return int(im_type[1:])

def self_twist_type_formatter(x):
    if x == 0:
        return 'neither'
    if x == 1:
        return 'CM only'
    if x == 2:
        return 'RM only'
    if x == 3:
        return 'both'
    return x # c = 'neither', 'CM only', 'RM only' or 'both'

def rel_dim_formatter(x):
    return 'dim=%s&dim_type=rel' % range_formatter(x)

def self_twist_type_query_formatter(x):
    if x in [0, 'neither']:
        return 'cm=no&rm=no'
    elif x in [1, 'CM only']:
        return 'cm=yes&rm=no'
    elif x in [2, 'RM only']:
        return 'cm=no&rm=yes'
    elif x in [3, 'both']:
        return 'cm=yes&rm=yes'

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

class CMF_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for classical modular forms
    """
    def __init__(self):
        self.nforms = comma(db.mf_newforms.count())
        self.nspaces = comma(db.mf_newspaces.count({'num_forms':{'$gt':0}}))
        self.ndim = comma(db.mf_hecke_cc.count())
        #self.weight_knowl = display_knowl('cmf.weight', title='weight')
        #self.level_knowl = display_knowl('cmf.level', title='level')
        self.newform_knowl = display_knowl('cmf.newform', title='newforms')
        self.newspace_knowl = display_knowl('cmf.newspace', title='newspaces')
        #stats_url = url_for(".statistics")

    @property
    def short_summary(self):
        return r'The database currently contains %s (Galois orbits of) %s, corresponding to %s modular forms over the complex numbers.  You can <a href="%s">browse further statistics</a> or <a href="%s">create your own</a>.' % (self.nforms, self.newform_knowl, self.ndim, url_for(".statistics"), url_for(".dynamic_statistics"))

    @property
    def summary(self):
        return r"The database currently contains %s (Galois orbits of) %s and %s nonzero %s, corresponding to %s modular forms over the complex numbers.  In addition to the statistics below, you can also <a href='%s'>create your own</a>." % (self.nforms, self.newform_knowl, self.nspaces, self.newspace_knowl, self.ndim, url_for(".dynamic_statistics"))

    extent_knowl = 'cmf.statistics_extent'
    table = db.mf_newforms
    baseurl_func = ".index"
    buckets = {'level':['1','2-10','11-100','101-1000','1001-2000', '2001-4000','4001-6000','6001-8000','8001-%d'%level_bound()],
               'weight':['1','2','3','4','5-8','9-16','17-32','33-64','65-%d'%weight_bound()],
               'dim':['1','2','3','4','5','6-10','11-20','21-100','101-1000','1001-10000','10001-100000'],
               'relative_dim':['1','2','3','4','5','6-10','11-20','21-100','101-1000'],
               'char_order':['1','2','3','4','5','6-10','11-20','21-100','101-1000'],
               'char_degree':['1','2','3','4','5','6-10','11-20','21-100','101-1000']}
    reverses = {'cm_discs': True}
    sort_keys = {'projective_image': projective_image_sort_key}
    knowls = {'level': 'cmf.level',
              'weight': 'cmf.weight',
              'dim': 'cmf.dimension',
              'relative_dim': 'cmf.dimension',
              'char_order': 'character.dirichlet.order',
              'char_degree': 'character.dirichlet.degree',
              'analytic_rank': 'cmf.analytic_rank',
              'projective_image': 'cmf.projective_image',
              'num_forms': 'cmf.galois_orbit',
              'inner_twist_count': 'cmf.inner_twist',
              'self_twist_type': 'cmf.self_twist',
              'cm_discs': 'cmf.cm_form',
              'rm_discs': 'cmf.rm_form'}
    top_titles = {'dim': 'absolute dimension',
                  'relative_dim': 'relative dimension',
                  'inner_twist_count': 'inner twists',
                  'cm_discs': 'complex multiplication',
                  'rm_discs': 'real multiplication'}
    short_display = {'char_order': 'character order',
                     'char_degree': 'character degree',
                     'num_forms': 'newforms',
                     'inner_twist_count': 'inner twists',
                     'cm_discs': 'CM disc',
                     'rm_discs': 'RM disc',
                     'dim': 'abs. dimension',
                     'relative_dim': 'rel. dimension'}
    formatters = {'projective_image': (lambda t: 'Unknown' if t is None else r'\(%s_{%s}\)' % (t[0], t[1:])),
                  'char_parity': (lambda t: 'odd' if t in [-1,'-1'] else 'even'),
                  'inner_twist_count': (lambda x: ('Unknown' if x == -1 else str(x))),
                  'self_twist_type': self_twist_type_formatter}
    query_formatters = {'projective_image': (lambda t: r'projective_image=%s' % (t,)),
                        'self_twist_type': self_twist_type_query_formatter,
                        'inner_twist_count': (lambda x: 'inner_twist_count={0}'.format(x if x != 'Unknown' else '-1')),
                        'relative_dim': rel_dim_formatter,
                        'level_primes': level_primes_formatter,
                        'level_radical': level_radical_formatter,
                        'cm_discs': (lambda t: r'self_twist_discs=%d' % (t,)),
                        'rm_discs': (lambda t: r'self_twist_discs=%d' % (t,)),
                        }
    split_lists = {'cm_discs': True,
                   'rm_discs': True}
    stat_list = [
        {'cols': ['level', 'weight'],
         'proportioner': proportioners.per_col_total,
         'totaler': totaler()},
        {'cols': ['level', 'dim'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
        {'cols': ['char_order', 'relative_dim'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
        {'cols':'analytic_rank',
         'totaler':{'avg':True}},
        {'cols':'projective_image',
         'top_title':[('projective images', 'cmf.projective_image'),
                      ('for weight 1 forms', None)],
         'constraint':{'weight': 1}},
        {'cols':'num_forms',
         'table':db.mf_newspaces,
         'top_title': [('number of newforms', 'cmf.galois_orbit'), (r'in \(S_k(N, \chi)\)', None)],
         'url_extras': 'search_type=Spaces&'},
        {'cols':'inner_twist_count'},
        {'cols':['self_twist_type', 'weight'],
         'title_joiner': ' by ',
         'proportioner': proportioners.per_col_total,
         'totaler': totaler(col_counts=False, corner_count=False)},
        {'cols': 'cm_discs',
         'totaler':{}},
        {'cols': 'rm_discs',
         'totaler':{}},
    ]
    # Used for dynamic stats
    dynamic_parse = staticmethod(newform_parse)
    dynamic_parent_page = "cmf_refine_search.html"
    dynamic_cols = ['level', 'weight', 'dim', 'relative_dim', 'analytic_conductor', 'char_order', 'char_degree', 'self_twist_type', 'inner_twist_count', 'analytic_rank', 'char_parity', 'projective_image', 'projective_image_type', 'artin_degree']

@cmf.route("/stats")
def statistics():
    title = 'Classical modular forms: Statistics'
    return render_template("display_stats.html", info=CMF_stats(), title=title, bread=get_bread(other='Statistics'), learnmore=learnmore_list())

@cmf.route("/dynamic_stats")
def dynamic_statistics():
    info = to_dict(request.args, search_array=CMFSearchArray())
    CMF_stats().dynamic_setup(info)
    title = 'Classical modular forms: Dynamic statistics'
    return render_template("dynamic_stats.html", info=info, title=title, bread=get_bread(other='Dynamic Statistics'), learnmore=learnmore_list())

class CMFSearchArray(SearchArray):
    sort_knowl = 'cmf.sort_order'
    _sort = [
        ('', 'analytic conductor', ['analytic_conductor', 'level']),
        ('level', 'level', ['level', 'weight']),
        ('weight', 'weight', ['weight', 'level']),
        ('character', 'character', ['level', 'char_orbit_index', 'weight']),
        ('prim', 'primitive character', ['char_conductor', 'prim_orbit_index', 'level', 'weight']),
        ('char_order', 'character order', ['char_order', 'level', 'char_orbit_index', 'weight']),
        ('Nk2', 'Nk^2', ['Nk2', 'level']),
        ('dim', 'dimension', ['dim', 'level', 'weight']),
        ('relative_dim', 'relative dimension', ['relative_dim', 'level', 'weight']),
        ('analytic_rank', 'analytic rank', ['analytic_rank', 'level', 'weight']),
        ('inner_twist_count', 'inner twist count', ['inner_twist_count', 'level', 'weight']),
        ('hecke_ring_index_factorization', 'coeff ring index', ['hecke_ring_index', 'level', 'weight']),
    ]
    for name, disp, sord in _sort:
        if 'char_orbit_index' not in sord:
            sord.append('char_orbit_index')
    _sort_spaces = _sort[:-3]
    _sort_forms = [(name, disp, sord + ['hecke_orbit']) for (name, disp, sord) in _sort]
    sorts = {'List': _sort_forms,
             'Traces': _sort_forms,
             'Spaces': _sort_spaces,
             'SpaceTraces': _sort_spaces}
    jump_example="3.6.a.a"
    jump_egspan="e.g. 3.6.a.a, 55.3.d or 20.5"
    jump_knowl="cmf.search_input"
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
            knowl='cmf.level',
            example='4',
            example_span='4, 1-20',
            select_box=level_quantifier)

        weight_quantifier = ParityMod(
            name='weight_parity',
            extra=['class="simult_select"', 'onchange="simult_change(event);"'])

        weight = TextBoxWithSelect(
            name='weight',
            label='Weight',
            knowl='cmf.weight',
            example='2',
            example_span='2, 4-8',
            select_box=weight_quantifier)

        character_quantifier = ParityMod(
            name='char_parity',
            extra=['class="simult_select"', 'onchange="simult_change(event);"'])

        character = TextBoxWithSelect(
            name='char_label',
            knowl='cmf.character',
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
            knowl='cmf.bad_prime',
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
            knowl='cmf.dimension',
            example='1',
            example_span='2, 1-6',
            select_box=dim_quantifier)
        hdim = HiddenBox(
            name='dim',
            label='')

        coefficient_field = TextBox(
            name='nf_label',
            knowl='cmf.coefficient_field',
            label='Coefficient field',
            example='1.1.1.1',
            example_span='4.0.144.1, Qsqrt5')

        analytic_conductor = TextBox(
            name='analytic_conductor',
            knowl='cmf.analytic_conductor',
            label='Analytic conductor',
            example='1-10',
            example_span='1-10')

        Nk2 = TextBox(
            name='Nk2',
            knowl='cmf.nk2',
            label=r'\(Nk^2\)',
            example='40-100',
            example_span='40-100')

        cm = SelectBox(
            name='cm',
            options=[('', 'any CM'), ('yes', 'has CM'), ('no', 'no CM')],
            width=82)
        rm = SelectBox(
            name='rm',
            options=[('', 'any RM'), ('yes', 'has RM'), ('no', 'no RM')],
            width=82)
        self_twist = DoubleSelectBox(
            label='Self-twists',
            knowl='cmf.self_twist',
            select_box1=cm,
            select_box2=rm,
            example_col=True)

        self_twist_discs = TextBox(
            name='self_twist_discs',
            label='CM/RM discriminant',
            knowl='cmf.self_twist',
            example='-3',
            example_span='-3')

        inner_twist_count = TextBox(
            name='inner_twist_count',
            knowl='cmf.inner_twist_count',
            label='Inner twist count',
            example='1-',
            example_span='0, 1-, 2-3')

        is_self_dual = YesNoBox(
            name='is_self_dual',
            knowl='cmf.selfdual',
            label='Is self-dual')

        coefficient_ring_index = TextBox(
            name='hecke_ring_index',
            label='Coefficient ring index',
            knowl='cmf.coefficient_ring',
            example='1',
            example_span='1, 2-4')

        hecke_ring_generator_nbound = TextBox(
            name='hecke_ring_generator_nbound',
            label='Coefficient ring gens.',
            knowl='cmf.hecke_ring_generators',
            example='20',
            example_span='7, 1-10')

        analytic_rank= TextBox(
            name='analytic_rank',
            label='Analytic rank',
            knowl='cmf.analytic_rank',
            example='1',
            example_span='1, 2-4')

        projective_image = TextBoxNoEg(
            name='projective_image',
            label='Projective image',
            knowl='cmf.projective_image',
            example='D15',
            example_span='wt. 1 only')

        projective_image_type = SelectBoxNoEg(
            name='projective_image_type',
            knowl='cmf.projective_image',
            label='Projective image type',
            options=[('', ''),
                     ('Dn', 'Dn'),
                     ('A4', 'A4'),
                     ('S4', 'S4'),
                     ('A5','A5')],
            example_span='wt. 1 only')

        num_newforms = TextBox(
            name='num_forms',
            label='Num. ' + display_knowl("cmf.newform", "newforms"),
            width=160,
            example='3')
        hnum_newforms = HiddenBox(
            name='num_forms',
            label='')

        results = CountBox()

        wt1only = BasicSpacer("Only for weight 1:")

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
            [level, weight],
            [level_primes, character],
            [char_order, char_primitive],
            [dim, coefficient_field],
            [analytic_conductor, Nk2],
            [self_twist, self_twist_discs],
            [inner_twist_count, is_self_dual],
            [coefficient_ring_index, hecke_ring_generator_nbound],
            [analytic_rank, projective_image],
            [results, projective_image_type]]

        self.refine_array = [
            [level, weight, analytic_conductor, Nk2, dim],
            [level_primes, character, char_primitive, char_order, coefficient_field],
            [self_twist, self_twist_discs, inner_twist_count, is_self_dual, analytic_rank],
            [coefficient_ring_index, hecke_ring_generator_nbound, wt1only, projective_image, projective_image_type]]

        self.space_array = [
            [level, weight, analytic_conductor, Nk2, dim],
            [level_primes, character, char_primitive, char_order, num_newforms]
        ]

        self.sd_array = [
            [level, weight, analytic_conductor, Nk2, hdim],
            [level_primes, character, char_primitive, char_order, hnum_newforms]
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
                knowl="cmf.include_all_spaces")
            return [search_again] + [(v, d) for v, d in spaces if v != st]

    def html(self, info=None):
        # We need to override html to add the trace inputs
        layout = [self.hidden_inputs(info), self.main_table(info), self.buttons(info)]
        st = self._st(info)
        if st in ["Traces", "SpaceTraces"]:
            trace_table = self._print_table(self.traces_array, info, layout_type="box")
            layout.append(trace_table)
        return "\n".join(layout)
