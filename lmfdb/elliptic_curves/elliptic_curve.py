# -*- coding: utf-8 -*-
import ast
import os
import re
from six import BytesIO
import tempfile
import time

from flask import render_template, url_for, request, redirect, make_response, send_file
from sage.all import ZZ, QQ, Qp, EllipticCurve, cputime
from sage.databases.cremona import parse_cremona_label, class_to_int

from lmfdb import db
from lmfdb.app import app
from lmfdb.backend.encoding import Json
from lmfdb.utils import (
    web_latex, to_dict, flash_error, display_knowl,
    parse_rational, parse_ints, parse_floats, parse_bracketed_posints, parse_primes,
    SearchArray, TextBox, SelectBox, SubsetBox, SubsetNoExcludeBox, TextBoxWithSelect, ExcludeOnlyBox, CountBox,
    YesNoBox, parse_element_of, parse_bool, search_wrap)
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.ec_stats import get_stats
from lmfdb.elliptic_curves.isog_class import ECisog_class
from lmfdb.elliptic_curves.web_ec import WebEC, match_lmfdb_label, match_cremona_label, split_lmfdb_label, split_cremona_label, weierstrass_eqn_regex, short_weierstrass_eqn_regex, class_lmfdb_label, curve_lmfdb_label, EC_ainvs

q = ZZ['x'].gen()

#########################
#   Data credit
#########################

def ec_credit():
    return 'John Cremona, Enrique  Gonz&aacute;lez Jim&eacute;nez, Robert Pollack, Jeremy Rouse, Andrew Sutherland and others: see <a href={}>here</a> for details'.format(url_for(".how_computed_page"))

#########################
#   Utility functions
#########################

def sorting_label(lab1):
    """
    Provide a sorting key.
    """
    a, b, c = parse_cremona_label(lab1)
    return (int(a), class_to_int(b), int(c))

#########################
#    Top level
#########################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Elliptic Curve labels', url_for(".labels_page"))]

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
    counts = get_stats().counts()

    conductor_list_endpoints = [1, 100, 1000, 10000, 100000, counts['max_N'] + 1]
    conductor_list = ["%s-%s" % (start, end - 1) for start, end in zip(conductor_list_endpoints[:-1],
                                                                       conductor_list_endpoints[1:])]
    rank_list = list(range(counts['max_rank'] + 1))
    torsion_list = list(range(1, 11)) + [12, 16]
    info['rank_list'] = rank_list
    info['torsion_list'] = torsion_list
    info['conductor_list'] = conductor_list
    info['counts'] = counts
    info['stats_url'] = url_for(".statistics")
    t = r'Elliptic Curves over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")), (r'$\Q$', ' ')]
    if err_args.get("err_msg"):
        # this comes from elliptic_curve_jump_error
        flash_error(err_args.pop("err_msg"), err_args.pop("label"))
        return redirect(url_for(".rational_elliptic_curves"))
    return render_template("ec-index.html",
                           info=info,
                           credit=ec_credit(),
                           title=t,
                           bread=bread,
                           learnmore=learnmore_list(),
                           calling_function="ec.rational_elliptic_curves",
                           **err_args)

@ec_page.route("/random")
def random_curve():
    label = db.ec_curves.random(projection=1)['lmfdb_label']
    cond, iso, num = split_lmfdb_label(label)
    return redirect(url_for(".by_triple_label", conductor=cond, iso_label=iso, number=num))

@ec_page.route("/curve_of_the_day")
def todays_curve():
    from datetime import date
    mordells_birthday = date(1888,1,28)
    n = (date.today()-mordells_birthday).days
    label = db.ec_curves.lucky({'number': 1}, offset = n)
    #return render_curve_webpage_by_label(label)
    return redirect(url_for(".by_ec_label", label=label), 307)

@ec_page.route("/stats")
def statistics():
    info = {
        'counts': get_stats().counts(),
        'stats': get_stats().stats(),
    }
    t = r'Elliptic Curves over $\Q$: Statistics'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             (r'$\Q$', url_for(".rational_elliptic_curves")),
             ('Statistics', ' ')]
    return render_template("ec-stats.html", info=info, credit=ec_credit(), title=t, bread=bread, learnmore=learnmore_list())


@ec_page.route("/<int:conductor>/")
def by_conductor(conductor):
    info = to_dict(request.args, search_array=ECSearchArray())
    info['bread'] = [('Elliptic Curves', url_for("ecnf.index")), (r'$\Q$', url_for(".rational_elliptic_curves")), ('%s' % conductor, url_for(".by_conductor", conductor=conductor))]
    info['title'] = r'Elliptic Curves over $\Q$ of Conductor %s' % conductor
    if request.args:
        # if conductor changed, fall back to a general search
        if 'conductor' in request.args and request.args['conductor'] != str(conductor):
            return redirect (url_for(".rational_elliptic_curves", **request.args), 307)
        info['title'] += ' Search Results'
        info['bread'].append(('Search Results',''))
    info['conductor'] = conductor
    return elliptic_curve_search(info)


