# -*- coding: utf-8 -*-
import re
import time
import ast
from pymongo import ASCENDING
from operator import mul
import lmfdb.base
from lmfdb.base import app
from flask import render_template, url_for, request, redirect, make_response, send_file
import tempfile
import os
import StringIO

from lmfdb.utils import web_latex, to_dict, web_latex_split_on_pm, random_object_from_collection
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.ec_stats import get_stats
from lmfdb.elliptic_curves.isog_class import ECisog_class
from lmfdb.elliptic_curves.web_ec import WebEC, match_lmfdb_label, match_cremona_label, split_lmfdb_label, split_cremona_label, weierstrass_eqn_regex, short_weierstrass_eqn_regex, class_lmfdb_label, curve_lmfdb_label, db_ec
from lmfdb.search_parsing import parse_rational, parse_ints, parse_bracketed_posints, parse_primes, parse_count, parse_start

import sage.all
from sage.all import ZZ, QQ, EllipticCurve
q = ZZ['x'].gen()

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


#########################
#    Top level
#########################

@app.route("/EC")
def EC_redirect():
    return redirect(url_for("ec.rational_elliptic_curves", **request.args))

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Elliptic Curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

#########################
#  Search/navigate
#########################

@ec_page.route("/")
def rational_elliptic_curves(err_args=None):
    if err_args is None:
        if len(request.args) != 0:
            return elliptic_curve_search(to_dict(request.args))
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
    return render_template("ec-index.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'), **err_args)

@ec_page.route("/random")
def random_curve():
    label = random_object_from_collection( db_ec() )['lmfdb_label']
    cond, iso, num = split_lmfdb_label(label)
    return redirect(url_for(".by_triple_label", conductor=cond, iso_label=iso, number=num))

@ec_page.route("/curve_of_the_day")
def todays_curve():
    from datetime import date
    mordells_birthday = date(1888,1,28)
    n = (date.today()-mordells_birthday).days
    label = db_ec().find({'number' : int(1)})[n]['label']
    #return render_curve_webpage_by_label(label)
    return redirect(url_for(".by_ec_label", label=label), 307)

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
    return render_template("ec-stats.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())


@ec_page.route("/<int:conductor>/")
def by_conductor(conductor):
    info = to_dict(request.args)
    info['bread'] = [('Elliptic Curves', url_for("ecnf.index")), ('$\Q$', url_for(".rational_elliptic_curves")), ('%s' % conductor, url_for(".by_conductor", conductor=conductor))]
    info['title'] = 'Elliptic Curves over $\Q$ of conductor %s' % conductor
    if len(request.args) > 0:
        # if conductor changed, fall back to a general search
        if 'conductor' in request.args and request.args['conductor'] != str(conductor):
            return redirect (url_for(".rational_elliptic_curves", **request.args), 307)
        info['title'] += ' search results'
        info['bread'].append(('search results',''))
    info['conductor'] = conductor
    return elliptic_curve_search(info)


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


def elliptic_curve_search(info):

    if info.get('download') == '1' and info.get('Submit') and info.get('query'):
        return download_search(info)

    if 'SearchAgain' in info:
        return rational_elliptic_curves()

    query = {}
    bread = info.get('bread',[('Elliptic Curves', url_for("ecnf.index")), ('$\Q$', url_for(".rational_elliptic_curves")), ('Search Results', '.')])

    if 'jump' in info:
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
                xainvs = ''.join(['[',','.join(ainvs),']'])
                data = db_ec().find_one({'xainvs': xainvs})
                if data is None:
                    data = db_ec().find_one({'ainvs': ainvs})
                    if data is None:
                        info['conductor'] = E.conductor()
                        return elliptic_curve_jump_error(label, info, missing_curve=True)
                return by_ec_label(data['lmfdb_label'])
            except (TypeError, ValueError, ArithmeticError):
                return elliptic_curve_jump_error(label, info)
        else:
            query['label'] = ''

    try:
        parse_rational(info,query,'jinv','j-invariant')
        parse_ints(info,query,'conductor')
        parse_ints(info,query,'torsion','torsion order')
        parse_ints(info,query,'rank')
        parse_ints(info,query,'sha','analytic order of &#1064;')
        parse_bracketed_posints(info,query,'torsion_structure',maxlength=2,process=str,check_divisibility='increasing')
        # speed up slow torsion_structure searches by also setting torsion
        if 'torsion_structure' in query and not 'torsion' in query:
            query['torsion'] = reduce(mul,[int(n) for n in query['torsion_structure']],1)
        if 'include_cm' in info:
            if info['include_cm'] == 'exclude':
                query['cm'] = 0
            elif info['include_cm'] == 'only':
                query['cm'] = {'$ne' : 0}

        parse_ints(info,query,field='isodeg',qfield='isogeny_degrees')

        parse_primes(info, query, 'surj_primes', name='surjective primes',
                     qfield='non-maximal_primes', mode='complement')
        if info.get('surj_quantifier') == 'exactly':
            mode = 'exact'
        else:
            mode = 'append'
        parse_primes(info, query, 'nonsurj_primes', name='non-surjective primes',
                     qfield='non-maximal_primes',mode=mode)
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info, bread)

    count = parse_count(info,100)
    start = parse_start(info)

    if 'optimal' in info and info['optimal'] == 'on':
        # fails on 990h3
        query['number'] = 1

    info['query'] = query
    cursor = db_ec().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('conductor', ASCENDING), ('iso_nlabel', ASCENDING),
                       ('lmfdb_number', ASCENDING)]).skip(start).limit(count)
    info['curves'] = res
    info['format_ainvs'] = format_ainvs
    info['curve_url'] = lambda dbc: url_for(".by_triple_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1], number=dbc['lmfdb_number'])
    info['iso_url'] = lambda dbc: url_for(".by_double_iso_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1])
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start + count < nres)

    
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
    if 'non-surjective_primes' in query or 'non-maximal_primes' in query:
        credit += ' and Andrew Sutherland'

    t = info.get('title','Elliptic Curves search results')
    return render_template("ec-search-results.html", info=info, credit=credit, bread=bread, title=t)


def search_input_error(info, bread):
    return render_template("ec-search-results.html", info=info, title='Elliptic Curve Search Input Error', bread=bread, learnmore=learnmore_list())

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

@ec_page.route("/<label>")
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
            label_type = 'label'
        else:
            label_type = 'iso'

        data = db_ec().find_one({label_type: label})
        if data is None:
            return elliptic_curve_jump_error(label, {})
        ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
        iso = data['lmfdb_iso'].split(".")[1]
        if number:
            return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=data['lmfdb_number']))
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
    xainvs = ''.join(['[',','.join(ainvs),']'])
    data = db_ec().find_one({'xainvs': xainvs})
    if data is None:
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

    return render_template("ec-isoclass.html",
                           properties2=class_data.properties,
                           info=class_data,
                           code=class_data.code,
                           bread=class_data.bread,
                           credit=credit,
                           title=class_data.title,
                           friends=class_data.friends,
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
    if data.data['iwdata']:
        credit = credit.replace(' and',',') + ' and Robert Pollack'
    data.modform_display = url_for(".modular_form_display", label=lmfdb_label, number="")

    code = data.code()
    code['show'] = {'magma':'','pari':'','sage':''} # use default show names
    return render_template("ec-curve.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           # set default show names but actually code snippets are filled in only when needed
                           code=code,
                           bread=data.bread, title=data.title,
                           friends=data.friends,
                           downloads=data.downloads,
                           learnmore=learnmore_list())

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
    return render_template("ec-padic-data.html", info=info)


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
    try:
        N, iso, number = split_lmfdb_label(label)
    except (ValueError,AttributeError):
        return elliptic_curve_jump_error(label, {})
    CDB = db_ec()
    if number:
        data = CDB.find_one({'lmfdb_label': label})
        if data is None:
            return elliptic_curve_jump_error(label, {})
        data_list = [data]
    else:
        data_list = sorted(list(CDB.find({'lmfdb_iso': label})), key=lambda E: E['number'])
        if len(data_list) == 0:
            return elliptic_curve_jump_error(label, {})

    # For each curve we will output all data fields except the '_id':
    # (This should also be possible by adding projection={'_id':False}
    # to the find() call but on testing that timed out.)
    for data in data_list:
        data.pop('_id')

    import json
    response = make_response('\n\n'.join(json.dumps(d) for d in data_list))
    response.headers['Content-type'] = 'text/plain'
    return response


def download_search(info):
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
    s += com + ' Elliptic curves downloaded from the LMFDB downloaded on %s.\n'%(mydate)
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [Weierstrass Coefficients]\n'
    s += '\n' + com2
    s += '\n'
    if dltype == 'magma':
        s += 'data := ['
    else:
        s += 'data = ['
    s += '\\\n'
    # reissue saved query here
    res = db_ec().find(ast.literal_eval(info["query"]))
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
                     as_attachment=True,
                     add_etags=False)


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


