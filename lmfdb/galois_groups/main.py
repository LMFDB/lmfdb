# -*- coding: utf-8 -*-
# This Blueprint is about Galois Groups
# Author: John Jones

import pymongo
ASC = pymongo.ASCENDING
from lmfdb import base
from lmfdb.base import app
from flask import render_template, request, url_for, redirect
from lmfdb.utils import to_dict, list_to_latex_matrix, random_object_from_collection
from lmfdb.search_parsing import clean_input, prep_ranges, parse_bool, parse_ints, parse_count, parse_start
import re
import bson
from lmfdb.galois_groups import galois_groups_page, logger
from sage.all import ZZ, latex, gap

# Test to see if this gap installation knows about transitive groups
# logger = make_logger("GG")

try:
    G = gap.TransitiveGroup(9, 2)
except:
    logger.fatal("It looks like the SPKGes gap_packages and database_gap are not installed on the server.  Please install them via 'sage -i ...' and try again.")

from lmfdb.transitive_group import group_display_short, group_display_pretty, group_knowl_guts, galois_module_knowl_guts, subfield_display, resolve_display, conjclasses, generators, chartable, aliastable, WebGaloisGroup

from lmfdb.WebNumberField import modules2string

GG_credit = 'GAP, Magma, J. Jones, and A. Bartel'

# convert [0,5,21,0,1] to [[1,5],[2,21],[4,1]]
def mult2mult(li):
    ans = []
    for j in range(len(li)):
        if li[j]>0:
            ans.append([j, li[j]])
    return ans


