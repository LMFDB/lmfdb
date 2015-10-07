# -*- coding: utf-8 -*-
import re
import time

from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response, send_file
import tempfile
import os
import StringIO

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range2, web_latex_split_on_pm, comma, clean_input
from lmfdb.number_fields.number_field import parse_list
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.ec_stats import get_stats
from lmfdb.elliptic_curves.isog_class import ECisog_class
from lmfdb.elliptic_curves.web_ec import WebEC, parse_list, parse_points, match_lmfdb_label, match_lmfdb_iso_label, match_cremona_label, split_lmfdb_label, split_lmfdb_iso_label, split_cremona_label, weierstrass_eqn_regex, short_weierstrass_eqn_regex

import sage.all
from sage.all import ZZ, QQ, EllipticCurve, latex, matrix, srange
q = ZZ['x'].gen()

#########################
#   Database connection
#########################
ecdb = None

def db_ec():
    global ecdb
    if ecdb is None:
        ecdb = lmfdb.base.getDBConnection().elliptic_curves.curves
    return ecdb


#########################
#   Utility functions
#########################

LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')

def format_ainvs(ainvs):
    """
    The a-invariants are stored as a list of strings because mongodb doesn't
    have big-ints, and all strings are stored as unicode. However, printing
    a list of unicodes looks like [u'0', u'1', ...]
    """
    return [ZZ(a) for a in ainvs]

def cmp_label(lab1, lab2):
    from sage.databases.cremona import parse_cremona_label, class_to_int
    a, b, c = parse_cremona_label(lab1)
    id1 = int(a), class_to_int(b), int(c)
    a, b, c = parse_cremona_label(lab2)
    id2 = int(a), class_to_int(b), int(c)
    return cmp(id1, id2)

def parse_torsion_structure(L):
    r"""
    Parse a string entered into torsion structure search box
    '[]' --> []
    '[n]' --> [str(n)]
    'n' --> [str(n)]
    '[m,n]' or '[m n]' --> [str(m),str(n)]
    'm,n' or 'm n' --> [str(m),str(n)]
    """
    # strip <whitespace> or <whitespace>[<whitespace> from the beginning:
    L1 = re.sub(r'^\s*\[?\s*', '', str(L))
    # strip <whitespace> or <whitespace>]<whitespace> from the beginning:
    L1 = re.sub(r'\s*]?\s*$', '', L1)
    # catch case where there is nothing left:
    if not L1:
        return []
    # This matches a string of 1 or more digits at the start,
    # optionally followed by nontrivial <ws> or <ws>,<ws> followed by
    # 1 or more digits at the end:
    TORS_RE = re.compile(r'^\d+((\s+|\s*,\s*)\d+)?$')
    if TORS_RE.match(L1):
        if ',' in L1:
            # strip interior <ws> and use ',' as delimiter:
            res = [int(a) for a in L1.replace(' ','').split(',')]
        else:
            # use whitespace as delimiter:
            res = [int(a) for a in L1.split()]
        n = len(res)
        if (n==1 and res[0]>0) or (n==2 and res[0]>0 and res[1]>0 and res[1]%res[0]==0):
            return res
    return 'Error parsing input %s for the torsion structure.  It needs to be a list of 0, 1 or 2 integers, optionally in square brackets, such as [6], 6, [2,2], or [2,4].  Moreover, each integer should be bigger than 1, and each divides the next.' % L


#########################
#    Top level
#########################

@app.route("/EC")
def EC_redirect():
    return redirect(url_for("ec.rational_elliptic_curves", **request.args))

#########################
#  Search/navigate
#########################

