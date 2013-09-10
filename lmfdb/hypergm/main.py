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
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ
from lmfdb.hypergm import hypergm_page, hgm_logger

from lmfdb.transitive_group import *

HGM_credit = 'D. Roberts and J. Jones'


def get_bread(breads=[]):
    bc = [("Hypergeometric Motives", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


def display_poly(coeffs):
    return web_latex(coeff_to_poly(coeffs))

def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')


@hypergm_page.route("/")
def index():
    bread = get_bread()
    if len(request.args) != 0:
        return local_field_search(**request.args)
    info = {'count': 20}
    return render_template("hgm-index.html", title="Hypergeometric Motives", bread=bread, credit=HGM_credit, info=info)


@hypergm_page.route("/<label>")
def by_label(label):
    return render_field_webpage({'label': label})


@hypergm_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("hgm-search.html", title="Local Number Field Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return flask.redirect(404)


def local_field_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results", url_for('.search'))])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        return render_field_webpage({'label': info['jump_to']})

    for param in ['p', 'n', 'c', 'e', 'gal']:
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
                    info['err'] = 'Error parsing input for Galois group: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
                    return search_input_error(info, bread)
            else:
                ran = info[param]
                ran = ran.replace('..', '-')
                if LIST_RE.match(ran):
                    tmp = parse_range2(ran, param)
                else:
                    names = {'p': 'prime p', 'n': 'degree', 'c':
                             'discriminant exponent c', 'e': 'ramification index e'}
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
    res = C.localfields.fields.find(query).sort([('p', pymongo.ASCENDING), (
        'n', pymongo.ASCENDING), ('c', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['fields'] = res
    info['number'] = nres
    info['group_display'] = group_display_shortC(C)
    info['display_poly'] = format_coeffs
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    return render_template("hgm-search.html", info=info, title="Local Number Field Search Result", bread=bread, credit=HGM_credit)


def render_field_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        data = C.localfields.fields.find_one({'label': label})
        if data is None:
            bread = get_bread([("Search error", url_for('.search'))])
            info['err'] = "Field " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        title = 'Local Number Field:' + label
        polynomial = coeff_to_poly(data['coeffs'])
        p = data['p']
        e = data['e']
        f = data['f']
        cc = data['c']
        GG = data['gal']
        gn = GG[0]
        gt = GG[1]
        prop2 = [
            ('Base', '\(\Q_{%s}\)' % p),
            ('Degree', '\(%s\)' % data['n']),
            ('e', '\(%s\)' % e),
            ('f', '\(%s\)' % f),
            ('c', '\(%s\)' % cc),
            ('Galois group', group_display_short(gn, gt, C)),
        ]
        Pt = PolynomialRing(QQ, 't')
        Pyt = PolynomialRing(Pt, 'y')
        eisenp = Pyt(str(data['eisen']))
        unramp = Pyt(str(data['unram']))
        # Look up the unram poly so we can link to it
        unramdata = C.localfields.fields.find_one({'p': p, 'n': f, 'c': 0})
        if len(unramdata) > 0:
            unramfriend = "/LocalNumberField/%s" % unramdata['label']
        else:
            logger.fatal("Cannot find unramified field!")
            unramfriend = ''
        rfdata = C.localfields.fields.find_one({'p': p, 'n': {'$in': [1, 2]}, 'rf': data['rf']})
        if rfdata is None:
            logger.fatal("Cannot find discriminant root field!")
            rffriend = ''
        else:
            rffriend = "/LocalNumberField/%s" % rfdata['label']

        info.update({
                    'polynomial': web_latex(polynomial),
                    'n': data['n'],
                    'p': data['p'],
                    'c': data['c'],
                    'e': data['e'],
                    'f': data['f'],
                    't': data['t'],
                    'u': data['u'],
                    'rf': printquad(data['rf'], p),
                    'hw': data['hw'],
                    'slopes': show_slopes(data['slopes']),
                    'gal': group_display_knowl(gn, gt, C),
                    'gt': gt,
                    'inertia': group_display_inertia(data['inertia'], C),
                    'unram': web_latex(unramp),
                    'eisen': web_latex(eisenp),
                    'gms': data['gms'],
                    'aut': data['aut'],
                    })
        friends = [('Galois group', "/GaloisGroup/%dT%d" % (gn, gt))]
        if unramfriend != '':
            friends.append(('Unramified subfield', unramfriend))
        if rffriend != '':
            friends.append(('Discriminant root field', rffriend))

        bread = get_bread([(label, ' ')])
        return render_template("hgm-show-motive.html", credit=HGM_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends)


def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return(sl)


def printquad(code, p):
    if code == [1, 0]:
        return('$\Q_{%s}$' % p)
    if code == [1, 1]:
        return('$\Q_{%s}(\sqrt{*})$' % p)
    if code == [-1, 1]:
        return('$\Q_{%s}(\sqrt{-*})$' % p)
    s = code[0]
    if code[1] == 1:
        s = str(s) + '*'
    return('$\Q_{' + str(p) + '}(\sqrt{' + str(s) + '})$')


def search_input_error(info, bread):
    return render_template("hgm-search.html", info=info, title='Local Field Search Input Error', bread=bread)