def get_bread(breads=[]):
    bc = [("Galois Groups", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def int_reps_are_complete(intreps):
    for r in intreps:
        if 'complete' in r:
            return r['complete']
    return -1

def galois_group_data(n, t):
    C = base.getDBConnection()
    return group_knowl_guts(n, t, C)


def group_alias_table():
    C = base.getDBConnection()
    return aliastable(C)


def galois_module_data(n, t, index):
    C = base.getDBConnection()
    return galois_module_knowl_guts(n, t, index, C)


@app.context_processor
def ctx_galois_groups():
    return {'group_alias_table': group_alias_table,
            'galois_module_data': galois_module_data}


def group_display_shortC(C):
    def gds(nt):
        return group_display_short(nt[0], nt[1], C)
    return gds

def group_display_prettyC(C):
    def gds(nt):
        return group_display_pretty(nt[0], nt[1], C)
    return gds

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')


@galois_groups_page.route("/<label>")
def by_label(label):
    clean_label = clean_input(label)
    if clean_label != label:
        return redirect(url_for('.by_label', label=clean_label), 301)
    return render_group_webpage({'label': label})


@galois_groups_page.route("/")
def index():
    bread = get_bread()
    if len(request.args) != 0:
        return galois_group_search(**request.args)
    info = {'count': 50}
    info['degree_list'] = range(16)[2:]
    learnmore = [#('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Galois group labels', url_for(".labels_page"))]
    return render_template("gg-index.html", title="Galois Groups", bread=bread, info=info, credit=GG_credit, learnmore=learnmore)

# FIXME: delete or fix this code
# Apparently obsolete code that causes a server error if executed
# @galois_groups_page.route("/search", methods=["GET", "POST"])
# def search():
#    if request.method == "GET":
#        val = request.args.get("val", "no value")
#        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
#        return render_template("gg-search.html", title="Galois Group Search", bread=bread, val=val)
#    elif request.method == "POST":
#        return "ERROR: we always do http get to explicitly display the search parameters"
#    else:
#        return flask.abort(404)


def galois_group_search(**args):
    info = to_dict(args)
    if info.get('jump_to'):
        return redirect(url_for('.by_label', label=info['jump_to']).strip(), 301)
    bread = get_bread([("Search results", ' ')])
    C = base.getDBConnection()
    query = {}

    def includes_composite(s):
        s = s.replace(' ','').replace('..','-')
        for interval in s.split(','):
            if '-' in interval[1:]:
                ix = interval.index('-',1)
                a,b = int(interval[:ix]), int(interval[ix+1:])
                if b == a:
                    if a != 1 and not a.is_prime():
                        return True
                if b > a and b > 3:
                    return True
            else:
                a = ZZ(interval)
                if a != 1 and not a.is_prime():
                    return True
    try:
        parse_ints(info,query,'n','degree')
        parse_ints(info,query,'t')
        for param in ('cyc', 'solv', 'prim', 'parity'):
            parse_bool(info,query,param,minus_one_to_zero=(param != 'parity'))
        degree_str = prep_ranges(info.get('n'))
        info['show_subs'] = degree_str is None or (LIST_RE.match(degree_str) and includes_composite(degree_str))
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info, bread)

    count = parse_count(info, 50)
    start = parse_start(info)

    res = C.transitivegroups.groups.find(query).sort([('n', pymongo.ASCENDING), ('t', pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['groups'] = res
    info['group_display'] = group_display_prettyC(C)
    info['report'] = "found %s groups" % nres
    info['yesno'] = yesno
    info['wgg'] = WebGaloisGroup.from_data
    info['start'] = start
    info['number'] = nres
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    return render_template("gg-search.html", info=info, title="Galois Group Search Result", bread=bread, credit=GG_credit)


def yesno(val):
    if val:
        return 'Yes'
    return 'No'


def render_group_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        label = label.replace('t', 'T')
        C = base.getDBConnection()
        data = C.transitivegroups.groups.find_one({'label': label})
        if data is None:
            bread = get_bread([("Search error", ' ')])
            info['err'] = "Group " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        data['label_raw'] = label.lower()
        title = 'Galois Group: ' + label
        wgg = WebGaloisGroup.from_data(data)
        n = data['n']
        t = data['t']
        data['yesno'] = yesno
        order = data['order']
        data['orderfac'] = latex(ZZ(order).factor())
        orderfac = latex(ZZ(order).factor())
        data['ordermsg'] = "$%s=%s$" % (order, latex(orderfac))
        if order == 1:
            data['ordermsg'] = "$1$"
        if ZZ(order).is_prime():
            data['ordermsg'] = "$%s$ (is prime)" % order
        pgroup = len(ZZ(order).prime_factors()) < 2
        if n == 1:
            G = gap.SmallGroup(n, t)
        else:
            G = gap.TransitiveGroup(n, t)
        if ZZ(order) < ZZ('10000000000'):
            ctable = chartable(n, t)
        else:
            ctable = 'Group too large'
        data['gens'] = generators(n, t)
        if n == 1 and t == 1:
            data['gens'] = 'None needed'
        data['chartable'] = ctable
        data['parity'] = "$%s$" % data['parity']
        data['cclasses'] = conjclasses(G, n)
        data['subinfo'] = subfield_display(C, n, data['subs'])
        data['resolve'] = resolve_display(C, data['resolve'])
        data['otherreps'] = wgg.otherrep_list()
        ae = wgg.arith_equivalent()
        if ae>0:
            if ae>1:
                data['arith_equiv'] = r'A number field with this Galois group has %d <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> fields.'% ae
            else:
                data['arith_equiv'] = r'A number field with this Galois group has exactly one <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> field.'
        else:
            data['arith_equiv'] = r'A number field with this Galois group has no <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> fields.'
        if len(data['otherreps']) == 0:
            data['otherreps']="There is no other low degree representation."
        query={'galois': bson.SON([('n', n), ('t', t)])}
        C = base.getDBConnection()
        intreps = C.transitivegroups.Gmodules.find({'n': n, 't': t}).sort('index', pymongo.ASCENDING)
        # turn cursor into a list
        intreps = [z for z in intreps]
        if len(intreps) > 0:
            data['int_rep_classes'] = [str(z[0]) for z in intreps[0]['gens']]
            for onerep in intreps:
                onerep['gens']=[list_to_latex_matrix(z[1]) for z in onerep['gens']]
            data['int_reps'] = intreps
            data['int_reps_complete'] = int_reps_are_complete(intreps)
            dcq = data['moddecompuniq']
            if dcq[0] == 0:
                data['decompunique'] = 0
            else:
                data['decompunique'] = dcq[0]
                data['isoms'] = [[mult2mult(z[0]), mult2mult(z[1])] for z in dcq[1]]
                data['isoms'] = [[modules2string(n,t,z[0]), modules2string(n,t,z[1])] for z in data['isoms']]
                #print dcq[1]
                #print data['isoms']

        friends = []
        one = C.numberfields.fields.find_one(query)
        if one:
            friends.append(('Number fields with this Galois group', url_for('number_fields.number_field_render_webpage')+"?galois_group=%dT%d" % (n, t) )) 
        prop2 = [('Label', label),
            ('Order', '\(%s\)' % order),
            ('n', '\(%s\)' % data['n']),
            ('Cyclic', yesno(data['cyc'])),
            ('Abelian', yesno(data['ab'])),
            ('Solvable', yesno(data['solv'])),
            ('Primitive', yesno(data['prim'])),
            ('$p$-group', yesno(pgroup)),
        ]
        pretty = group_display_pretty(n,t,C)
        if len(pretty)>0:
            prop2.extend([('Group:', pretty)])
            info['pretty_name'] = pretty
        data['name'] = re.sub(r'_(\d+)',r'_{\1}',data['name'])
        data['name'] = re.sub(r'\^(\d+)',r'^{\1}',data['name'])
        info.update(data)

        bread = get_bread([(label, ' ')])
        return render_template("gg-show-group.html", credit=GG_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends)


def search_input_error(info, bread):
    return render_template("gg-search.html", info=info, title='Galois Group Search Input Error', bread=bread)

@galois_groups_page.route("/random")
def random_group():
    label = random_object_from_collection(base.getDBConnection().transitivegroups.groups)['label']
    return redirect(url_for(".by_label", label=label), 301)

@galois_groups_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Galois group data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Galois group labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.gg.extent',
                           credit=GG_credit, title=t, bread=bread, 
                           learnmore=learnmore)

@galois_groups_page.route("/Labels")
def labels_page():
    t = 'Labels for Galois groups'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='gg.label',learnmore=learnmore, credit=GG_credit, title=t, bread=bread)

@galois_groups_page.route("/Source")
def how_computed_page():
    t = 'Source of the Galois group data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                #('Source of the data', url_for(".how_computed_page")),
                ('Galois group labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.gg.source',
                           credit=GG_credit, title=t, bread=bread, 
                           learnmore=learnmore)

