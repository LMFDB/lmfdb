from flask import render_template, url_for, redirect, abort, request, flash
from markupsafe import Markup
from collections import defaultdict
from lmfdb.db_backend import db
from lmfdb.classical_modular_forms import cmf
from lmfdb.search_parsing import parse_ints, parse_floats, parse_bool,\
        parse_primes, parse_nf_string, parse_noop, parse_equality_constraints,\
        integer_options, search_parser, parse_subset
from lmfdb.search_wrapper import search_wrap
from lmfdb.utils import flash_error, to_dict, comma, display_knowl, bigint_knowl
from lmfdb.classical_modular_forms.web_newform import WebNewform, convert_newformlabel_from_conrey,  quad_field_knowl, cyc_display, field_display_gen
from lmfdb.classical_modular_forms.web_space import WebNewformSpace, WebGamma1Space, DimGrid, convert_spacelabel_from_conrey, get_bread, get_search_bread, get_dim_bread, newform_search_link, ALdim_table, OLDLABEL_RE as OLD_SPACE_LABEL_RE
from lmfdb.classical_modular_forms.download import CMF_download
from lmfdb.display_stats import StatsDisplay, per_row_total, per_col_total, sum_totaler
from sage.databases.cremona import class_to_int
from sage.all import ZZ, next_prime, cartesian_product_iterator, cached_function
import re

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Classical modular form labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def credit():
    return "Alex J Best, Jonathan Bober, Andrew Booker, Edgar Costa, John Cremona, David Roe, Andrew Sutherland, John Voight"

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

def ALdims_knowl(al_dims, level, weight):
    dim_dict = {}
    for vec, dim, cnt in al_dims:
        dim_dict[tuple(ev for (p, ev) in vec)] = dim
    short = "+".join(r'\(%s\)'%dim_dict.get(vec,0) for vec in cartesian_product_iterator([[1,-1] for _ in range(len(al_dims[0][0]))]))
    # We erase plus_dim and minus_dim if they're obvious
    AL_table = ALdim_table(al_dims, level, weight)
    return r'<a title="[ALdims]" knowl="dynamic_show" kwargs="%s">%s</a>'%(AL_table, short)

