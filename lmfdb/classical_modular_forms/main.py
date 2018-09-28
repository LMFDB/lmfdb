from flask import render_template, url_for, redirect, abort, request, flash, make_response
from markupsafe import Markup
import re
from collections import defaultdict
from lmfdb.db_backend import db
from lmfdb.db_encoding import Json
from lmfdb.classical_modular_forms import cmf
from lmfdb.search_parsing import parse_ints, parse_signed_ints, parse_bool, parse_bool_unknown, parse_nf_string, integer_options, search_parser
from lmfdb.search_wrapper import search_wrap
from lmfdb.downloader import Downloader
from lmfdb.utils import flash_error, to_dict, comma, display_knowl, polyquo_knowl
from lmfdb.WebNumberField import field_pretty, nf_display_knowl
from lmfdb.classical_modular_forms.web_newform import WebNewform, convert_newformlabel_from_conrey, encode_hecke_orbit
from lmfdb.classical_modular_forms.web_space import WebNewformSpace, WebGamma1Space, DimGrid, convert_spacelabel_from_conrey, get_bread, get_search_bread, get_dim_bread, OLDLABEL_RE as OLD_SPACE_LABEL_RE
from lmfdb.display_stats import StatsDisplay, boolean_unknown_format
from sage.databases.cremona import class_to_int, cremona_letter_code
from sage.all import next_prime

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
            name = field_pretty(nf_label)
            if name == nf_label and len(name) > 16:
                # truncate if too long
                parts = nf_label.split('.')
                parts[2] = 'N'
                name = '.'.join(parts)
            return nf_display_knowl(nf_label, name)
        else:
            poly = mf.get('field_poly')
            if poly:
                return polyquo_knowl(poly)
            return ""
    info["nf_link"] = nf_link
    def cm_link(mf):
        if mf['is_cm'] == -1:
            return "No"
        elif mf['is_cm'] == 0:
            return ""
        else:
            cm_label = "2.0.%s.1"%(-mf['cm_disc'])
            return '<a href="{0}"> {1} </a>'.format(url_for("number_fields.by_label", label=cm_label),
                                                    field_pretty(cm_label))
    info["cm_link"] = cm_link
    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series'}
    def display_AL(results):
        if not results:
            return False
        N = results[0]['level']
        if not all(mf['level'] == N for mf in results):
            return False
        return all(mf['char_order'] == 1 for mf in results)
    info["display_AL"] = display_AL

@cmf.route("/")
def index():
    if len(request.args) > 0:
        info = to_dict(request.args)
        if 'submit_again' in info:
            # We had to use submit_again because submit broke
            # the Next button for some reason.
            info['submit'] = info['submit_again']
        if info.get('submit') == 'Dimensions':
            for key in newform_only_fields:
                if key in info:
                    return dimension_form_search(info)
            return dimension_space_search(info)
        elif info.get('submit') == 'Spaces':
            return space_search(info)
        else:
            return newform_search(info)
    info = {"stats": CMF_stats()}
    newform_labels = ('1.12.a.a','11.2.a.a', '49.2.e.b')
    info["newform_list"] = [ {'label':label,'url':url_for_label(label)} for label in newform_labels ]
    space_labels = ('20.5','60.2','55.3.d')
    info["space_list"] = [ {'label':label,'url':url_for_label(label)} for label in space_labels ]
    info["weight_list"] = ('2', '3-4', '5-9', '10-50')
    info["level_list"] = ('1', '2-9', '10-99', '100-1000')
    bread = get_bread()
    return render_template("cmf_browse.html",
                           info=info,
                           credit=credit(),
                           title="Holomorphic Cusp Forms",
                           learnmore=learnmore_list(),
                           bread=get_bread())

