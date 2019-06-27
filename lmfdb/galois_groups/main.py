# -*- coding: utf-8 -*-
# This Blueprint is about Galois Groups
# Author: John Jones

import re

from flask import render_template, request, url_for, redirect
from sage.all import ZZ, latex, gap

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    list_to_latex_matrix, flash_error, comma,
    clean_input, prep_ranges, parse_bool, parse_ints, parse_bracketed_posints, parse_restricted,
    search_wrap)
from lmfdb.number_fields.web_number_field import modules2string
from lmfdb.galois_groups import galois_groups_page, logger
from .transitive_group import (
    group_display_pretty, small_group_display_knowl, galois_module_knowl_guts,
    subfield_display, resolve_display, chartable,
    group_alias_table, WebGaloisGroup)

# Test to see if this gap installation knows about transitive groups
# logger = make_logger("GG")

try:
    G = gap.TransitiveGroup(9, 2)
except:
    logger.fatal("It looks like the SPKGes gap_packages and database_gap are not installed on the server.  Please install them via 'sage -i ...' and try again.")

GG_credit = 'GAP, Magma, J. Jones, and A. Bartel'

# convert [0,5,21,0,1] to [[1,5],[2,21],[4,1]]
def mult2mult(li):
    ans = []
    for j in range(len(li)):
        if li[j]>0:
            ans.append([j, li[j]])
    return ans