def set_info_funcs(info):
    info["mf_url"] = lambda mf: url_for_label(mf['label'])
    def nf_link(mf):
        m = mf.get('field_poly_root_of_unity')
        d = mf.get('dim')
        if m and d != 2:
            return cyc_display(m, d, mf.get('field_poly_is_real_cyclotomic'))
        else:
            return field_display_gen(mf.get('nf_label'), mf.get('field_poly'), mf.get('field_disc'), truncate=16)

    info["nf_link"] = nf_link

    def quad_links(mf, is_field, disc_field, bound = None):
        if mf[is_field]:
            discs = mf[disc_field]
            if bound:
                discs = discs[:bound]
            return ', '.join( map(quad_field_knowl, discs) )
        else:
            return "No"
    info["self_twist_link"] = lambda mf: quad_links(mf, 'is_self_twist', 'self_twist_discs', bound = 1)
    info["cm_link"] = lambda mf: quad_links(mf, 'is_cm', 'cm_discs')
    info["rm_link"] = lambda mf: quad_links(mf, 'is_rm', 'rm_discs')
    info["cm_col"] = info.get('cm_discs') is not None or 'cm' in  info.get('has_self_twist', '')
    info["rm_col"] = info.get('rm_discs') is not None or 'rm' in  info.get('has_self_twist', '')
    info["self_twist_col"] = not (info["cm_col"] or info["rm_col"])


    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series'}
    def display_AL(results):
        if not results:
            return False
        N = results[0]['level']
        if not all(mf['level'] == N for mf in results):
            return False
        if N == 1:
            return False
        return all(mf['char_order'] == 1 for mf in results)
    info["display_AL"] = display_AL

    def display_Fricke(results):
        # only called if display_AL has returned False
        return any(mf['char_order'] == 1 for mf in results)
    info["display_Fricke"] = display_Fricke

    def all_weight1(results):
        return all(mf.get('weight') == 1 for mf in results)
    info["all_weight1"] = all_weight1

    def all_D2(results):
        return all(mf.get('projective_image') == 'D2' for mf in results)
    info["all_D2"] = all_D2


    # assumes the format Dn A4 S4 S5
    info["display_projective_image"] = lambda mf: ('%s_{%s}' % (mf['projective_image'][:1], mf['projective_image'][1:])) if 'projective_image' in mf else ''

    # For spaces
    def display_decomp(space):
        hecke_orbit_dims = space.get('hecke_orbit_dims')
        if hecke_orbit_dims is None: # shouldn't happen
            return 'unknown'
        dim_dict = defaultdict(int)
        terms = []
        for dim in hecke_orbit_dims:
            dim_dict[dim] += 1
        for dim in sorted(dim_dict.keys()):
            count = dim_dict[dim]
            query = {'weight':space['weight'],
                     'char_label':'%s.%s'%(space['level'],space['char_orbit_label']),
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
    info['display_decomp'] = display_decomp

    info['show_ALdims_col'] = lambda spaces: any('AL_dims' in space for space in spaces)
    def display_ALdims(space):
        al_dims = space.get('AL_dims')
        if al_dims:
            return ALdims_knowl(al_dims, space['level'], space['weight'])
        else:
            return ''
    info['display_ALdims'] = display_ALdims

    info['download_spaces'] = lambda results: any(space['dim'] > 1 for space in results)
    info['bigint_knowl'] = bigint_knowl


favorite_newform_labels = [[('23.1.b.a','Smallest analytic conductor'),
                            ('11.2.a.a','First weight 2 form'),
                            ('39.1.d.a','First D2 form'),
                            ('7.3.b.a','First CM-form with weight at least 2'),
                            ('23.2.a.a','First trivial-character non-rational form'),
                            ('1.12.a.a','Delta')],
                           [('124.1.i.a','First non-dihedral weight 1 form'),
                            ('148.1.f.a','First S4 form'),
                            ('633.1.m.b','First A5 form'),
                            ('163.3.b.a','Best q-expansion'),
                            ('8.14.b.a','Large weight, non-self dual, analytic rank 1'),
                            ('8.21.d.b','Large coefficient ring index'),
                            ('3600.1.e.a','Many zeros in q-expansion'),
                            ('983.2.c.a','Large dimension'),
                            ('3997.1.cz.a','Largest projective image')]]
favorite_space_labels = [[('1161.1.i', 'Has A5, S4, D3 forms'),
                          ('23.10', 'Mile high 11s'),
                          ('3311.1.h', 'Most weight 1 forms'),
                          ('1200.2.a', 'All forms rational'),
                          ('9450.2.a','Most newforms'),
                          ('4000.1.bf', 'Two large A5 forms')]]

@cmf.route("/")
def index():
    if len(request.args) > 0:
        info = to_dict(request.args)
        # hidden_search_type for prev/next buttons
        info['search_type'] = search_type = info.get('search_type', info.get('hidden_search_type', 'List'))

        if search_type == 'Dimensions':
            # We have to handle dim separately since we want to allow it as a parameter
            # for Space searches, but it doesn't make to display a dimension grid
            # with constrained dimension
            for key in newform_only_fields.keys() + ['dim']:
                if key in info:
                    return dimension_form_search(info)
            return dimension_space_search(info)
        elif search_type == 'Spaces':
            return space_search(info)
        elif search_type == 'Traces':
            return trace_search(info)
        elif search_type == 'Random':
            return newform_search(info, random=True)
        elif search_type == 'List':
            return newform_search(info)
        assert False
    info = {"stats": CMF_stats()}
    info["newform_list"] = [[{'label':label,'url':url_for_label(label),'reason':reason} for label, reason in sublist] for sublist in favorite_newform_labels]
    info["space_list"] = [[{'label':label,'url':url_for_label(label),'reason':reason} for label, reason in sublist] for sublist in favorite_space_labels]
    info["weight_list"] = ('1', '2', '3', '4', '5-8', '9-16', '17-32', '33-64', '65-%d' % weight_bound() )
    info["level_list"] = ('1', '2-10', '11-100', '101-1000', '1001-2000', '2001-4000', '4001-6000', '6001-8000', '8001-%d' % level_bound() )
    return render_template("cmf_browse.html",
                           info=info,
                           credit=credit(),
                           title="Classical Modular Forms",
                           learnmore=learnmore_list(),
                           bread=get_bread())

@cmf.route("/random")
def random_form():
    if len(request.args) > 0:
        info = to_dict(request.args)
        return newform_search(info, random=True)
    else:
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
    info['format'] = info.get('format', 'embed' if newform.dim > 1 else 'satake')
    p, maxp = 2, 10
    if info['format'] in ['satake', 'satake_angle']:
        while p <= maxp:
            if newform.level % p == 0:
                maxp = next_prime(maxp)
            p = next_prime(p)
    errs = []
    info['n'] = info.get('n', '2-%s'%maxp)
    try:
        info['CC_n'] = integer_options(info['n'], 1000)
    except (ValueError, TypeError) as err:
        info['n'] = '2-%s'%maxp
        info['CC_n'] = range(2,maxp+1)
        if err.args and err.args[0] == 'Too many options':
            errs.append(r"Only \(a_n\) up to %s are available"%(newform.cqexp_prec-1))
        else:
            errs.append("<span style='color:black'>n</span> must be an integer, range of integers or comma separated list of integers")
    maxm = min(newform.dim, 20)
    info['m'] = infom = info.get('m', '1-%s'%maxm)
    try:
        if '.' in infom:
            # replace embedding codes with the corresponding integers
            infom = re.sub(r'\d+\.\d+', newform.embedding_from_conrey, infom)
        info['CC_m'] = integer_options(infom, 1000)
    except (ValueError, TypeError) as err:
        info['m'] = '1-%s'%maxm
        info['CC_m'] = range(1,maxm+1)
        if err.args and err.args[0] == 'Too many options':
            errs.append('Web interface only supports 1000 embeddings at a time.  Use download link to get more (may take some time).')
        else:
            errs.append("<span style='color:black'>Embeddings</span> must consist of integers or embedding codes")
    try:
        info['prec'] = int(info.get('prec',6))
        if info['prec'] < 1 or info['prec'] > 15:
            raise ValueError
    except (ValueError, TypeError):
        info['prec'] = 6
        errs.append("<span style='color:black'>Precision</span> must be a positive integer, at most 15 (for higher precision, use the download button)")
    newform.setup_cc_data(info)
    if newform.cqexp_prec != 0 and max(info['CC_n']) >= newform.cqexp_prec:
        errs.append(r"Only \(a_n\) up to %s are available"%(newform.cqexp_prec-1))
    if errs:
        flash(Markup("<br>".join(errs)), "error")
    return render_template("cmf_newform.html",
                           info=info,
                           newform=newform,
                           properties2=newform.properties,
                           downloads=newform.downloads,
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
                           downloads=space.downloads,
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
                           downloads=space.downloads,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@cmf.route("/<level>/")
def by_url_level(level):
    if "." in level:
        return redirect(url_for_label(label = level), code=301)
    info = to_dict(request.args)
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
@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/")
def by_url_space_conreylabel(level, weight, conrey_label):
    label = convert_spacelabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label))
    return redirect(url_for_label(label), code=301)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit_label, hecke_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit_label+"."+hecke_orbit
    return render_newform_webpage(label)