def elliptic_curve_jump_error(label, args, wellformed_label=False, cremona_label=False, missing_curve=False):
    err_args = {}
    for field in ['conductor', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure']:
        err_args[field] = args.get(field, '')
    err_args['count'] = args.get('count', '100')
    err_args['label'] = label
    if wellformed_label:
        err_args['err_msg'] = "No curve or isogeny class in the database has label %s"
    elif missing_curve:
        err_args['err_msg'] = "The elliptic curve %s is not in the database"
    elif not label:
        err_args['err_msg'] = "Please enter a non-empty label %s"
    else:
        err_args['err_msg'] = r"%s does not define a recognised elliptic curve over $\mathbb{Q}$"
    return rational_elliptic_curves(err_args)

def elliptic_curve_jump(info):
    label = info.get('jump', '').replace(" ", "")
    m = match_lmfdb_label(label)
    if m:
        try:
            return by_ec_label(label)
        except ValueError:
            return elliptic_curve_jump_error(label, info, wellformed_label=True)
    m = match_cremona_label(label)
    if m:
        try:
            return redirect(url_for(".by_ec_label", label=label))
            #return by_ec_label(label)
        except ValueError:
            return elliptic_curve_jump_error(label, info, wellformed_label=True)

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
            lmfdb_label = db.ec_curves.lucky({'ainvs': EC_ainvs(E)}, 'lmfdb_label')
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
    s += com + '   [a1,a2,a3,a4,a6] (Weierstrass Coefficients)\n'
    s += '\n' + com2 + '\n'
    s += 'data ' + ass + ' [' + '\\\n'
    # reissue saved query here
    res = db.ec_curves.search(ast.literal_eval(info["query"]), 'ainvs')
    s += ",\\\n".join([str(ainvs) for ainvs in res])
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
             table=db.ec_curves,
             title='Elliptic Curves Search Results',
             err_title='Elliptic Curve Search Input Error',
             per_page=50,
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             shortcuts={'jump':elliptic_curve_jump,
                        'download':download_search},
             bread=lambda:[('Elliptic Curves', url_for("ecnf.index")),
                           (r'$\Q$', url_for(".rational_elliptic_curves")),
                           ('Search Results', '.')],
             credit=ec_credit)