@ec_page.route("/")
def rational_elliptic_curves(err_args=None):
    if err_args is None:
        if len(request.args) != 0:
            return elliptic_curve_search(**request.args)
        else:
            err_args = {}
            for field in ['conductor', 'jinv', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure', 'msg']:
                err_args[field] = ''
            err_args['count'] = '100'
    counts = get_stats().counts()

    conductor_list_endpoints = [1, 100, 1000, 10000, 100000, counts['max_N'] + 1]
    conductor_list = ["%s-%s" % (start, end - 1) for start, end in zip(conductor_list_endpoints[:-1],
                                                                       conductor_list_endpoints[1:])]
    rank_list = range(counts['max_rank'] + 1)
    torsion_list = range(1,11) + [12, 16]
    info = {
        'rank_list': rank_list,
        'torsion_list': torsion_list,
        'conductor_list': conductor_list,
        'counts': counts,
        'stats_url': url_for(".statistics")
    }
    credit = 'John Cremona and Andrew Sutherland'
    t = 'Elliptic curves over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")), ('$\Q$', ' ')]
    return render_template("browse_search.html", info=info, credit=credit, title=t, bread=bread, **err_args)

@ec_page.route("/random")
def random_curve():
    from sage.misc.prandom import randint
    n = get_stats().counts()['ncurves']
    n = randint(0,n-1)
    label = db_ec().find()[n]['label']
    # This version leaves the word 'random' in the URL:
    # return render_curve_webpage_by_label(label)
    # This version uses the curve's own URL:
    return redirect(url_for(".by_ec_label", label=label), 301)


@ec_page.route("/curve_of_the_day")
def todays_curve():
    from datetime import date
    mordells_birthday = date(1888,1,28)
    n = (date.today()-mordells_birthday).days
    label = db_ec().find({'number' : int(1)})[n]['label']
    #return render_curve_webpage_by_label(label)
    return redirect(url_for(".by_ec_label", label=label), 301)

@ec_page.route("/stats")
def statistics():
    info = {
        'counts': get_stats().counts(),
        'stats': get_stats().stats(),
    }
    credit = 'John Cremona'
    t = 'Elliptic curves over $\Q$: statistics'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('$\Q$', url_for(".rational_elliptic_curves")),
             ('statistics', ' ')]
    return render_template("statistics.html", info=info, credit=credit, title=t, bread=bread)


@ec_page.route("/<int:conductor>/")
def by_conductor(conductor):
    return elliptic_curve_search(conductor=conductor, **request.args)