# Backward compatibility from before 2018
@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/")
def by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit):
    label = convert_newformlabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label)+"."+hecke_orbit)
    return redirect(url_for_label(label), code=301)

# From L-functions
@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<int:conrey_label>/<int:embedding>/")
def by_url_newform_conreylabel_with_embedding(level, weight, char_orbit_label, hecke_orbit, conrey_label, embedding):
    assert conrey_label > 0
    assert embedding > 0
    label = str(level)+"."+str(weight)+"."+char_orbit_label+"."+hecke_orbit
    return redirect(url_for_label(label), code=301)




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

def jump_box(info):
    jump = info.pop("jump").strip()
    errmsg = None
    if OLD_SPACE_LABEL_RE.match(jump):
        jump = convert_spacelabel_from_conrey(jump)
    #handle direct trace_hash search
    if re.match(r'^\#\d+$',jump) and long(jump[1:]) < 2**61:
        label = db.mf_newforms.lucky({'trace_hash': long(jump[1:].strip())}, projection="label")
        if label:
            return redirect(url_for_label(label), 301)
        else:
            errmsg = "hash %s not found"
    elif jump == 'yes':
        query = {}
        newform_parse(info, query)
        jump = db.mf_newforms.lucky(query, 'label')
        if jump is None:
            errmsg = "There are no newforms specified by the query %s"
            jump = query
    if errmsg is None:
        try:
            return redirect(url_for_label(jump), 301)
        except ValueError:
            errmsg = "%s is not a valid newform or space label"
    flash_error (errmsg, jump)
    return redirect(url_for(".index"))