@cmf.route("/random")
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
    info = to_dict(request.args)
    info['format'] = info.get('format','embed' if newform.dim>1 else 'satake')
    p, maxp = 2, 20
    if info['format'] in ['satake', 'satake_angle']:
        while p <= maxp:
            if newform.level % p == 0:
                maxp = next_prime(maxp)
            p = next_prime(p)
    info['n'] = info.get('n', '2-%s'%maxp)
    info['m'] = info.get('m', '1-20')
    errs = []
    try:
        info['CC_n'] = integer_options(info['n'], 1000)
    except (ValueError, TypeError):
        info['n'] = '2-20'
        info['CC_n'] = range(2,21)
        errs.append("<span style='color:black'>n</span> must be an integer, range of integers or comma separated list of integers (yielding at most 1000 possibilities)")
    try:
        info['CC_m'] = integer_options(info['m'], 1000)
    except (ValueError, TypeError):
        info['m'] = '1-20'
        info['CC_m'] = range(1,21)
        errs.append("<span style='color:black'>m</span> must be an integer, range of integers or comma separated list of integers (yielding at most 1000 possibilities)")
    try:
        info['prec'] = int(info.get('prec',6))
        if info['prec'] < 1 or info['prec'] > 15:
            raise ValueError
    except (ValueError, TypeError):
        info['prec'] = 6
        errs.append("<span style='color:black'>Precision</span> must be a positive integer, at most 15 (for higher precision, use the download button)")
    if errs:
        flash(Markup("<br>".join(errs)), "error")
    return render_template("cmf_newform.html",
                           info=info,
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
    return render_template("cmf_space.html",
                           info=info,
                           space=space,
                           properties2=space.properties,
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
    return render_template("cmf_full_gamma1_space.html",
                           info=info,
                           space=space,
                           properties2=space.properties,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@cmf.route("/<int:level>/")
def by_url_level(level):
    return newform_search({'level' : level})

@cmf.route("/<int:level>/<int:weight>/")
def by_url_full_gammma1_space_label(level, weight):
    label = str(level)+"."+str(weight)
    return render_full_gamma1_space_webpage(label)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/")
def by_url_space_label(level, weight, char_orbit_label):
    label = str(level)+"."+str(weight)+"."+char_orbit_label
    return render_space_webpage(label)

@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/")
def by_url_space_conreylabel(level, weight, conrey_label):
    label = convert_spacelabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label))
    return redirect(url_for_label(label), code=301)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit_label, hecke_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit_label+"."+hecke_orbit
    return render_newform_webpage(label)

@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/")
def by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit):
    label = convert_newformlabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label)+"."+hecke_orbit)
    return redirect(url_for_label(label), code=301)

@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/<int:embedding>/")
def by_url_newform_conreylabel_with_embedding(level, weight, conrey_label, hecke_orbit, embedding):
    assert embedding > 0
    return by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit)



def url_for_label(label):
    slabel = label.split(".")
    if len(slabel) == 4:
        return url_for(".by_url_newform_label", level=slabel[0], weight=slabel[1], char_orbit_label=slabel[2], hecke_orbit=slabel[3])
    elif len(slabel) == 3:
        return url_for(".by_url_space_label", level=slabel[0], weight=slabel[1], char_orbit_label=slabel[2])
    elif len(slabel) == 2:
        return url_for(".by_url_full_gammma1_space_label", level=slabel[0], weight=slabel[1])
    elif len(slabel) == 1:
        return url_for(".by_url_level", level=slabel[0])
    else:
        raise ValueError("Invalid label")

def _get_hecke_nf(label):
    try:
        code = encode_hecke_orbit(label)
    except ValueError:
        return abort(404, "Invalid label: %s"%label)
    eigenvals = db.mf_hecke_nf.search({'hecke_orbit_code':code}, ['n','an','trace_an'], sort=['n'])
    if not eigenvals:
        return abort(404, "No form found for %s"%(label))
    data = []
    for i, ev in enumerate(eigenvals):
        if ev['n'] != i+1:
            return abort(404, "Database error (please report): %s missing a(%s)"%(label, i+1))
        data.append((ev.get('an'),ev.get('trace_an')))
    return data

@cmf.route("/download_qexp/<label>")
def download_qexp(label):
    data = _get_hecke_nf(label)
    if not isinstance(data,list):
        return data
    dim = None
    qexp = []
    for an, trace_an in data:
        if not an:
            # only had traces
            return abort(404, "No q-expansion found for %s"%(label))
        if dim is None:
            dim = len(an)
            qexp.append([0] * dim)
        qexp.append(an)
    if dim == 1:
        s = Json.dumps([an[0] for an in qexp])
    else:
        # Spacing helps distingish different levels
        s = "[" + ", ".join("[" + ",".join(str(c) for c in an) + "]" for an in qexp) + "]"
    response = make_response(s)
    response.headers['Content-type'] = 'text/plain'
    return response

@cmf.route("/download_traces/<label>")
def download_traces(label):
    data = _get_hecke_nf(label)
    if not isinstance(data,list):
        return data
    qexp = [0] + [trace_an for an, trace_an in data]
    response = make_response(Json.dumps(qexp))
    response.headers['Context-type'] = 'text/plain'
    return response

def _get_hecke_cc(label):
    try:
        code = encode_hecke_orbit(label)
    except ValueError:
        return abort(404, "Invalid label: %s"%label)
    eigenvals = db.mf_hecke_cc.search({'hecke_orbit_code':code}, ['lfunction_label','embedding_root_real', 'embedding_root_imag', 'an', 'angles'])#, sort=['conrey_label','embedding_index'])
    if not eigenvals:
        return abort(404, "No form found for %s"%(label))
    return [(ev.get('lfunction_label'), [ev.get('embedding_root_real'), ev.get('embedding_root_imag')], ev.get('an'), ev.get('angles')) for ev in eigenvals]

