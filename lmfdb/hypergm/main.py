# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones 

import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input, image_callback
from lmfdb.number_fields.number_field import parse_list
from sage.all import ZZ, var, PolynomialRing, QQ, latex
from lmfdb.hypergm import hypergm_page, hgm_logger

from lmfdb.transitive_group import *

HGM_credit = 'D. Roberts and J. Jones'

# Helper functions

# A and B are lists, tn and td are num/den for t
def ab_label(A,B):
    return "A" + ".".join(map(str,A)) + "_B" + ".".join(map(str,B))
    
def make_label(A,B,tn,td):
    AB_str = ab_label(A,B)
    t = QQ( "%d/%d" % (tn, td))
    t_str = "/t%s.%s" % (str(t.numerator()), str(t.denominator()))
    return AB_str + t_str

def get_bread(breads=[]):
    bc = [("Motives", url_for("motive.index")), ("Hypergeometric", url_for("motive.index2")), ("$\Q$", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def display_t(tn, td):
    t = QQ("%d/%d" % (tn, td))
    if t.denominator() == 1:
        return str(t.numerator())
    return "%s/%s" % (str(t.numerator()), str(t.denominator()))

# Returns a string of val if val = 0, 1, -1, or version with p factored out otherwise
def factor_out_p(val, p):
    if val == 0 or val == -1:
        return str(val)
    if val==1:
        return '+1'
    s = 1
    if val<0:
        s = -1
        val = -val
    ord = ZZ(val).valuation(p)
    val = val/p**ord
    out = ''
    if s == -1:
        out += '-'
    else:
        out += '+'
    if ord==1:
        out +=  str(p)
    elif ord>1:
        out +=  '%d^{%d}' % (p, ord)
    if val>1:
        if ord ==1:
            out += r'\cdot '
        out += str(val)
    return out

# c is a list of coefficients
def poly_with_factored_coeffs(c, p):
    c = [factor_out_p(b,p) for b in c]
    out = ''
    for j in range(len(c)):
        xpow = 'x^{'+ str(j) +'}'
        if j == 0:
            xpow = ''
        elif j==1:
            xpow = 'x'
        if c[j] != '0':
            if c[j] == '+1':
                if j==0:
                    out += '+1'
                else:
                    out += '+'+xpow
            elif c[j] == '-1':
                if j==0:
                    out += '-1'
                else:
                    out += '-'+ xpow
            else:
                if j==0:
                    out += c[j]
                else:
                    out += c[j] + xpow
    if out[0] == '+':
        out = out[1:]
    return out


LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')
IF_RE = re.compile(r'^\[\]|(\[\d+(,\d+)*\])$')  # invariant factors
PAIR_RE = re.compile(r'^\[\d+,\d+\]$')


@hypergm_page.route("/")
def index():
    bread = get_bread()
    if len(request.args) != 0:
        return hgm_search(**request.args)
    info = {'count': 20}
    return render_template("hgm-index.html", title="Hypergeometric Motives over $\Q$", bread=bread, credit=HGM_credit, info=info)



@hypergm_page.route("/plot/circle/<AB>")
def hgm_family_circle_image(AB):
    A,B = AB.split("_")
    from plot import circle_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = circle_image(A, B)
    return image_callback(G)

@hypergm_page.route("/plot/linear/<AB>")
def hgm_family_linear_image(AB):
    # piecewise linear, as opposed to piecewise constant
    A,B = AB.split("_")
    from plot import piecewise_linear_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = piecewise_linear_image(A, B)
    return image_callback(G)

@hypergm_page.route("/plot/constant/<AB>")
def hgm_family_constant_image(AB):
    # piecewise constant
    A,B = AB.split("_")
    from plot import piecewise_constant_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = piecewise_constant_image(A, B)
    return image_callback(G)


@hypergm_page.route("/<label>")
def by_family_label(label):
    return render_hgm_family_webpage({'label': label})

@hypergm_page.route("/<label>/<t>")
def by_label(label, t):
    return render_hgm_webpage({'label': label+'_'+t})

@hypergm_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("hgm-search.html", title="Hypergeometric Motive Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return flask.redirect(404)
    

def hgm_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results", url_for('.search'))])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        return render_hgm_webpage({'label': info['jump_to']})

    # t, generic, irreducible
    # 'A', 'B', 'hodge'
    for param in ['A', 'B']:
        if (param == 't' and PAIR_RE.match(info['t'])) or (param == 'A' and IF_RE.match(info[param])) or (param == 'B' and IF_RE.match(info[param])):
            query[param] = parse_list(info[param])
        else:
            print "Bad input"
            
    for param in ['degree','weight','sign']:
        if info.get(param):
            info[param] = clean_input(info[param])
            if param == 'gal':
                try:
                    gcs = complete_group_codes(info[param])
                    if len(gcs) == 1:
                        tmp = ['gal', list(gcs[0])]
                    if len(gcs) > 1:
                        tmp = [{'gal': list(x)} for x in gcs]
                        tmp = ['$or', tmp]
                except NameError as code:
                    info['err'] = 'Error parsing input for A: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
                    return search_input_error(info, bread)
            else:
                ran = info[param]
                ran = ran.replace('..', '-')
                if LIST_RE.match(ran):
                    tmp = parse_range2(ran, param)
                else:
                    names = {'weight': 'weight', 'degree': 'degree', 'sign': 'sign'}
                    info['err'] = 'Error parsing input for the %s.  It needs to be an integer (such as 5), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 2,3,8 or 3-5, 7, 8-11).' % names[param]
                    return search_input_error(info, bread)
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

    count_default = 20
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
    if info.get('paging'):
        try:
            paging = int(info['paging'])
            if paging == 0:
                start = 0
        except:
            pass

    # logger.debug(query)
    res = C.hgm.motives.find(query).sort([('cond', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['motives'] = res
    info['number'] = nres
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    info['make_label'] = make_label
    info['display_t'] = display_t

    return render_template("hgm-search.html", info=info, title="Hypergeometric Motive over $\Q$ Search Result", bread=bread, credit=HGM_credit)


def render_hgm_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        data = C.hgm.motives.find_one({'label': label})
        if data is None:
            bread = get_bread([("Search error", url_for('.search'))])
            info['err'] = "Motive " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        title = 'Hypergeometric Motive:' + label
        A = data['A']
        B = data['B']
        tn,td = data['t']
        t = latex(QQ(str(tn)+'/'+str(td)))
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
        locinfo = data['locinfo']
        for j in range(len(locinfo)):
            locinfo[j] = [primes[j]] + locinfo[j]
            locinfo[j][2] = poly_with_factored_coeffs(locinfo[j][2], primes[j])
        hodge = data['hodge']
        prop2 = [
            ('Degree', '\(%s\)' % data['degree']),
            ('Weight',  '\(%s\)' % data['weight']),
            ('Conductor', '\(%s\)' % data['cond']),
        ]
        info.update({
                    'A': A,
                    'B': B,
                    't': t,
                    'degree': data['degree'],
                    'weight': data['weight'],
                    'sign': data['sign'],
                    'sig': data['sig'],
                    'hodge': hodge,
                    'cond': data['cond'],
                    'req': data['req'],
                    'locinfo': locinfo
                    })
        AB_data, t_data = data["label"].split("_t")
        #AB_data = data["label"].split("_t")[0]
        friends = [("Motive family "+AB_data.replace("_"," "), url_for(".by_family_label", label = AB_data))]
        friends.append(('L-function', url_for("l_functions.l_function_hgm_page", label=AB_data, t='t'+t_data)))
#        if rffriend != '':
#            friends.append(('Discriminant root field', rffriend))


        bread = get_bread([(label, ' ')])
        return render_template("hgm-show-motive.html", credit=HGM_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends)

def render_hgm_family_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        data = C.hgm.families.find_one({'label': label})
        if data is None:
            bread = get_bread([("Search error", url_for('.search'))])
            info['err'] = "Family of hypergeometric motives " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        title = 'Hypergeometric Motive Family:' + label
        A = data['A']
        B = data['B']
        hodge = data['hodge']
        prop2 = [
            ('Degree', '\(%s\)' % data['degree']),
            ('Weight',  '\(%s\)' % data['weight'])
        ]
        info.update({
                    'A': A,
                    'B': B,
                    'degree': data['degree'],
                    'weight': data['weight'],
                    'hodge': hodge,
                    'gal2': data['gal2'],
                    'gal3': data['gal3'],
                    'gal5': data['gal5'],
                    'gal7': data['gal7'],
                    })
        friends = []
#        friends = [('Galois group', "/GaloisGroup/%dT%d" % (gn, gt))]
#        if unramfriend != '':
#            friends.append(('Unramified subfield', unramfriend))
#        if rffriend != '':
#            friends.append(('Discriminant root field', rffriend))

        info.update({"plotcircle":  url_for(".hgm_family_circle_image", AB  =  "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
        info.update({"plotlinear": url_for(".hgm_family_linear_image", AB  = "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
        info.update({"plotconstant": url_for(".hgm_family_constant_image", AB  = "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
        bread = get_bread([(label, ' ')])
        return render_template("hgm-show-family.html", credit=HGM_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends)


def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return(sl)


def search_input_error(info, bread):
    return render_template("hgm-search.html", info=info, title='Motive Search Input Error', bread=bread)
