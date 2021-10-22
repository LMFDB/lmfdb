# -*- coding: utf-8 -*-
import ast
import os
import re
from io import BytesIO
import time

from flask import render_template, url_for, request, redirect, make_response, send_file, abort
from sage.all import ZZ, QQ, Qp, RealField, EllipticCurve, cputime
from sage.databases.cremona import parse_cremona_label, class_to_int

from lmfdb import db
from lmfdb.app import app
from lmfdb.backend.encoding import Json
from lmfdb.utils import (
    web_latex, to_dict, comma, flash_error, display_knowl, raw_typeset,
    parse_rational_to_list, parse_ints, parse_floats, parse_bracketed_posints, parse_primes,
    SearchArray, TextBox, SelectBox, SubsetBox, TextBoxWithSelect, CountBox,
    StatsDisplay, parse_element_of, parse_bool, parse_signed_ints, search_wrap, redirect_no_cache)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.isog_class import ECisog_class
from lmfdb.elliptic_curves.web_ec import WebEC, match_lmfdb_label, match_cremona_label, split_lmfdb_label, split_cremona_label, weierstrass_eqn_regex, short_weierstrass_eqn_regex, class_lmfdb_label, curve_lmfdb_label, EC_ainvs, latex_sha, gl2_subgroup_data, CREMONA_BOUND
from sage.misc.cachefunc import cached_method
from lmfdb.ecnf.ecnf_stats import latex_tor
from .congruent_numbers import get_congruent_number_data, congruent_number_data_directory

q = ZZ['x'].gen()
the_ECstats = None

#########################
#   Utility functions
#########################

def sorting_label(lab1):
    """
    Provide a sorting key.
    """
    a, b, c = parse_cremona_label(lab1)
    return (int(a), class_to_int(b), int(c))