@ec_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the elliptic curve data over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Completeness', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ec.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@ec_page.route("/Source")
def how_computed_page():
    t = 'Source of the elliptic curve data over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Source', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ec.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ec_page.route("/Labels")
def labels_page():
    t = 'Labels for elliptic curves over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Labels', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='ec.q.lmfdb_label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@ec_page.route('/<conductor>/<iso>/<number>/download/<download_type>')
def ec_code_download(**args):
    response = make_response(ec_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response

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
    Ecode = E.code()
    lang = args['download_type']
    code = "%s %s code for working with elliptic curve %s\n\n" % (Comment[lang],Fullname[lang],label)
    if lang=='gp':
        lang = 'pari'
    for k in sorted_code_names:
        if lang in Ecode[k]:
            code += "\n%s %s: \n" % (Comment[lang],code_names[k])
            code += Ecode[k][lang] + ('\n' if not '\n' in Ecode[k][lang] else '')
    return code

def tor_struct_search_Q(prefill="any"):
    def fix(t):
        return t + ' selected = "yes"' if prefill==t else t
    def cyc(n):
        return [fix("["+str(n)+"]"), "$C_{{{}}}$".format(n)]
    def cyc2(m,n):
        return [fix("[{},{}]".format(m,n)), "$C_{{{}}}\\times C_{{{}}}$".format(m,n)]
    gps = [[fix(""), "any"], [fix("[]"), "trivial"]]
    for n in range(2,13):
        if n!=11:
            gps.append(cyc(n))
    for n in range(1,5):
        gps.append(cyc2(2,2*n))
    return "\n".join(["<select name='torsion_structure'>"] + ["<option value={}>{}</option>".format(a,b) for a,b in gps] + ["</select>"])

# the following allows the preceding function to be used in any template via {{...}}
app.jinja_env.globals.update(tor_struct_search_Q=tor_struct_search_Q)