def elliptic_curve_search(info, query):
    parse_rational(info,query,'jinv','j-invariant')
    parse_ints(info,query,'conductor')
    parse_ints(info,query,'torsion','torsion order')
    parse_ints(info,query,'rank')
    parse_ints(info,query,'sha','analytic order of &#1064;')
    parse_ints(info,query,'num_int_pts','num_int_pts')
    parse_floats(info,query,'regulator','regulator')
    parse_bool(info,query,'semistable','semistable')
    parse_bracketed_posints(info,query,'torsion_structure',maxlength=2,check_divisibility='increasing')
    # speed up slow torsion_structure searches by also setting torsion
    #if 'torsion_structure' in query and not 'torsion' in query:
    #    query['torsion'] = reduce(mul,[int(n) for n in query['torsion_structure']],1)
    if 'include_cm' in info:
        if info['include_cm'] == 'exclude':
            query['cm'] = 0
        elif info['include_cm'] == 'only':
            query['cm'] = {'$ne' : 0}
    #parse_ints(info,query,field='cm_disc',qfield='cm')
    if 'cm_disc' in info:
        query['cm'] = info['cm_disc']
    parse_element_of(info,query,field='isodeg',qfield='isogeny_degrees',split_interval=1000)
    #parse_ints(info,query,field='isodeg',qfield='isogeny_degrees')
    parse_primes(info, query, 'surj_primes', name='maximal primes',
                 qfield='nonmax_primes', mode='exclude')
    parse_primes(info, query, 'nonsurj_primes', name='non-maximal primes',
                 qfield='nonmax_primes',mode=info.get('surj_quantifier'), radical='nonmax_rad')
    parse_primes(info, query, 'bad_primes', name='bad primes',
                 qfield='bad_primes',mode=info.get('bad_quantifier'))
    # The button which used to be labelled Optimal only no/yes"
    # (default no) has been renamed "Curves per isogeny class all/one"
    # (default one) but the only change in behavious is that we no
    # longer treat class 990h (where the optial curve is #3 not #1) as
    # special: the "one" option just restricts to curves whose
    # 'number' is 1.
    if 'optimal' in info and info['optimal'] == 'on':
        query.update({'number':1})

        # Old behaviour was as follows:
        # For all isogeny classes except 990h the optimal curve is number 1, while for class 990h it is number 3.
        # So setting query['number'] = 1 is nearly correct, but fails on 990h3.
        # Instead, we use this more complicated query:
        # query.update({"$or":[{'iso':'990h', 'number':3}, {'iso':{'$ne':'990h'},'number':1}]})

    info['curve_ainvs'] = lambda dbc: str([ZZ(ai) for ai in dbc['ainvs']])
    info['curve_url_LMFDB'] = lambda dbc: url_for(".by_triple_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1], number=dbc['lmfdb_number'])
    info['iso_url_LMFDB'] = lambda dbc: url_for(".by_double_iso_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1])
    info['curve_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['label'])
    info['iso_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['iso'])

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
            label_type = 'label'
        else:
            label_type = 'iso'

        data = db.ec_curves.lucky({label_type: label}, projection=1)
        if data is None:
            return elliptic_curve_jump_error(label, {}, wellformed_label=True, missing_curve=True)
        ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
        iso = data['lmfdb_iso'].split(".")[1]
        if number:
            return render_curve_webpage_by_label(label)
            #return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=data['lmfdb_number']))
        else:
            return render_isogeny_class(label)
            #return redirect(url_for(".by_double_iso_label", conductor=N, iso_label=iso))


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
    label = db.ec_curves.lucky({'ainvs': EC_ainvs(E)},'lmfdb_label')
    if label is None:
        N = E.conductor()
        return elliptic_curve_jump_error(eqn, {'conductor':N}, missing_curve=True)
    return redirect(url_for(".by_ec_label", label=label), 301)

def render_isogeny_class(iso_class):
    class_data = ECisog_class.by_label(iso_class)
    if class_data == "Invalid label":
        return elliptic_curve_jump_error(iso_class, {}, wellformed_label=False)
    if class_data == "Class not found":
        return elliptic_curve_jump_error(iso_class, {}, wellformed_label=True, missing_curve=True)
    class_data.modform_display = url_for(".modular_form_display", label=class_data.lmfdb_iso+"1", number="")

    return render_template("ec-isoclass.html",
                           properties=class_data.properties,
                           info=class_data,
                           code=class_data.code,
                           bread=class_data.bread,
                           credit=ec_credit(),
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
    ainvs = db.ec_curves.lookup(label, 'ainvs', 'lmfdb_label')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})
    E = EllipticCurve(ainvs)
    modform = E.q_eigenform(number)
    modform_string = web_latex(modform)
    return modform_string

# This function is now redundant since we store plots as
# base64-encoded pngs.
@ec_page.route("/plot/<label>")
def plot_ec(label):
    ainvs = db.ec_curves.lookup(label, 'ainvs', 'lmfdb_label')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})
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
    cpt0 = cputime()
    t0 = time.time()
    data = WebEC.by_label(label)
    if data == "Invalid label":
        return elliptic_curve_jump_error(label, {}, wellformed_label=False)
    if data == "Curve not found":
        return elliptic_curve_jump_error(label, {}, wellformed_label=True, missing_curve=True)
    try:
        lmfdb_label = data.lmfdb_label
    except AttributeError:
        return elliptic_curve_jump_error(label, {}, wellformed_label=False)

    data.modform_display = url_for(".modular_form_display", label=lmfdb_label, number="")

    code = data.code()
    code['show'] = {'magma':'','pari':'','sage':''} # use default show names
    T =  render_template("ec-curve.html",
                         properties=data.properties,
                         credit=ec_credit(),
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


@ec_page.route("/download_qexp/<label>/<limit>")
def download_EC_qexp(label, limit):
    N, iso, number = split_lmfdb_label(label)
    if number:
        ainvs = db.ec_curves.lookup(label, 'ainvs', 'lmfdb_label')
    else:
        ainvs = db.ec_curves.lookup(label, 'ainvs', 'lmfdb_iso')
    E = EllipticCurve(ainvs)
    response = make_response(','.join(str(an) for an in E.anlist(int(limit), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response


@ec_page.route("/download_all/<label>")
def download_EC_all(label):
    try:
        N, iso, number = split_lmfdb_label(label)
    except (ValueError,AttributeError):
        return elliptic_curve_jump_error(label, {})
    if number:
        data = db.ec_curves.lookup(label, label_col='lmfdb_label')
        if data is None:
            return elliptic_curve_jump_error(label, {})
        data_list = [data]
    else:
        data_list = list(db.ec_curves.search({'lmfdb_iso': label}, projection=2, sort=['number']))
        if not data_list:
            return elliptic_curve_jump_error(label, {})

    response = make_response('\n\n'.join(Json.dumps(d) for d in data_list))
    response.headers['Content-type'] = 'text/plain'
    return response


@ec_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of the Elliptic Curve data over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             (r'$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Completeness', '')]
    return render_template("single.html", kid='dq.ec.extent',
                           credit=ec_credit(), title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@ec_page.route("/Source")
def how_computed_page():
    t = r'Source of the Elliptic Curve data over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             (r'$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Source', '')]
    return render_template("single.html", kid='dq.ec.source',
                           credit=ec_credit(), title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ec_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of the Elliptic Curve data over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             (r'$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Reliability', '')]
    return render_template("single.html", kid='dq.ec.reliability',
                           credit=ec_credit(), title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@ec_page.route("/Labels")
def labels_page():
    t = r'Labels for Elliptic Curves over $\Q$'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             (r'$\Q$', url_for("ec.rational_elliptic_curves")),
             ('Labels', '')]
    return render_template("single.html", kid='ec.q.lmfdb_label',
                           credit=ec_credit(), title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

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
    def __init__(self):
        cond = TextBox(
            name="conductor",
            label="Conductor",
            knowl="ec.q.conductor",
            example="389",
            example_span="389 or 100-200")
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="ec.rank",
            example="0")
        torsion = TextBox(
            name="torsion",
            label="Torsion order",
            knowl="ec.torsion_order",
            example="2")
        sha = TextBox(
            name="sha",
            label="Analytic order of &#1064;",
            knowl="ec.q.analytic_sha_order",
            example="4")
        surj_primes = TextBox(
            name="surj_primes",
            label="Maximal primes",
            knowl="ec.maximal_galois_rep",
            example="2,3")
        isodeg = TextBox(
            name="isodeg",
            label="Cyclic isogeny degree",
            knowl="ec.isogeny",
            example="16")
        num_int_pts = TextBox(
            name="num_int_pts",
            label="Number of %s" % display_knowl("ec.q.integral_points", "integral points"),
            example="2",
            example_span="2 or 4-15")

        jinv = TextBox(
            name="jinv",
            label="j-invariant",
            knowl="ec.q.j_invariant",
            example="1728",
            example_span="1728 or -4096/11")
        cm = ExcludeOnlyBox(
            name="include_cm",
            label="CM",
            knowl="ec.complex_multiplication")
        tor_opts = ([("", ""),
                     ("[]", "trivial")] +
                    [("[%s]"%n, "C%s"%n) for n in range(2, 13) if n != 11] +
                    [("[2,%s]"%n, "C2&times;C%s"%n) for n in range(2, 10, 2)])
        torsion_struct = SelectBox(
            name="torsion_structure",
            label="Torsion structure",
            knowl="ec.torsion_subgroup",
            options=tor_opts)
        optimal = SelectBox(
            name="optimal",
            label="Curves per isogeny class",
            knowl="ec.isogeny_class",
            options=[("", ""),
                     ("on", "one")])
        surj_quant = SubsetNoExcludeBox(
            name="surj_quantifier")
        nonsurj_primes = TextBoxWithSelect(
            name="nonsurj_primes",
            label="Non-max. $p$",
            short_label="Non-max. $p$",
            knowl="ec.maximal_galois_rep",
            example="2,3",
            select_box=surj_quant)
        bad_quant = SubsetBox(
            name="bad_quantifier")
        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            label="Bad $p$",
            knowl="ec.q.reduction_type",
            example="5,13",
            select_box=bad_quant)
        regulator = TextBox(
            name="regulator",
            label="Regulator",
            knowl="ec.q.regulator",
            example="8.4-9.1")
        semistable = YesNoBox(
            name="semistable",
            label="Semistable",
            example="Yes",
            knowl="ec.semistable")
        cm_opts = [('', ''), ('-3', -3), ('-4', -4), ('-7', -7), ('-8', -8), ('-11', -11), ('-12', -12), ('-16', -16),
                        ('-19', -19), ('-27', -27), ('-28', -28), ('-43', -43), ('-67', -67), ('-163', -163)]
        cm_disc = SelectBox(
            name="cm_disc",
            label="CM discriminant",
            example="-3",
            knowl="ec.complex_multiplication",
            options=cm_opts
            )

        count = CountBox()

        self.browse_array = [
            [cond, jinv],
            [rank, regulator],
            [torsion, torsion_struct],
            [cm_disc, cm],
            [sha, optimal],
            [surj_primes, nonsurj_primes],
            [isodeg, bad_primes],
            [num_int_pts, semistable],
            [count]
            ]

        self.refine_array = [
            [cond, jinv, rank, torsion, torsion_struct],
            [sha, isodeg, surj_primes, nonsurj_primes, bad_primes],
            [num_int_pts, regulator, cm, cm_disc, semistable],
            [optimal]
            ]