def elliptic_curve_jump_error(label, args, wellformed_label=False, cremona_label=False, missing_curve=False):
    err_args = {}
    for field in ['conductor', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure']:
        err_args[field] = args.get(field, '')
    err_args['count'] = args.get('count', '100')
    if wellformed_label:
        err_args['err_msg'] = "No curve or isogeny class in the database has label %s" % label
    elif cremona_label:
        err_args['err_msg'] = "To search for a Cremona label use 'Cremona:%s'" % label
    elif missing_curve:
        err_args['err_msg'] = "The elliptic curve %s (conductor = %s) is not in the database" % (label, args.get('conductor','?'))
    else:
        err_args['err_msg'] = "%s does not define a recognised elliptic curve over $\mathbb{Q}$" % label
    return rational_elliptic_curves(err_args)


def elliptic_curve_search(**args):
    info = to_dict(args)
    query = {}
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('$\Q$', url_for(".rational_elliptic_curves")),
             ('Search Results', '.')]
    if 'SearchAgain' in args:
        return rational_elliptic_curves()

    if 'jump' in args:
        label = info.get('label', '').replace(" ", "")
        m = match_lmfdb_label(label)
        if m:
            try:
                return by_ec_label(label)
            except ValueError:
                return elliptic_curve_jump_error(label, info, wellformed_label=True)
        elif label.startswith("Cremona:"):
            label = label[8:]
            m = match_cremona_label(label)
            if m:
                try:
                    return by_ec_label(label)
                except ValueError:
                    return elliptic_curve_jump_error(label, info, wellformed_label=True)
        elif match_cremona_label(label):
            return elliptic_curve_jump_error(label, info, cremona_label=True)
        elif label:
            # Try to parse a string like [1,0,3,2,4] as valid
            # Weistrass coefficients:
            lab = re.sub(r'\s','',label)
            lab = re.sub(r'^\[','',lab)
            lab = re.sub(r']$','',lab)
            try:
                labvec = lab.split(',')
                labvec = [QQ(str(z)) for z in labvec] # Rationals allowed
                E = EllipticCurve(labvec)
                # Now we do have a valid curve over Q, but it might
                # not be in the database.
                ainvs = [str(c) for c in E.minimal_model().ainvs()]
                data = db_ec().find_one({'ainvs': ainvs})
                if data is None:
                    info['conductor'] = E.conductor()
                    return elliptic_curve_jump_error(label, info, missing_curve=True)
                return by_ec_label(data['lmfdb_label'])
            except (TypeError, ValueError, ArithmeticError):
                return elliptic_curve_jump_error(label, info)
        else:
            query['label'] = ''

    if info.get('jinv'):
        j = clean_input(info['jinv'])
        j = j.replace('+', '')
        if not QQ_RE.match(j):
            info['err'] = 'Error parsing input for the j-invariant.  It needs to be a rational number.'
            return search_input_error(info, bread)
        query['jinv'] = str(QQ(j)) # to simplify e.g. 1728/1

    for field in ['conductor', 'torsion', 'rank', 'sha']:
        if info.get(field):
            info[field] = clean_input(info[field])
            ran = info[field]
            ran = ran.replace('..', '-').replace(' ', '')
            if not LIST_RE.match(ran):
                names = {'conductor': 'conductor', 'torsion': 'torsion order', 'rank':
                         'rank', 'sha': 'analytic order of &#1064;'}
                info['err'] = 'Error parsing input for the %s.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).' % names[field]
                return search_input_error(info, bread)
            # Past input check
            tmp = parse_range2(ran, field)
            # work around syntax for $or
            # we have to foil out multiple or conditions
            if tmp[0] == '$or' and '$or' in query:
                newors = []
                for y in tmp[1]:
                    oldors = [dict.copy(x) for x in query['$or']]
                    for x in oldors:
                        x.update(y)
                    newors.extend(oldors)
                tmp[1] = newors
            query[tmp[0]] = tmp[1]

    if 'optimal' in info and info['optimal'] == 'on':
        # fails on 990h3
        query['number'] = 1

    if 'torsion_structure' in info and info['torsion_structure']:
        res = parse_torsion_structure(info['torsion_structure'])
        if 'Error' in res:
            info['err'] = res
            return search_input_error(info, bread)
        #update info for repeat searches
        info['torsion_structure'] = str(res).replace(' ','')
        query['torsion_structure'] = [str(r) for r in res]

    if info.get('surj_primes'):
        info['surj_primes'] = clean_input(info['surj_primes'])
        format_ok = LIST_POSINT_RE.match(info['surj_primes'])
        if format_ok:
            surj_primes = [int(p) for p in info['surj_primes'].split(',')]
            format_ok = all([ZZ(p).is_prime(proof=False) for p in surj_primes])
        if format_ok:
            query['non-surjective_primes'] = {"$nin": surj_primes}
        else:
            info['err'] = 'Error parsing input for surjective primes.  It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11).'
            return search_input_error(info, bread)

    if info.get('nonsurj_primes'):
        info['nonsurj_primes'] = clean_input(info['nonsurj_primes'])
        format_ok = LIST_POSINT_RE.match(info['nonsurj_primes'])
        if format_ok:
            nonsurj_primes = [int(p) for p in info['nonsurj_primes'].split(',')]
            format_ok = all([ZZ(p).is_prime(proof=False) for p in nonsurj_primes])
        if format_ok:
            if info['surj_quantifier'] == 'exactly':
                nonsurj_primes.sort()
                query['non-surjective_primes'] = nonsurj_primes
            else:
                if 'non-surjective_primes' in query:
                    query['non-surjective_primes'] = { "$nin": surj_primes, "$all": nonsurj_primes }
                else:
                    query['non-surjective_primes'] = { "$all": nonsurj_primes }
        else:
            info['err'] = 'Error parsing input for nonsurjective primes.  It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11).'
            return search_input_error(info, bread)

    if 'download' in info and info['download'] != '0':
        res = db_ec().find(query).sort([ ('conductor', ASCENDING), ('lmfdb_iso', ASCENDING), ('lmfdb_number', ASCENDING) ])
        return download_search(info, res)
    
    count_default = 100
    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = count_default
    else:
        count = count_default
    info['count'] = count

    start_default = 0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default

    cursor = db_ec().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('conductor', ASCENDING), ('lmfdb_iso', ASCENDING), ('lmfdb_number', ASCENDING)
                       ]).skip(start).limit(count)
    info['curves'] = res
    info['format_ainvs'] = format_ainvs
    info['curve_url'] = lambda dbc: url_for(".by_triple_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1], number=dbc['lmfdb_number'])
    info['iso_url'] = lambda dbc: url_for(".by_double_iso_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1])
    info['number'] = nres
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    elif nres == 2:
        info['report'] = 'displaying both matches'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    credit = 'John Cremona'
    if 'non-surjective_primes' in query:
        credit += 'and Andrew Sutherland'
    t = 'Elliptic Curves search results'
    return render_template("search_results.html", info=info, credit=credit, bread=bread, title=t)


def search_input_error(info, bread):
    return render_template("search_results.html", info=info, title='Elliptic Curve Search Input Error', bread=bread)

##########################
#  Specific curve pages
##########################

@ec_page.route("/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor,iso_label):
    full_iso_label = str(conductor)+"."+iso_label
    return render_isogeny_class(full_iso_label)

@ec_page.route("/<int:conductor>/<iso_label>/<int:number>")
def by_triple_label(conductor,iso_label,number):
    full_label = str(conductor)+"."+iso_label+str(number)
    return render_curve_webpage_by_label(full_label)

# The following function determines whether the given label is in
# LMFDB or Cremona format, and also whether it is a curve label or an
# isogeny class label, and calls the appropriate function

@ec_page.route("/<label>")
def by_ec_label(label):
    ec_logger.debug(label)
    try:
        N, iso, number = split_lmfdb_label(label)
    except AttributeError:
        ec_logger.debug("%s not a valid lmfdb label, trying cremona")
        try:
            N, iso, number = split_cremona_label(label)
        except AttributeError:
            ec_logger.debug("%s not a valid cremona label either, trying Weierstrass")
            eqn = label.replace(" ","")
            if weierstrass_eqn_regex.match(eqn) or short_weierstrass_eqn_regex.match(eqn):
                return by_weierstrass(eqn)
            else:
                return elliptic_curve_jump_error(label, {})

        # We permanently redirect to the lmfdb label
        if number: # it's a curve
            data = db_ec().find_one({'label': label})
            if data is None:
                return elliptic_curve_jump_error(label, {})
            ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
            #return redirect(url_for(".by_ec_label", label=data['lmfdb_label']), 301)
            return render_curve_webpage_by_label(data['label'])
        else: # it's an isogeny class
            data = db_ec().find_one({'iso': label})
            if data is None:
                return elliptic_curve_jump_error(label, {})
            ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
            #return redirect(url_for(".by_ec_label", label=data['iso']), 301)
            return render_isogeny_class(data['iso'])

    if number:
        return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=number))
    else:
        return redirect(url_for(".by_double_iso_label", conductor=N, iso_label=iso))

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
    N = E.conductor()
    ainvs = [str(ai) for ai in E.ainvs()]
    data = db_ec().find_one({'ainvs': ainvs})
    if data is None:
        return elliptic_curve_jump_error(eqn, {'conductor':N}, missing_curve=True)
    return redirect(url_for(".by_ec_label", label=data['lmfdb_label']), 301)

def render_isogeny_class(iso_class):
    credit = 'John Cremona'
    class_data = ECisog_class.by_label(iso_class)
    if class_data == "Invalid label":
        return elliptic_curve_jump_error(iso_class, {}, wellformed_label=False)
    if class_data == "Class not found":
        return elliptic_curve_jump_error(iso_class, {}, wellformed_label=True)
    class_data.modform_display = url_for(".modular_form_display", label=class_data.lmfdb_iso+"1", number="")

    return render_template("iso_class.html",
                           properties2=class_data.properties,
                           info=class_data,
                           bread=class_data.bread,
                           credit=credit,
                           title=class_data.title,
                           friends=class_data.friends,
                           downloads=class_data.downloads)

@ec_page.route("/modular_form_display/<label>/<number>")
def modular_form_display(label, number):
    try:
        number = int(number)
    except:
        number = 10
    if number < 10:
        number = 10
    # if number > 100000:
    #     number = 20
    # if number > 50000:
    #     return "OK, I give up."
    # if number > 20000:
    #     return "This incident will be reported to the appropriate authorities."
    # if number > 9600:
    #     return "You have been banned from this website."
    # if number > 4800:
    #     return "Seriously."
    # if number > 2400:
    #     return "I mean it."
    # if number > 1200:
    #     return "Please stop poking me."
    if number > 1000:
        number = 1000
    data = db_ec().find_one({'lmfdb_label': label})
    if data is None:
        return elliptic_curve_jump_error(label, {})
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    modform = E.q_eigenform(number)
    modform_string = web_latex_split_on_pm(modform)
    return modform_string

# This function is now redundant since we store plots as
# base64-encoded pngs.
@ec_page.route("/plot/<label>")
def plot_ec(label):
    C = lmfdb.base.getDBConnection()
    data = C.elliptic_curves.curves.find_one({'lmfdb_label': label})
    if data is None:
        return elliptic_curve_jump_error(label, {})
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    P = E.plot()
    _, filename = tempfile.mkstemp('.png')
    P.save(filename)
    data = open(filename).read()
    os.unlink(filename)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response


def render_curve_webpage_by_label(label):
    credit = 'John Cremona and Andrew Sutherland'
    data = WebEC.by_label(label)
    if data == "Invalid label":
        return elliptic_curve_jump_error(label, {}, wellformed_label=False)
    if data == "Curve not found":
        return elliptic_curve_jump_error(label, {}, wellformed_label=True)
    try:
        lmfdb_label = data.lmfdb_label
    except AttributeError:
        return elliptic_curve_jump_error(label, {}, wellformed_label=False)

    if data.twoadic_label:
        credit = credit.replace(' and',',') + ' and Jeremy Rouse'
    data.modform_display = url_for(".modular_form_display", label=lmfdb_label, number="")

    return render_template("curve.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           bread=data.bread, title=data.title,
                           friends=data.friends,
                           downloads=data.downloads)

@ec_page.route("/padic_data")
def padic_data():
    info = {}
    label = request.args['label']
    p = int(request.args['p'])
    info['p'] = p
    N, iso, number = split_lmfdb_label(label)
    if request.args['rank'] == '0':
        info['reg'] = 1
    elif number == '1':
        C = lmfdb.base.getDBConnection()
        data = C.elliptic_curves.curves.find_one({'lmfdb_iso': N + '.' + iso})
        data = C.elliptic_curves.padic_db.find_one({'lmfdb_iso': N + '.' + iso, 'p': p})
        info['data'] = data
        if data is None:
            info['reg'] = 'no data'
        else:
            val = int(data['val'])
            aprec = data['prec']
            reg = sage.all.Qp(p, aprec)(int(data['unit']), aprec - val) << val
            info['reg'] = web_latex(reg)
    else:
        info['reg'] = "no data"
    return render_template("padic_data.html", info=info)


@ec_page.route("/download_qexp/<label>/<limit>")
def download_EC_qexp(label, limit):
    ec_logger.debug(label)
    CDB = lmfdb.base.getDBConnection().elliptic_curves.curves
    N, iso, number = split_lmfdb_label(label)
    if number:
        data = CDB.find_one({'lmfdb_label': label})
    else:
        data = CDB.find_one({'lmfdb_iso': label})
    ainvs = data['ainvs']
    ec_logger.debug(ainvs)
    E = EllipticCurve([int(a) for a in ainvs])
    response = make_response(','.join(str(an) for an in E.anlist(int(limit), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response


@ec_page.route("/download_all/<label>")
def download_EC_all(label):
    CDB = lmfdb.base.getDBConnection().elliptic_curves.curves
    N, iso, number = split_lmfdb_label(label)
    if number:
        data = CDB.find_one({'lmfdb_label': label})
        if data is None:
            return elliptic_curve_jump_error(label, {})
        data_list = [data]
    else:
        data_list = sorted(list(CDB.find({'lmfdb_iso': label})), key=lambda E: E['number'])
        if len(data_list) == 0:
            return elliptic_curve_jump_error(label, {})

    # titles of all entries of curves
    dump_data = []
    titles = [str(c) for c in data_list[0]]
    titles = [t for t in titles if t[0] != '_']
    titles.sort()
    dump_data.append(titles)
    for data in data_list:
        data1 = []
        for t in titles:
            d = data[t]
            if t == 'ainvs':
                data1.append(format_ainvs(d))
            elif t in ['torsion_generators', 'torsion_structure']:
                data1.append([eval(g) for g in d])
            elif t == 'x-coordinates_of_integral_points':
                data1.append(parse_list(d))
            elif t == 'gens':
                data1.append(parse_points(d))
            elif t in ['iso', 'label', 'lmfdb_iso', 'lmfdb_label']:
                data1.append(str(d))
            else:
                data1.append(d)
        dump_data.append(data1)
    response = make_response('\n'.join(str(an) for an in dump_data))
    response.headers['Content-type'] = 'text/plain'
    return response


def download_search(info, res):
    dltype = info['Submit']
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'elliptic_curves.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'elliptic_curves.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'elliptic_curves.m'
    s = com1 + "\n"
    s += com + ' Elliptic curves downloaded from the LMFDB downloaded %s\n'% mydate
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [Weierstrass Coefficients]\n'
    s += '\n' + com2
    s += '\n'
    if dltype == 'magma':
        s += 'data := ['
    else:
        s += 'data = ['
    s += '\\\n'
    for f in res:
        entry = str(f['ainvs'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        s += entry + ',\\\n'
    s = s[:-3]
    s += ']\n'
    if delim == 'brace':
        s = s.replace('[', '{')
        s = s.replace(']', '}')
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True)


#@ec_page.route("/download_Rub_data")
# def download_Rub_data():
#    import gridfs
#    label=(request.args.get('label'))
#    type=(request.args.get('type'))
#    C = base.getDBConnection()
#    fs = gridfs.GridFS(C.elliptic_curves,'isogeny' )
#    isogeny=C.ellcurves.isogeny.files
#    filename=isogeny.find_one({'label':str(label),'type':str(type)})['filename']
#    d= fs.get_last_version(filename)
#    response = make_response(d.readline())
#    response.headers['Content-type'] = 'text/plain'
#    return response