@cmf.route("/download_cc_data/<label>")
def download_cc_data(label):
    data = _get_hecke_cc(label)
    if not isinstance(data,list):
        return data
    down = []
    for label, root, an, angles in data:
        D = {'label':label,
             'an':an}
        if root != [None,None]:
            D['root'] = root
        down.append(Json.dumps(D))
    response = make_response('\n\n'.join(down))
    response.headers['Content-type'] = 'text/plain'
    return response

@cmf.route("/download_satake_angles/<label>")
def download_satake_angles(label):
    data = _get_hecke_cc(label)
    if not isinstance(data,list):
        return data
    down = []
    for label, root, an, angles in data:
        D = {'label':label,
             'angles':angles}
        if root != [None,None]:
            D['root'] = root
        down.append(Json.dumps(D))
    response = make_response('\n\n'.join(down))
    response.headers['Content-type'] = 'text/plain'
    return response

@cmf.route("/download_newform/<label>")
def download_newform(label):
    data = db.mf_newforms.lookup(label)
    if data is None:
        return abort(404, "Label not found: %s"%label)
    cc_data = _get_hecke_cc(label)
    if not isinstance(cc_data, list):
        return cc_data
    embedding_list = []
    for label, root, an, angles in data:
        D = {'label': label,
             'an': an,
             'angles': angles}
        if root != [None, None]:
            D['root'] = root
        embedding_list.append(D)
    data['complex_embeddings'] = embedding_list
    nf_data = _get_hecke_nf(label)
    if not isinstance(nf_data, list):
        return nf_data
    qexp = [[0] * data['dim']]
    traces = [0]
    for an, trace_an in data:
        if an:
            qexp.append(an)
        traces.append(trace_an)
    if len(qexp) > 1:
        data['qexp'] = qexp
    data['traces'] = traces
    response = make_response(Json.dumps(data))
    response.headers['Content-type'] = 'text/plain'
    return response

def jump_box(info):
    jump = info["jump"].strip()
    if OLD_SPACE_LABEL_RE.match(jump):
        jump = convert_spacelabel_from_conrey(jump)
    try:
        return redirect(url_for_label(jump), 301)
    except ValueError:
        errmsg = "%s is not a valid newform or space label"
    flash_error (errmsg, jump)
    return redirect(url_for(".index"))

class CMF_download(Downloader):
    table = db.mf_newforms
    title = 'Cuspidal newforms'


@search_parser(default_name='Character orbit label') # see SearchParser.__call__ for actual arguments when calling
def parse_character(inp, query, qfield, level_field='level', conrey_field='char_labels'):
    pair = inp.split('.')
    if len(pair) != 2:
        raise ValueError("It must be of the form N.i")
    level, orbit = pair
    level = int(level)
    if level_field in query and query[level_field] != level:
        raise ValueError("Inconsistent level")
    query[level_field] = level
    if orbit.isalpha():
        query[qfield] = class_to_int(orbit) + 1 # we don't store the prim_orbit_label
    else:
        if conrey_field is None:
            raise ValueError("You must use the orbit label when searching by primitive character")
        query[conrey_field] = {'$contains': int(orbit)}

newform_only_fields = ['dim','nf_label','is_cm','cm_disc','is_twist_minimal','has_inner_twist','analytic_rank']
def common_parse(info, query):
    parse_ints(info, query, 'weight', name="Weight")
    if 'weight_parity' in info:
        parity=info['weight_parity']
        if parity == 'even':
            query['odd_weight'] = False
        elif parity == 'odd':
            query['odd_weight'] = True
    if 'char_parity' in info:
        parity=info['char_parity']
        if parity == 'even':
            query['char_parity'] = 1
        elif parity == 'odd':
            query['char_parity'] = -1
    parse_ints(info, query, 'level', name="Level")
    parse_character(info, query, 'char_label', qfield='char_orbit_index')
    parse_character(info, query, 'prim_label', qfield='prim_orbit_index', level_field='char_conductor', conrey_field=None)
    parse_ints(info, query, 'char_order', name="Character order")
    parse_bool(info, query, 'char_is_real', name="Character is real")

def newform_parse(info, query):
    common_parse(info, query)
    parse_ints(info, query, 'dim', name="Dimension")
    parse_nf_string(info, query,'nf_label', name="Coefficient field")
    parse_bool_unknown(info, query, 'is_cm',name='CM form')
    parse_ints(info, query, 'cm_disc', name="CM discriminant")
    parse_bool(info, query, 'is_twist_minimal')
    parse_bool_unknown(info, query, 'has_inner_twist')
    parse_ints(info, query, 'analytic_rank')