def get_bread(tail=[]):
    base = [('Elliptic curves', url_for("ecnf.index")), (r'$\Q$', url_for(".rational_elliptic_curves"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def get_stats():
    global the_ECstats
    if the_ECstats is None:
        the_ECstats = ECstats()
    return the_ECstats

#########################
#    Top level
#########################

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Elliptic curve labels', url_for(".labels_page")),
            ('Congruent number curves', url_for(".render_congruent_number_data"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


#########################
#  Search/navigate
#########################

@ec_page.route("/")
def rational_elliptic_curves(err_args=None):
    info = to_dict(request.args, search_array=ECSearchArray())
    if err_args is None:
        if request.args:
            return elliptic_curve_search(info)
        else:
            err_args = {}
            for field in ['conductor', 'jinv', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure', 'msg']:
                err_args[field] = ''
            err_args['count'] = '50'

    counts = get_stats()

    conductor_list_endpoints = [1, 100, 1000, 10000, 100000, int(counts.max_N_Cremona) + 1]
    conductor_list = dict([(r,r) for r in ["%s-%s" % (start, end - 1) for start, end in zip(conductor_list_endpoints[:-1],
                                                                                            conductor_list_endpoints[1:])]])
    conductor_list[">{}".format(counts.max_N_Cremona)] = "{}-".format(counts.max_N_Cremona)

    rank_list = list(range(counts.max_rank + 1))
    torsion_list = list(range(1, 11)) + [12, 16]
    info['rank_list'] = rank_list
    info['torsion_list'] = torsion_list
    info['conductor_list'] = conductor_list
    info['stats'] = ECstats()
    info['stats_url'] = url_for(".statistics")

    t = r'Elliptic curves over $\Q$'
    if err_args.get("err_msg"):
        # this comes from elliptic_curve_jump_error
        flash_error(err_args.pop("err_msg"), err_args.pop("label"))
        return redirect(url_for(".rational_elliptic_curves"))
    return render_template("ec-index.html",
                           info=info,
                           title=t,
                           bread=get_bread(),
                           learnmore=learnmore_list(),
                           calling_function="ec.rational_elliptic_curves",
                           **err_args)

@ec_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "ec.q",
        db.ec_curvedata,
        url_for_label,
        label_col="lmfdb_label",
        title=r"Some interesting elliptic curves over $\Q$",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@ec_page.route("/random")
@redirect_no_cache
def random_curve():
    label = db.ec_curvedata.random(projection = 'lmfdb_label')
    cond, iso, num = split_lmfdb_label(label)
    return url_for(".by_triple_label", conductor=cond, iso_label=iso, number=num)

@ec_page.route("/curve_of_the_day")
@redirect_no_cache # disables cache on todays curve
def todays_curve():
    from datetime import date
    mordells_birthday = date(1888,1,28)
    n = (date.today()-mordells_birthday).days
    label = db.ec_curvedata.lucky(projection='lmfdb_label', offset = n)
    return url_for(".by_ec_label", label=label)

################################################################################
# Statistics
################################################################################

class ECstats(StatsDisplay):
    """
    Class for creating and displaying statistics for elliptic curves over Q
    """

    def __init__(self):
        self.ncurves = db.ec_curvedata.count()
        self.ncurves_c = comma(self.ncurves)
        self.nclasses = db.ec_classdata.count()
        self.nclasses_c = comma(self.nclasses)
        self.max_N_Cremona = 500000
        self.max_N_Cremona_c = comma(self.max_N_Cremona)
        self.max_N = db.ec_curvedata.max('conductor')
        self.max_N_c = comma(self.max_N)
        self.max_N_prime = 1000000
        self.max_N_prime_c = comma(self.max_N_prime)
        self.max_rank = db.ec_curvedata.max('rank')
        self.max_rank_c = comma(self.max_rank)
        self.cond_knowl = display_knowl('ec.q.conductor', title = "conductor")
        self.rank_knowl = display_knowl('ec.rank', title = "rank")
        self.ec_knowl = display_knowl('ec.q', title='elliptic curves')
        self.cl_knowl = display_knowl('ec.isogeny', title = "isogeny classes")

    @property
    def short_summary(self):
        stats_url = url_for(".statistics")
        return r'The database currently includes %s %s defined over $\Q$, in %s %s, with %s at most %s.  Here are some further <a href="%s">statistics and completeness information</a>.' % (self.ncurves_c, self.ec_knowl, self.nclasses_c, self.cl_knowl, self.cond_knowl, self.max_N_c, stats_url)

    @property
    def summary(self):
        return r'Currently, the database includes ${}$ {} over $\Q$ in ${}$ {}, with {} at most ${}$.'.format(self.ncurves_c, self.ec_knowl, self.nclasses_c, self.cl_knowl, self.cond_knowl, self.max_N_c)
    
    table = db.ec_curvedata
    baseurl_func = ".rational_elliptic_curves"

    knowls = {'rank': 'ec.rank',
              'sha': 'ec.q.analytic_sha_order',
              'torsion_structure': 'ec.torsion_order'}

    top_titles = {'rank': 'rank',
                  'sha': 'analytic order of &#1064;',
                  'torsion_structure': 'torsion subgroups'}

    formatters = {'torsion_structure': latex_tor,
                  'sha': latex_sha}

    query_formatters = {'torsion_structure': 'torsion_structure={}'.format,
                        'sha': 'sha={}'.format}

    stat_list = [
        {'cols': 'rank', 'totaler': {'avg': True}},
        {'cols': 'torsion_structure'},
        {'cols': 'sha', 'totaler': {'avg': False}},
    ]

    @cached_method
    def isogeny_degrees(self):
        # cur = db._execute(SQL("SELECT UNIQ(SORT(ARRAY_AGG(elements ORDER BY elements))) FROM ec_curvedata, UNNEST(isogeny_degreed) as elements"))
        # return cur.fetchone()[0]
        #
        # It's a theorem that the complete set of possible degrees is this:
        return list(range(1,20)) + [21,25,27,37,43,67,163]
        
# NB the context processor wants something callable and the summary is a *property*

@app.context_processor
def ctx_elliptic_curve_summary():
    return {'elliptic_curve_summary': lambda: ECstats().summary}

@app.context_processor
def ctx_gl2_subgroup():
    return {'gl2_subgroup_data': gl2_subgroup_data}

@ec_page.route("/stats")
def statistics():
    title = r'Elliptic curves over $\Q$: Statistics'
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=ECstats(), title=title, bread=bread, learnmore=learnmore_list())


@ec_page.route("/<int:conductor>/")
def by_conductor(conductor):
    info = to_dict(request.args, search_array=ECSearchArray())
    info['bread'] = get_bread([('%s' % conductor, url_for(".by_conductor", conductor=conductor))])
    info['title'] = r'Elliptic curves over $\Q$ of conductor %s' % conductor
    if request.args:
        # if conductor changed, fall back to a general search
        if 'conductor' in request.args and request.args['conductor'] != str(conductor):
            return redirect (url_for(".rational_elliptic_curves", **request.args), 307)
        info['title'] += ' Search results'
        info['bread'].append(('Search results',''))
    info['conductor'] = conductor
    return elliptic_curve_search(info)


def elliptic_curve_jump_error(label, args, missing_curve=False, missing_class=False, invalid_class=False):
    err_args = {}
    for field in ['conductor', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure']:
        err_args[field] = args.get(field, '')
    err_args['count'] = args.get('count', '100')
    err_args['label'] = label
    if missing_curve:
        err_args['err_msg'] = "The elliptic curve %s is not in the database"
    elif missing_class:
        err_args['err_msg'] = "The isogeny class %s is not in the database"
    elif invalid_class:
        err_args['err_msg'] = r"%s is not a valid label for an isogeny class of elliptic curves over $\mathbb{Q}$"
    elif not label:
        err_args['err_msg'] = "Please enter a non-empty label %s"
    else:
        err_args['err_msg'] = r"%s is not a valid label for an elliptic curve or isogeny class over $\mathbb{Q}$"
    return rational_elliptic_curves(err_args)

def elliptic_curve_jump(info):
    label = info.get('jump', '').replace(" ", "")
    m = match_lmfdb_label(label)
    if m:
        try:
            return by_ec_label(label)
        except ValueError:
            return elliptic_curve_jump_error(label, info, missing_curve=True)
    m = match_cremona_label(label)
    if m:
        try:
            return redirect(url_for(".by_ec_label", label=label))
            #return by_ec_label(label)
        except ValueError:
            return elliptic_curve_jump_error(label, info, missing_curve=True)

    if label:
        # Try to parse a string like [1,0,3,2,4] as valid
        # Weistrass coefficients:
        lab = re.sub(r'\s','',label)
        lab = re.sub(r'^\[','',lab)
        lab = re.sub(r']$','',lab)
        try:
            labvec = lab.split(',')
            labvec = [QQ(str(z)) for z in labvec] # Rationals allowed
            E = EllipticCurve(labvec).minimal_model()
            # Now we do have a valid curve over Q, but it might
            # not be in the database.
            lmfdb_label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)}, 'lmfdb_label')
            if lmfdb_label is None:
                info['conductor'] = E.conductor()
                return elliptic_curve_jump_error(label, info, missing_curve=True)
            return by_ec_label(lmfdb_label)
        except (TypeError, ValueError, ArithmeticError):
            return elliptic_curve_jump_error(label, info)
    else:
        return elliptic_curve_jump_error('', info)

def download_search(info):
    dltype = info['Submit']
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    ass = '='  # assignment
    eol = ''   # end of line
    filename = 'elliptic_curves.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'elliptic_curves.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        ass = ":="
        eol = ';'
        filename = 'elliptic_curves.m'
    s = com1 + "\n"
    s += com + ' Elliptic curves downloaded from the LMFDB downloaded on {}.\n'.format(mydate)
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [a1,a2,a3,a4,a6] (Weierstrass coefficients)\n'
    s += '\n' + com2 + '\n'
    s += 'data ' + ass + ' [' + '\\\n'
    # reissue saved query here
    res = db.ec_curvedata.search(ast.literal_eval(info["query"]), 'ainvs')
    s += ",\\\n".join(str(ainvs) for ainvs in res)
    s += ']' + eol + '\n'
    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)

def url_for_label(label):
    if label == "random":
        return url_for(".random_curve")
    return url_for(".by_ec_label", label=label)

@search_wrap(template="ec-search-results.html",
             table=db.ec_curvedata,
             title='Elliptic curve search results',
             err_title='Elliptic curve search input error',
             per_page=50,
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             shortcuts={'jump':elliptic_curve_jump,
                        'download':download_search},
             bread=lambda:get_bread('Search results'))

def elliptic_curve_search(info, query):
    parse_rational_to_list(info,query,'jinv','j-invariant')
    parse_ints(info,query,'conductor')
    if info.get('conductor_type'):
        if info['conductor_type'] == 'prime':
            query['num_bad_primes'] = 1
            query['semistable'] = True
        elif info['conductor_type'] == 'prime_power':
            query['num_bad_primes'] = 1
        elif info['conductor_type'] == 'squarefree':
            query['semistable'] = True
        elif info['conductor_type'] == 'divides':
            if not isinstance(query.get('conductor'), int):
                raise ValueError("You must specify a single level")
            else:
                query['conductor'] = {'$in': ZZ(query['conductor']).divisors()}
    parse_signed_ints(info, query, 'discriminant', qfield=('signD', 'absD'))
    parse_ints(info,query,'torsion','torsion order')
    parse_ints(info,query,'rank')
    parse_ints(info,query,'sha','analytic order of &#1064;')
    parse_ints(info,query,'num_int_pts','num_int_pts')
    parse_ints(info,query,'class_size','class_size')
    parse_ints(info,query,'class_deg','class_deg')
    parse_floats(info,query,'regulator','regulator')
    parse_floats(info, query, 'faltings_height', 'faltings_height')
    parse_bool(info,query,'semistable','semistable')
    parse_bool(info,query,'potential_good_reduction','potential_good_reduction')
    parse_bracketed_posints(info,query,'torsion_structure',maxlength=2,check_divisibility='increasing')
    # speed up slow torsion_structure searches by also setting torsion
    #if 'torsion_structure' in query and not 'torsion' in query:
    #    query['torsion'] = reduce(mul,[int(n) for n in query['torsion_structure']],1)
    if 'cm' in info:
        if info['cm'] == 'noCM':
            query['cm'] = 0
        elif info['cm'] == 'CM':
            query['cm'] = {'$ne' : 0}
        else:
            parse_ints(info,query,field='cm',qfield='cm')
    parse_element_of(info,query,'isogeny_degrees',split_interval=1000,contained_in=get_stats().isogeny_degrees)
    parse_primes(info, query, 'maximal_primes', name='maximal primes',
                 qfield='nonmaximal_primes', mode='exclude')
    parse_primes(info, query, 'nonmaximal_primes', name='non-maximal primes',
                 qfield='nonmaximal_primes',mode=info.get('max_quantifier'), radical='nonmax_rad')
    parse_primes(info, query, 'bad_primes', name='bad primes',
                 qfield='bad_primes',mode=info.get('bad_quantifier'))
    parse_primes(info, query, 'sha_primes', name='sha primes',
                 qfield='sha_primes',mode=info.get('sha_quantifier'))
    if info.get("nonmaximal_image"):
        query['elladic_images'] = {'$contains': info['nonmaximal_image'].strip() }
        if not 'cm' in query:
            query['cm'] = 0
    # The button which used to be labelled Optimal only no/yes"
    # (default: no) has been renamed "Curves per isogeny class
    # all/one" (default: all).  When this option is "one" we only list
    # one curve in each class, currently choosing the curve with
    # minimal Faltings heights, which is conjecturally the
    # Gamma_1(N)-optimal curve.
    if 'optimal' in info and info['optimal'] == 'on':
        query["__one_per__"] = "lmfdb_iso"

    info['curve_ainvs'] = lambda dbc: str([ZZ(ai) for ai in dbc['ainvs']])
    info['curve_url_LMFDB'] = lambda dbc: url_for(".by_triple_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1], number=dbc['lmfdb_number'])
    info['iso_url_LMFDB'] = lambda dbc: url_for(".by_double_iso_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1])
    info['cremona_bound'] = CREMONA_BOUND
    info['curve_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['Clabel'])
    info['iso_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['Ciso'])
    info['FH'] = lambda dbc: RealField(20)(dbc['faltings_height'])

##########################
#  Specific curve pages
##########################

@ec_page.route("/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor,iso_label):
    full_iso_label = class_lmfdb_label(conductor,iso_label)
    return render_isogeny_class(full_iso_label)

@ec_page.route("/<int:conductor>/<iso_label>/<int:number>")
def by_triple_label(conductor,iso_label,number):
    full_label = curve_lmfdb_label(conductor,iso_label,number)
    return render_curve_webpage_by_label(full_label)

# The following function determines whether the given label is in
# LMFDB or Cremona format, and also whether it is a curve label or an
# isogeny class label, and calls the appropriate function

@ec_page.route("/<label>/")
def by_ec_label(label):
    ec_logger.debug(label)

    # First see if we have an LMFDB label of a curve or class:
    try:
        N, iso, number = split_lmfdb_label(label)
        if number:
            return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=number))
        else:
            return redirect(url_for(".by_double_iso_label", conductor=N, iso_label=iso))

    except AttributeError:
        ec_logger.debug("%s not a valid lmfdb label, trying cremona")
        # Next see if we have a Cremona label of a curve or class:
        try:
            N, iso, number = split_cremona_label(label)
        except AttributeError:
            ec_logger.debug("%s not a valid cremona label either, trying Weierstrass")
            eqn = label.replace(" ","")
            if weierstrass_eqn_regex.match(eqn) or short_weierstrass_eqn_regex.match(eqn):
                return by_weierstrass(eqn)
            else:
                return elliptic_curve_jump_error(label, {})

        if number: # it's a curve
            label_type = 'Clabel'
        else:
            label_type = 'Ciso'

        data = db.ec_curvedata.lucky({label_type: label})
        if data is None:
            return elliptic_curve_jump_error(label, {}, missing_curve=True)
        ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
        if number:
            return render_curve_webpage_by_label(label)
        else:
            return render_isogeny_class(label)


def by_weierstrass(eqn):
    w = weierstrass_eqn_regex.match(eqn)
    if not w:
        w = short_weierstrass_eqn_regex.match(eqn)
    if not w:
        return elliptic_curve_jump_error(eqn, {})
    try:
        ainvs = [ZZ(ai) for ai in w.groups()]
    except TypeError:
        return elliptic_curve_jump_error(eqn, {})
    E = EllipticCurve(ainvs).global_minimal_model()
    label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)},'lmfdb_label')
    if label is None:
        N = E.conductor()
        return elliptic_curve_jump_error(eqn, {'conductor':N}, missing_curve=True)
    return redirect(url_for(".by_ec_label", label=label), 301)

def render_isogeny_class(iso_class):
    class_data = ECisog_class.by_label(iso_class)
    if class_data == "Invalid label":
        return elliptic_curve_jump_error(iso_class, {}, invalid_class=True)
    if class_data == "Class not found":
        return elliptic_curve_jump_error(iso_class, {}, missing_class=True)
    class_data.modform_display = url_for(".modular_form_display", label=class_data.lmfdb_iso+"1", number="")

    return render_template("ec-isoclass.html",
                           properties=class_data.properties,
                           info=class_data,
                           code=class_data.code,
                           bread=class_data.bread,
                           title=class_data.title,
                           friends=class_data.friends,
                           KNOWL_ID="ec.q.%s"%iso_class,
                           downloads=class_data.downloads,
                           learnmore=learnmore_list())

@ec_page.route("/modular_form_display/<label>")
@ec_page.route("/modular_form_display/<label>/<number>")
def modular_form_display(label, number):
    try:
        number = int(number)
    except ValueError:
        number = 10
    if number < 10:
        number = 10
    if number > 1000:
        number = 1000
    ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_label')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})
    E = EllipticCurve(ainvs)
    modform = E.q_eigenform(number)
    modform_string = raw_typeset(modform)
    return modform_string

def render_curve_webpage_by_label(label):
    cpt0 = cputime()
    t0 = time.time()
    data = WebEC.by_label(label)
    if data == "Invalid label":
        return elliptic_curve_jump_error(label, {})
    if data == "Curve not found":
        return elliptic_curve_jump_error(label, {}, missing_curve=True)
    try:
        lmfdb_label = data.lmfdb_label
    except AttributeError:
        return elliptic_curve_jump_error(label, {})

    data.modform_display = url_for(".modular_form_display", label=lmfdb_label, number="")

    code = data.code()
    code['show'] = {'magma':'','pari':'','sage':''} # use default show names
    T =  render_template("ec-curve.html",
                         properties=data.properties,
                         data=data,
                         # set default show names but actually code snippets are filled in only when needed
                         code=code,
                         bread=data.bread, title=data.title,
                         friends=data.friends,
                         downloads=data.downloads,
                         KNOWL_ID="ec.q.%s"%lmfdb_label,
                         BACKUP_KNOWL_ID="ec.q.%s"%data.lmfdb_iso,
                         learnmore=learnmore_list())
    ec_logger.debug("Total walltime: %ss"%(time.time() - t0))
    ec_logger.debug("Total cputime: %ss"%(cputime(cpt0)))
    return T

@ec_page.route("/padic_data/<label>/<int:p>")
def padic_data(label, p):
    try:
        N, iso, number = split_lmfdb_label(label)
    except AttributeError:
        return abort(404)
    info = {'p': p}
    if db.ec_curvedata.lookup(label, label_col='lmfdb_label', projection="rank") == 0:
        info['reg'] = 1
    elif number == '1':
        data = db.ec_padic.lucky({'lmfdb_iso': N + '.' + iso, 'p': p})
        if data is None:
            info['reg'] = 'no data'
        else:
            val = int(data['val'])
            aprec = data['prec']
            reg = Qp(p, aprec)(int(data['unit']), aprec - val) << val
            info['reg'] = web_latex(reg)
    else:
        info['reg'] = "no data"
    return render_template("ec-padic-data.html", info=info)


@ec_page.route("/download_qexp/<label>/<int:limit>")
def download_EC_qexp(label, limit):
    try:
        N, iso, number = split_lmfdb_label(label)
    except (ValueError,AttributeError):
        return elliptic_curve_jump_error(label, {})
    if number:
        ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_label')
    else:
        ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_iso')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})        
    if limit > 100000:
        return redirect(url_for('.download_EC_qexp',label=label,limit=10000), 301)
    E = EllipticCurve(ainvs)
    response = make_response(','.join(str(an) for an in E.anlist(int(limit), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response


#TODO: get all the data from all the relevant tables, not just the search table.

@ec_page.route("/download_all/<label>")
def download_EC_all(label):
    try:
        N, iso, number = split_lmfdb_label(label)
    except (ValueError,AttributeError):
        return elliptic_curve_jump_error(label, {})
    if number:
        data = db.ec_curvedata.lookup(label, label_col='lmfdb_label')
        if data is None:
            return elliptic_curve_jump_error(label, {})
        data_list = [data]
    else:
        data_list = list(db.ec_curvedata.search({'lmfdb_iso': label}, sort=['lmfdb_number']))
        if not data_list:
            return elliptic_curve_jump_error(label, {})

    response = make_response('\n\n'.join(Json.dumps(d) for d in data_list))
    response.headers['Content-type'] = 'text/plain'
    return response

@ec_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for elliptic curve data over $\Q$'
    bread = get_bread('Source')
    return render_template("double.html", kid='rcs.source.ec.q', kid2='rcs.ack.ec.q',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ec_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of elliptic curve data over $\Q$'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.ec.q',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@ec_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of elliptic curve data over $\Q$'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.ec.q',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@ec_page.route("/Labels")
def labels_page():
    t = r'Labels for elliptic curves over $\Q$'
    bread = get_bread('Labels')
    return render_template("single.html", kid='ec.q.lmfdb_label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@ec_page.route('/<conductor>/<iso>/<number>/download/<download_type>')
def ec_code_download(**args):
    response = make_response(ec_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response

@ec_page.route("/CongruentNumbers")
def render_congruent_number_data():
    info = to_dict(request.args)
    if 'lookup' in info:
        return redirect(url_for(".render_single_congruent_number", n=info['lookup']))
    learnmore = learnmore_list_remove('Congruent numbers and curves')
    t = 'Congruent numbers and congruent number curves'
    bread = get_bread(t)
    if 'filename' in info:
        filepath = os.path.join(congruent_number_data_directory,info['filename'])
        if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
            return send_file(filepath, as_attachment=True, add_etags=False)
        else:
            flash_error('File {} not found'.format(info['filename']))
            return redirect(url_for(".rational_elliptic_curves"))

    return render_template("congruent_number_data.html", info=info, title=t, bread=bread, learnmore=learnmore)

@ec_page.route("/CongruentNumber/<int:n>")
def render_single_congruent_number(n):
    if 0 < n and n <= 1000000:
        info = get_congruent_number_data(n)
    else:
        info = {'n': n, 'error': 'out of range'}
    t = "Is {} a congruent number?".format(n)
    bread = get_bread() + [("Congruent numbers", url_for(".render_congruent_number_data")), (n, "")]
    return render_template("single_congruent_number.html", info=info, title=t, bread=bread, learnmore=learnmore_list())


sorted_code_names = ['curve', 'tors', 'intpts', 'cond', 'disc', 'jinv', 'rank', 'reg', 'real_period', 'cp', 'ntors', 'sha', 'qexp', 'moddeg', 'L1', 'localdata', 'galrep', 'padicreg']

code_names = {'curve': 'Define the curve',
                 'tors': 'Torsion subgroup',
                 'intpts': 'Integral points',
                 'cond': 'Conductor',
                 'disc': 'Discriminant',
                 'jinv': 'j-invariant',
                 'rank': 'Rank',
                 'reg': 'Regulator',
                 'real_period': 'Real Period',
                 'cp': 'Tamagawa numbers',
                 'ntors': 'Torsion order',
                 'sha': 'Order of Sha',
                 'qexp': 'q-expansion of modular form',
                 'moddeg': 'Modular degree',
                 'L1': 'Special L-value',
                 'localdata': 'Local data',
                 'galrep': 'mod p Galois image',
                 'padicreg': 'p-adic regulator'}

Fullname = {'magma': 'Magma', 'sage': 'SageMath', 'gp': 'Pari/GP'}
Comment = {'magma': '//', 'sage': '#', 'gp': '\\\\', 'pari': '\\\\'}

def ec_code(**args):
    label = curve_lmfdb_label(args['conductor'], args['iso'], args['number'])
    E = WebEC.by_label(label)
    if E == "Invalid label":
        return elliptic_curve_jump_error(label, {})
    if E == "Curve not found":
        return elliptic_curve_jump_error(label, {}, missing_curve=True)
    Ecode = E.code()
    lang = args['download_type']
    code = "%s %s code for working with elliptic curve %s\n\n" % (Comment[lang],Fullname[lang],label)
    if lang=='gp':
        lang = 'pari'
    for k in sorted_code_names:
        if lang in Ecode[k]:
            code += "\n%s %s: \n" % (Comment[lang],code_names[k])
            code += Ecode[k][lang] + ('\n' if '\n' not in Ecode[k][lang] else '')
    return code

def tor_struct_search_Q(prefill="any"):
    def fix(t):
        return t + ' selected = "yes"' if prefill==t else t
    def cyc(n):
        return [fix("["+str(n)+"]"), "C{}".format(n)]
    def cyc2(m,n):
        return [fix("[{},{}]".format(m,n)), "C{}&times;C{}".format(m,n)]
    gps = [[fix(""), "any"], [fix("[]"), "trivial"]]
    for n in range(2,13):
        if n!=11:
            gps.append(cyc(n))
    for n in range(1,5):
        gps.append(cyc2(2,2*n))
    return "\n".join(["<select name='torsion_structure', style='width: 155px'>"] + ["<option value={}>{}</option>".format(a,b) for a,b in gps] + ["</select>"])

# the following allows the preceding function to be used in any template via {{...}}
app.jinja_env.globals.update(tor_struct_search_Q=tor_struct_search_Q)

class ECSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"
    jump_example = "11.a2"
    jump_egspan = "e.g. 11.a2 or 389.a or 11a1 or 389a or [0,1,1,-2,0] or [-3024, 46224]"
    jump_prompt = "Label or coefficients"
    jump_knowl = "ec.q.search_input"
    def __init__(self):
        conductor_quantifier = SelectBox(
            name='conductor_type',
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides','divides'),
                     ],
            min_width=85)
        cond = TextBoxWithSelect(
            name="conductor",
            label="Conductor",
            knowl="ec.q.conductor",
            example="389",
            example_span="389 or 100-200",
            select_box=conductor_quantifier)
        disc = TextBox(
            name="discriminant",
            label="Discriminant",
            knowl="ec.discriminant",
            example="389",
            example_span="389 or 100-200")
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="ec.rank",
            example="0")
        sha = TextBox(
            name="sha",
            label="Analytic order of &#1064;",
            knowl="ec.analytic_sha_order",
            example="4")
        isodeg = TextBox(
            name="isogeny_degrees",
            label="Cyclic isogeny degree",
            knowl="ec.isogeny",
            example="16")
        class_size = TextBox(
            name="class_size",
            label="Isogeny class size",
            knowl="ec.isogeny_class",
            example="4")
        class_deg = TextBox(
            name="class_deg",
            label="Isogeny class degree",
            knowl="ec.isogeny_class_degree",
            example="16")
        num_int_pts = TextBox(
            name="num_int_pts",
            label="Integral points",
            knowl="ec.q.integral_points",
            example="2",
            example_span="2 or 4-15")
        jinv = TextBox(
            name="jinv",
            label="j-invariant",
            knowl="ec.q.j_invariant",
            example="1728",
            example_span="1728 or -4096/11")
        torsion_opts = ([("", ""),("[]", "trivial")] +
                        [("%s"%n, "order %s"%n) for  n in range(4,16,4)] +
                        [("[%s]"%n, "C%s"%n) for n in range(2, 13) if n != 11] +
                        [("[2,%s]"%n, "C2&times;C%s"%n) for n in range(2, 10, 2)])
        torsion = SelectBox(
            name="torsion",
            label="Torsion",
            knowl="ec.torsion_subgroup",
            example="C3",
            options=torsion_opts)
        optimal = SelectBox(
            name="optimal",
            label="Curves per isogeny class",
            knowl="ec.isogeny_class",
            example="all, one",
            options=[("", "all"),
                     ("on", "one")])
        bad_quant = SubsetBox(
            name="bad_quantifier")
        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            label="Bad primes $p$",
            short_label="Bad $p$",
            knowl="ec.q.reduction_type",
            example="5,13",
            select_box=bad_quant)
        sha_quant = SubsetBox(
            name="sha_quantifier")
        sha_primes = TextBoxWithSelect(
            name="sha_primes",
            label="$p$ dividing |&#1064;|",
            short_label="$p$ div |&#1064;|",
            knowl="ec.analytic_sha_order",
            example="3,5",
            select_box=sha_quant)
        regulator = TextBox(
            name="regulator",
            label="Regulator",
            knowl="ec.q.regulator",
            example="8.4-9.1")
        faltings_height = TextBox(
            name="faltings_height",
            label="Faltings height",
            knowl="ec.q.faltings_height",
            example="-1-2")
        reduction_opts = ([("", ""),
                           ("semistable",  "semistable"),
                           ("not semistable",  "not semistable"),
                           ("potentially good", "potentially good"),
                           ("not potentially good", "not potentially good")])
        reduction = SelectBox(
            name="reduction",
            label="Reduction",
            example="semistable",
            knowl="ec.reduction",
            options=reduction_opts)
        galois_image = TextBox(
            name="nonmaximal_image",
            label=r"Galois image",
            short_label=r"Galois image",
            example="13.91.3.2",
            knowl="ec.galois_rep_elladic_image")
        nonmax_quant = SubsetBox(
            name="nonmax_quantifier")
        nonmax_primes = TextBoxWithSelect(
            name="nonmax_primes",
            label=r"Nonmaximal $\ell$",
            short_label=r"Nonmax $\ell$",
            knowl="ec.maximal_elladic_galois_rep",
            example="2,3",
            select_box=nonmax_quant)
        cm_opts = ([('', ''), ('noCM', 'no potential CM'), ('CM', 'potential CM')] +
                   [('-%d'%d, 'CM discriminant -%d'%d) for  d in [3,4,7,8,11,12,16,19,27,38,43,67,163]] +
                   [('-3,-12,-27', 'potential CM by Q(zeta_3)'), ('-4,-16', 'potential CM by Q(i)'), ('-7,-28', 'potential CM by Q(sqrt(7))')])
        cm = SelectBox(
            name="cm_disc",
            label="Complex multiplication",
            example="potential CM by Q(i)",
            knowl="ec.complex_multiplication",
            options=cm_opts
            )

        count = CountBox()

        self.browse_array = [
            [cond, jinv],
            [disc, bad_primes],
            [cm, torsion],
            [rank, regulator],
            [sha, sha_primes],
            [galois_image, nonmax_primes],
            [class_size, class_deg],
            [optimal, isodeg],
            [num_int_pts, reduction],
            [count, faltings_height]
            ]

        self.refine_array = [
            [cond, jinv, disc, torsion, cm],
            [rank, regulator, bad_primes, sha, galois_image],
            [class_size, class_deg, isodeg, sha_primes, nonmax_primes],
            [optimal, reduction, num_int_pts, faltings_height]
            ]