@cmf.route("/download_qexp/<label>")
def download_qexp(label):
    return CMF_download().download_qexp(label, lang='sage')

@cmf.route("/download_traces/<label>")
def download_traces(label):
    return CMF_download().download_traces(label)

@cmf.route("/download_cc_data/<label>")
def download_cc_data(label):
    return CMF_download().download_cc_data(label)

@cmf.route("/download_satake_angles/<label>")
def download_satake_angles(label):
    return CMF_download().download_satake_angles(label)

@cmf.route("/download_newform_to_magma/<label>")
def download_newform_to_magma(label):
    return CMF_download().download_newform_to_magma(label)

@cmf.route("/download_newform/<label>")
def download_newform(label):
    return CMF_download().download_newform(label)

@cmf.route("/download_newspace/<label>")
def download_newspace(label):
    return CMF_download().download_newspace(label)

@cmf.route("/download_full_space/<label>")
def download_full_space(label):
    return CMF_download().download_full_space(label)

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

newform_only_fields = {
    'nf_label': 'Coefficient field',
    'is_self_twist': 'Has self twist',
    'cm_discs': 'CM discriminant',
    'rm_discs': 'RM discriminant',
    'inner_twist_count': 'Inner twist count',
    'analytic_rank': 'Analytic rank',
    'has_self_twist': 'Has self-twist',
    'is_self_dual': 'Is self dual',
}
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
    parse_floats(info, query, 'analytic_conductor', name="Analytic conductor")
    parse_ints(info, query, 'Nk2', name=r"\(Nk^2\)")
    parse_character(info, query, 'char_label', qfield='char_orbit_index')
    parse_character(info, query, 'prim_label', qfield='prim_orbit_index', level_field='char_conductor', conrey_field=None)
    parse_ints(info, query, 'char_order', name="Character order")
    prime_mode = info['prime_quantifier'] = info.get('prime_quantifier', 'exact')
    parse_primes(info, query, 'level_primes', name='Primes dividing level', mode=prime_mode, radical='level_radical')

def parse_self_twist(info, query):
    # self_twist_values = [('', 'unrestricted'), ('yes', 'has self-twist'), ('cm', 'has CM'), ('rm', 'has RM'), ('cm_and_rm', 'has CM and RM'), ('no', 'no self-twists') ]
    inp = info.get('has_self_twist')
    if inp:
        if inp in ['no', 'yes']:
            info['is_self_twist'] = inp
            parse_bool(info, query, 'is_self_twist', name='Has self-twist')
        else:
            if 'cm' in inp:
                info['is_cm'] = 'yes'
            if 'rm' in inp:
                info['is_rm'] = 'yes'
            parse_bool(info, query, 'is_cm', name='Has self-twist')
            parse_bool(info, query, 'is_rm', name='Has self-twist')

def parse_discriminant(d, sign = 0):
    d = int(d)
    if d*sign < 0:
        raise ValueError('%d %s 0' % (d, '<' if sign > 0 else '>'))
    if (d % 4) not in [0, 1]:
        raise ValueError('%d != 0 or 1 mod 4' % d)
    return d


def newform_parse(info, query):
    common_parse(info, query)
    parse_ints(info, query, 'dim', name="Dimension")
    parse_nf_string(info, query,'nf_label', name="Coefficient field")
    parse_self_twist(info, query)
    parse_subset(info, query, 'self_twist_discs', name="CM/RM discriminant", parse_singleton=lambda d: parse_discriminant(d))
    parse_bool(info, query, 'is_twist_minimal')
    parse_ints(info, query, 'inner_twist_count')
    parse_ints(info, query, 'analytic_rank')
    parse_noop(info, query, 'atkin_lehner_string')
    parse_ints(info, query, 'fricke_eigenval')
    parse_bool(info, query, 'is_self_dual')
    parse_noop(info, query, 'projective_image')
    parse_noop(info, query, 'projective_image_type')
    parse_ints(info, query, 'artin_degree', name="Artin degree")

@search_wrap(template="cmf_newform_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download(),
                        #'download_exact':download_exact,
                        #'download_complex':download_complex
             },
             projection=['label', 'level', 'weight', 'dim', 'analytic_conductor', 'trace_display', 'atkin_lehner_eigenvals', 'qexp_display', 'char_order', 'hecke_orbit_code', 'projective_image', 'field_poly', 'nf_label', 'is_cm', 'is_rm', 'cm_discs', 'rm_discs', 'field_poly_root_of_unity', 'field_poly_is_real_cyclotomic', 'field_disc', 'fricke_eigenval', 'is_self_twist', 'self_twist_discs'],
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def newform_search(info, query):
    newform_parse(info, query)
    set_info_funcs(info)