def learnmore_list():
    return [('Completeness of the data', url_for(".cande")),
            ('Source of the data', url_for(".source")),
            ('Reliability of the data', url_for(".reliability")),
            ('Galois group labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

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

def galois_module_data(n, t, index):
    return galois_module_knowl_guts(n, t, index)


@app.context_processor
def ctx_galois_groups():
    return {'group_alias_table': group_alias_table,
            'galois_module_data': galois_module_knowl_guts}

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
        return galois_group_search(request.args)
    info = {'count': 50}
    info['degree_list'] = range(16)[2:]
    return render_template("gg-index.html", title="Galois Groups", bread=bread, info=info, credit=GG_credit, learnmore=learnmore_list())

# For the search order-parsing
def make_order_key(order):
    order1 = int(ZZ(order).log(10))
    return '%03d%s'%(order1,str(order))

@search_wrap(template="gg-search.html",
             table=db.gps_transitive,
             title='Galois Group Search Results',
             err_title='Galois Group Search Input Error',
             learnmore=learnmore_list,
             shortcuts={'jump_to': lambda info:redirect(url_for('.by_label', label=info['jump_to']).strip(), 301)},
             bread=lambda: get_bread([("Search Results", ' ')]),
             credit=lambda: GG_credit)
def galois_group_search(info, query):
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
    parse_ints(info,query,'n','degree')
    parse_ints(info,query,'t')
    parse_ints(info,query,'order')
    parse_bracketed_posints(info, query, qfield='gapidfull', split=False, exactlength=2, keepbrackets=True, name='GAP id', field='gapid')
    for param in ('cyc', 'solv', 'prim'):
        parse_bool(info, query, param, process=int, blank=['0','Any'])
    parse_restricted(info,query,'parity',allowed=[1,-1],process=int,blank=['0','Any'])
    if 'order' in query and 'n' not in query:
        query['__sort__'] = ['order', 'gapid', 'n', 't']

    degree_str = prep_ranges(info.get('n'))
    info['show_subs'] = degree_str is None or (LIST_RE.match(degree_str) and includes_composite(degree_str))
    info['group_display'] = group_display_pretty
    info['yesno'] = yesno
    info['wgg'] = WebGaloisGroup.from_data

def yesno(val):
    if val:
        return 'Yes'
    return 'No'


def render_group_webpage(args):
    data = {}
    if 'label' in args:
        label = clean_input(args['label'])
        label = label.replace('t', 'T')
        data = db.gps_transitive.lookup(label)
        if data is None:
            if re.match(r'^\d+T\d+$', label):
                flash_error("Group %s was not found in the database.", label)
            else:
                flash_error("%s is not a valid label for a Galois group.", label)
            return redirect(url_for(".index"))
        data['label_raw'] = label.lower()
        title = 'Galois Group: ' + label
        wgg = WebGaloisGroup.from_nt(data['n'], data['t'])
        data['wgg'] = wgg
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
        if wgg.num_conjclasses() < 50:
            data['cclasses'] = wgg.conjclasses()
        if ZZ(order) < ZZ(10000000) and wgg.num_conjclasses() < 21:
            data['chartable'] = chartable(n, t)
        data['gens'] = wgg.generator_string()
        if n == 1 and t == 1:
            data['gens'] = 'None needed'
        data['num_cc'] = comma(wgg.num_conjclasses())
        data['parity'] = "$%s$" % data['parity']
        data['subinfo'] = subfield_display(n, data['subfields'])
        data['resolve'] = resolve_display(data['quotients'])
        if data['gapid'] == 0:
            data['gapid'] = "Data not available"
        else:
            data['gapid'] = small_group_display_knowl(int(data['order']),
                                                      int(data['gapid']),
                                                      str([int(data['order']), int(data['gapid'])]))
        data['otherreps'] = wgg.otherrep_list()
        ae = data['arith_equiv']
        if ae>0:
            if ae>1:
                data['arith_equiv'] = r'A number field with this Galois group has %d <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> fields.'% ae
            else:
                data['arith_equiv'] = r'A number field with this Galois group has exactly one <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> field.'
        elif ae > -1:
            data['arith_equiv'] = r'A number field with this Galois group has no <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> fields.'
        else:
            data['arith_equiv'] = r'Data on whether or not a number field with this Galois group has <a knowl="nf.arithmetically_equivalent", title="arithmetically equivalent">arithmetically equivalent</a> fields has not been computed.'
        intreps = list(db.gps_gmodules.search({'n': n, 't': t}))
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
        if db.nf_fields.exists({'degree': n, 'galt': t}):
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
        pretty = group_display_pretty(n,t)
        if len(pretty)>0:
            prop2.extend([('Group:', pretty)])
            data['pretty_name'] = pretty
        data['name'] = re.sub(r'_(\d+)',r'_{\1}',data['name'])
        data['name'] = re.sub(r'\^(\d+)',r'^{\1}',data['name'])

        bread = get_bread([(label, ' ')])
        return render_template("gg-show-group.html", credit=GG_credit, title=title, bread=bread, info=data, properties2=prop2, friends=friends, KNOWL_ID="gg.%s"%data['label_raw'], learnmore=learnmore_list())


def search_input_error(info, bread):
    return render_template("gg-search.html", info=info, title='Galois Group Search Input Error', bread=bread, learnmore=learnmore_list())

@galois_groups_page.route("/random")
def random_group():
    label = db.gps_transitive.random()
    return redirect(url_for(".by_label", label=label), 307)

@galois_groups_page.route("/Completeness")
def cande():
    t = 'Completeness of Galois Group Data'
    bread = get_bread([("Completeness", )])
    learnmore = learnmore_list_remove('Completeness')
    return render_template("single.html", kid='rcs.cande.gg',
                           credit=GG_credit, title=t, bread=bread, 
                           learnmore=learnmore)

@galois_groups_page.route("/Labels")
def labels_page():
    t = 'Labels for Galois Groups'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='gg.label',
           learnmore=learnmore_list_remove('label'), 
           credit=GG_credit, title=t, bread=bread)

@galois_groups_page.route("/Source")
def source():
    t = 'Source of the Galois Group Data'
    bread = get_bread([("Source", '')])
    return render_template("single.html", kid='rcs.source.gg',
                           credit=GG_credit, title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'))

@galois_groups_page.route("/Reliability")
def reliability():
    t = 'Reliability of the Galois Group Data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.rigor.gg',
                           credit=GG_credit, title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'))