@search_wrap(template="cmf_newform_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':jump_box,
                        #'download_exact':download_exact,
                        #'download_complex':download_complex
             },
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def newform_search(info, query):
    newform_parse(info, query)
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
    return k > 1 and N*k*k <= 1000
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
            return url_for(".by_url_space_label", level=N, weight=k, char_orbit_label="a")
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

@search_wrap(template="cmf_dimension_search_results.html",
             table=db.mf_newforms,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_form_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list,
             credit=credit)
def dimension_form_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    newform_parse(info, query)

@search_wrap(template="cmf_dimension_search_results.html",
             table=db.mf_newspaces,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_space_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list,
             credit=credit)
def dimension_space_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    common_parse(info, query)

@search_wrap(template="cmf_space_search_results.html",
             table=db.mf_newspaces,
             title='Newform Space Search Results',
             err_title='Newform Space Search Input Error',
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def space_search(info, query):
    common_parse(info, query)
    parse_ints(info, query, 'dim', name='Dimension')
    parse_ints(info, query, 'num_forms', name='Number of newforms')
    set_info_funcs(info)

@cmf.route("/Completeness")
def completeness_page():
    t = 'Completeness of $\GL_2$ holomorphic newform data over $\Q$'
    return render_template("single.html", kid='dq.mf.elliptic.extent',
                           credit=credit(), title=t,
                           bread=get_bread(other='Completeness'),
                           learnmore=learnmore_list_remove('Completeness'))


@cmf.route("/Source")
def how_computed_page():
    t = 'Source of $\GL_2$ holomorphic newform data over $\Q$'
    return render_template("single.html", kid='dq.mf.elliptic.source',
                           credit=credit(), title=t,
                           bread=get_bread(other='Source'),
                           learnmore=learnmore_list_remove('Source'))

@cmf.route("/Labels")
def labels_page():
    t = 'Labels for $\GL_2$ holomorphic newforms over $\Q$'
    return render_template("single.html", kid='mf.elliptic.label',
                           credit=credit(), title=t,
                           bread=get_bread(other='Labels'),
                           learnmore=learnmore_list_remove('labels'))

def cm_format(D):
    if D == 1:
        return 'Not CM'
    elif D == 0:
        return 'Unknown'
    else:
        cm_label = "2.0.%s.1"%(-D)
        return nf_display_knowl(cm_label, field_pretty(cm_label))

class CMF_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for cuspidal newforms
    """
    def __init__(self):
        nforms = comma(db.mf_newforms.count())
        nspaces = comma(db.mf_newspaces.count())
        Nk2bound = 1000 # should be added to dq_extent table?
        weight_knowl = display_knowl('mf.elliptic.weight', title = 'weight')
        level_knowl = display_knowl('mf.elliptic.level', title='level')
        stats_url = url_for(".statistics")
        self.short_summary = r'The database currently contains %s newforms of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\). Here are some <a href="%s">further statistics</a>.' % (nforms, weight_knowl, level_knowl, Nk2bound, stats_url)
        self.summary = r"The database currently contains %s (Galois orbits of) newforms and %s spaces of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\)." % (nforms, nspaces, weight_knowl, level_knowl, Nk2bound)

    table = db.mf_newforms
    baseurl_func = ".index"

    stat_list = [
        {'cols': [],
         'buckets':{'dim':[1,1,2,3,4,5,10,20,100,1000,10000]},
         'row_title':'dimension',
         'knowl':'mf.elliptic.dimension'},
        {'cols': 'cm_disc',
         'top_title':'complex multiplication',
         'row_title':'CM by',
         'knowl':'mf.elliptic.cm_form',
         'reverse':True,
         'formatter':cm_format},
        {'cols':'has_inner_twist',
         'top_title':'inner twisting',
         'row_title':'has inner twist',
         'knowl':'mf.elliptic.inner_twist',
         'formatter':boolean_unknown_format},
        {'cols':'analytic_rank',
         'row_title':'analytic rank',
         'knowl':'lfunction.analytic_rank',
         'avg':True},
        {'cols':'num_forms',
         'table':db.mf_newspaces,
         'top_title': r'number of newforms in \(S_k(\Gamma_0(N), \chi)\)',
         'row_title': 'newforms',
         'knowl': 'mf.elliptic.galois-orbits',
         'url_extras': 'submit=Spaces&'},
    ]

@cmf.route("/stats")
def statistics():
    title = 'Cupsidal Newforms: Statistics'
    return render_template("display_stats.html", info=CMF_stats(), credit=credit(), title=title, bread=get_bread(other='Statistics'), learnmore=learnmore_list())