def trace_postprocess(res, info, query):
    if res:
        hecke_codes = [mf['hecke_orbit_code'] for mf in res]
        trace_dict = defaultdict(dict)
        for rec in db.mf_hecke_traces.search({'n':{'$in': info['Tr_n']}, 'hecke_orbit_code':{'$in':hecke_codes}}, projection=['hecke_orbit_code', 'n', 'trace_an'], sort=[]):
            trace_dict[rec['hecke_orbit_code']][rec['n']] = rec['trace_an']
        for mf in res:
            mf['tr_an'] = trace_dict[mf['hecke_orbit_code']]
    return res

@search_wrap(template="cmf_trace_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download().download_multiple_traces},
             projection=['label', 'dim', 'hecke_orbit_code', 'weight'],
             postprocess=trace_postprocess,
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def trace_search(info, query):
    newform_parse(info, query)
    parse_equality_constraints(info, query, 'an_constraints', qfield='traces', shift=-1)
    set_info_funcs(info)
    ns = info['n'] = info.get('n', '1-40')
    n_primality = info['n_primality'] = info.get('n_primality', 'primes')
    Trn = integer_options(ns, 1000)
    if n_primality == 'primes':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime()]
    elif n_primality == 'prime_powers':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime_power()]
    else:
        Trn = [n for n in Trn if n > 1]
    info['Tr_n'] = Trn

def set_rows_cols(info, query):
    """
    Sets weight_list and level_list, which are the row and column headers
    """
    try:
        info['weight_list'] = integer_options(info['weight'], max_opts=200)
    except ValueError:
        raise ValueError("Table too large: at most 200 options for weight")
    if 'odd_weight' in query:
        if query['odd_weight']:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 1]
        else:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 0]
    try:
        info['level_list'] = integer_options(info['level'], max_opts=1000)
    except ValueError:
        raise ValueError("Table too large: at most 1000 options for level")
    if len(info['weight_list']) * len(info['level_list']) > 10000:
        raise ValueError("Table too large: must have at most 5000 entries")

def has_data_nontriv(N, k):
    return N*k*k <= Nk2_bound(nontriv=True)
def has_data(N, k):
    return N*k*k <= Nk2_bound()
def has_data_mixed(N, k):
    if k == 1:
        return N <= Nk2_bound(nontriv=True)
    else:
        return has_data(N, k)

def dimension_space_postprocess(res, info, query):
    set_rows_cols(info, query)
    hasdata = has_data_mixed
    dim_dict = {(N,k):DimGrid() for N in info['level_list'] for k in info['weight_list'] if hasdata(N,k)}
    for space in res:
        dims = DimGrid.from_db(space)
        N = space['level']
        k = space['weight']
        if hasdata(N, k):
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
    info['cusp_types'] = ['M', 'S', 'E']
    info['newness_types'] = ['all', 'new', 'old']
    info['one_type'] = False
    info['switch_text'] = switch_text
    info['url_generator'] = url_generator
    info['has_data'] = hasdata
    return dim_dict

def dimension_form_postprocess(res, info, query):
    urlgen_info = dict(info)
    urlgen_info['search_type'] = ''
    urlgen_info['count'] = 50
    set_rows_cols(info, query)
    if query.get('char_order') == 1 or query.get('char_conductor') == 1:
        hasdata = has_data
    else:
        hasdata = has_data_nontriv
    dim_dict = {(N,k):0 for N in info['level_list'] for k in info['weight_list'] if hasdata(N,k)}
    for form in res:
        N = form['level']
        k = form['weight']
        if hasdata(N,k):
            dim_dict[N,k] += form['dim']
    def url_generator(N, k):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'List'
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
    info['has_data'] = hasdata
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
             shortcuts={'download':CMF_download().download_spaces},
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def space_search(info, query):
    for key, display in newform_only_fields.items():
        if key in info:
            msg = "%s not valid when searching for spaces" % display
            flash_error(msg)
            raise ValueError(msg)
    common_parse(info, query)
    if not info.get('dim', '').strip():
        # Only show non-empty spaces
        info['dim'] = '1-'
    parse_ints(info, query, 'dim', name='Dimension')
    parse_ints(info, query, 'num_forms', name='Number of newforms')
    if info.get('all_spaces') == 'yes' and 'num_forms' in query:
        msg = "Cannot specify number of newforms while requesting all spaces"
        flash_error(msg)
        raise ValueError(msg)
    if 'num_forms' not in query and info.get('all_spaces') != 'yes':
        # Don't show spaces that only include dimension data but no newforms (Nk2 > 4000, nontrivial character)
        query['num_forms'] = {'$exists':True}
    set_info_funcs(info)

@cmf.route("/Completeness")
def completeness_page():
    t = 'Completeness of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.extent',
                           credit=credit(), title=t,
                           bread=get_bread(other='Completeness'),
                           learnmore=learnmore_list_remove('Completeness'))


@cmf.route("/Source")
def how_computed_page():
    t = 'Source of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.source',
                           credit=credit(), title=t,
                           bread=get_bread(other='Source'),
                           learnmore=learnmore_list_remove('Source'))

@cmf.route("/Labels")
def labels_page():
    t = 'Labels for classical modular forms'
    return render_template("single.html", kid='mf.elliptic.label',
                           credit=credit(), title=t,
                           bread=get_bread(other='Labels'),
                           learnmore=learnmore_list_remove('labels'))

@cmf.route("/Reliability")
def reliability_page():
    t = 'Reliability of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.reliability',
                           credit=credit(), title=t,
                           bread=get_bread(other='Reliability'),
                           learnmore=learnmore_list_remove('Reliability'))


def projective_image_sort_key(im_type):
    if im_type == 'A4':
        return -3
    elif im_type == 'S4':
        return -2
    elif im_type == 'A5':
        return -1
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

def self_twist_type_query_formatter(x):
    if x in [0, 'neither']:
        return 'has_self_twist=no'
    elif x in [1, 'CM only']:
        return 'has_self_twist=cm'
    elif x in [2, 'RM only']:
        return 'has_self_twist=rm'
    elif x in [3, 'both']:
        return 'has_self_twist=cm_and_rm'

def level_primes_formatter(x):
    subset = x.get('$containedin')
    if subset:
        return 'level_primes=%s&prime_quantifier=subsets' % (','.join(map(str, subset)))
    supset = x.get('$contains')
    if supset:
        return 'level_primes=%s&prime_quantifier=append' % (','.join(map(str, supset)))
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
        self.nspaces = comma(db.mf_newspaces.count({'num_forms':{'$exists':True}}))
        self.ndim = comma(db.mf_hecke_cc.count())
        self.weight_knowl = display_knowl('mf.elliptic.weight', title='weight')
        self.level_knowl = display_knowl('mf.elliptic.level', title='level')
        self.newform_knowl = display_knowl('mf.elliptic.newform', title='newforms')
        #stats_url = url_for(".statistics")

    @property
    def short_summary(self):
        return r'The database currently contains %s (Galois orbits of) %s of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\), corresponding to %s modular forms over the complex numbers.' % (self.nforms, self.newform_knowl, self.weight_knowl, self.level_knowl, Nk2_bound(), self.ndim)

    @property
    def summary(self):
        return r"The database currently contains %s (Galois orbits of) %s and %s spaces of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\), corresponding to %s modular forms over the complex numbers.  In addition to the statistics below, you can also <a href='%s'>create your own</a>." % (self.nforms, self.newform_knowl, self.nspaces, self.weight_knowl, self.level_knowl, Nk2_bound(), self.ndim, url_for(".dynamic_statistics"))

    table = db.mf_newforms
    baseurl_func = ".index"
    buckets = {'level':['1','2-10','11-100','101-1000','1001-2000', '2001-4000','4001-6000','6001-8000','8001-10000'],
               'weight':['1','2','3','4','5-8','9-16','17-32','33-64','65-200'],
               'dim':['1','2','3','4','5-10','11-20','21-100','101-1000','1001-10000','10001-100000'],
               'char_order':['1','2','3','4','5','6-10','11-20','21-100','101-1000']}
    reverses = {'cm_discs': True}
    sort_keys = {'projective_image': projective_image_sort_key}
    knowls = {'level': 'mf.elliptic.level',
              'weight': 'mf.elliptic.weight',
              'dim': 'mf.elliptic.dimension',
              'char_order': 'character.dirichlet.order',
              'analytic_rank': 'mf.elliptic.analytic_rank',
              'projective_image': 'mf.elliptic.projective_image',
              'num_forms': 'mf.elliptic.galois-orbits',
              'inner_twist_count': 'mf.elliptic.inner_twist',
              'self_twist_type': 'mf.elliptic.self_twist',
              'cm_discs': 'mf.elliptic.cm_form',
              'rm_discs': 'mf.elliptic.rm_form'}
    top_titles = {'dim': 'dimension',
                  'inner_twist_count': 'inner twists',
                  'cm_discs': 'complex multiplication',
                  'rm_discs': 'real multiplication'}
    row_titles = {'char_order': 'character order',
                  'num_forms': 'newforms',
                  'inner_twist_count': 'inner twists',
                  'cm_discs': 'CM disc',
                  'rm_discs': 'RM disc'}
    formatters = {'projective_image': (lambda t: r'\(%s_{%s}\)' % (t[0], t[1:])),
                  'char_parity': (lambda t: 'odd' if t in [-1,'-1'] else 'even'),
                  'inner_twist_count': (lambda x: ('Unknown' if x == -1 else str(x))),
                  'self_twist_type': self_twist_type_formatter}
    query_formatters = {'projective_image': (lambda t: r'projective_image=%s' % (t,)),
                        'self_twist_type': self_twist_type_query_formatter,
                        'inner_twist_count': (lambda x: 'inner_twist_count={0}'.format(x if x != 'Unknown' else '-1')),
                        'level_primes': level_primes_formatter,
                        'level_radical': level_radical_formatter}
    split_lists = {'cm_discs': True,
                   'rm_discs': True}
    stat_list = [
        {'cols': ['level', 'weight'],
         'proportioner': per_col_total,
         'totaler': sum_totaler(),
         'corner_label':r'\(N \backslash k\)'},
        {'cols': ['level', 'dim'],
         'proportioner': per_row_total,
         'totaler': sum_totaler(),
         'corner_label':r'\(N \backslash d\)',
        },
        {'cols':'char_order'},
        {'cols':'analytic_rank',
         'top_title':[('analytic ranks', 'mf.elliptic.analytic_rank'),
                      ('for forms of weight greater than 1', None)],
         'totaler':{'avg':True}},
        {'cols':'projective_image',
         'top_title':[('projective images', 'mf.elliptic.projective_image'),
                      ('for weight 1 forms', None)]},
        {'cols':'num_forms',
         'table':db.mf_newspaces,
         'top_title': [('number of newforms', 'mf.elliptic.galois-orbits'), (r'in \(S_k(N, \chi)\)', None)],
         'url_extras': 'search_type=Spaces&'},
        {'cols':'inner_twist_count'},
        {'cols':['self_twist_type', 'weight'],
         'title_joiner': ' by ',
         'proportioner': per_col_total,
         'totaler': sum_totaler(col_counts=False, corner_count=False),
         'corner_label':'weight'},
        {'cols': 'cm_discs',
         'totaler':{}},
        {'cols': 'rm_discs',
         'totaler':{}},
    ]
    # Used for dynamic stats
    dynamic_parse = staticmethod(newform_parse)
    dynamic_parent_page = "cmf_refine_search.html"
    dynamic_cols = [
        ('level','Level'),
        ('weight','Weight'),
        ('dim','Dimension'),
        ('analytic_conductor','Analytic conductor'),
        ('char_order','Character order'),
        ('self_twist_type','Self twist type'),
        ('inner_twist_count','Num inner twists'),
        ('analytic_rank','Analytic rank'),
        ('char_parity','Character parity'),
        ('projective_image','Projective image'),
        ('projective_image_type','Projective image type'),
        ('artin_degree','Artin degree'),
    ]


@cmf.route("/stats")
def statistics():
    title = 'Cuspidal Newforms: Statistics'
    return render_template("display_stats.html", info=CMF_stats(), credit=credit(), title=title, bread=get_bread(other='Statistics'), learnmore=learnmore_list())

@cmf.route("/dynamic_stats")
def dynamic_statistics():
    if len(request.args) > 0:
        info = to_dict(request.args)
    else:
        info = {}
    CMF_stats().dynamic_setup(info)
    title = 'Cuspidal Newforms: Dynamic Statistics'
    return render_template("dynamic_stats.html", info=info, credit=credit(), title=title, bread=get_bread(other='Dynamic Statistics'), learnmore=learnmore_list())
