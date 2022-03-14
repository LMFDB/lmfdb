#i -*- coding: utf-8 -*-
# This Blueprint is about Galois Groups
# Author: John Jones

import re

from flask import abort, render_template, request, url_for, redirect
from sage.all import ZZ, latex, gap

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    list_to_latex_matrix, flash_error, comma, latex_comma, to_dict, display_knowl,
    clean_input, prep_ranges, parse_bool, parse_ints, parse_galgrp,
    SearchArray, TextBox, TextBoxNoEg, YesNoBox, ParityBox, CountBox,
    StatsDisplay, totaler, proportioners, prop_int_pretty,
    search_wrap, redirect_no_cache)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MultiProcessedCol, MathCol, CheckCol, SearchCol
from lmfdb.api import datapage
from lmfdb.number_fields.web_number_field import modules2string
from lmfdb.galois_groups import galois_groups_page, logger
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from .transitive_group import (
    galois_module_knowl_guts, group_display_short,
    subfield_display, resolve_display, chartable,
    group_alias_table, WebGaloisGroup, knowl_cache)

# Test to see if this gap installation knows about transitive groups
# logger = make_logger("GG")

try:
    G = gap.TransitiveGroup(9, 2)
except Exception:
    logger.fatal("It looks like the SPKGes gap_packages and database_gap are not installed on the server.  Please install them via 'sage -i ...' and try again.")

# convert [0,5,21,0,1] to [[1,5],[2,21],[4,1]]
def mult2mult(li):
    return [[j, li_j] for j, li_j in enumerate(li) if li_j > 0]


def learnmore_list():
    return [('Source and acknowledgments', url_for(".source")),
            ('Completeness of the data', url_for(".cande")),
            ('Reliability of the data', url_for(".reliability")),
            ('Galois group labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def get_bread(breads=[]):
    bc = [("Galois groups", url_for(".index"))]
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
        return redirect(url_for_label(clean_label), 301)
    return render_group_webpage({'label': label})

def url_for_label(label):
    return url_for(".by_label", label=label)

@galois_groups_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=GalSearchArray(), stats=GaloisStats())
    if request.args:
        return galois_group_search(info)
    info['degree_list'] = list(range(1, 48))
    return render_template("gg-index.html", title="Galois groups", bread=bread, info=info, learnmore=learnmore_list())

# For the search order-parsing
def make_order_key(order):
    order1 = int(ZZ(order).log(10))
    return '%03d%s'%(order1,str(order))

gg_columns = SearchColumns([
    LinkCol("label", "gg.label", "Label", url_for_label, default=True),
    SearchCol("pretty", "gg.simple_name", "Name", default=True),
    MathCol("order", "group.order", "Order", default=True, align="right"),
    MathCol("parity", "gg.parity", "Parity", default=True, align="right"),
    CheckCol("solv", "group.solvable", "Solvable", default=True),
    MathCol("nilpotency", "group.nilpotent", "Nil. class", short_title="nilpotency class"),
    MathCol("num_conj_classes", "gg.conjugacy_classes", "Conj. classes", short_title="conjugacy classes"),
    MultiProcessedCol("subfields", "gg.subfields", "Subfields",
                      ["subfields", "cache"],
                      lambda subs, cache: WebGaloisGroup(None, {"subfields": subs}).subfields(cache=cache),
                      default=lambda info: info["show_subs"]),
    MultiProcessedCol("siblings", "gg.other_representations", "Low Degree Siblings",
                      ["siblings", "bound_siblings", "cache"],
                      lambda sibs, bnd, cache: WebGaloisGroup(None, {"siblings":sibs, "bound_siblings":bnd}).otherrep_list(givebound=False, cache=cache),
                      default=True)
],
    db_cols=["bound_siblings", "gapid", "label", "name", "order", "parity", "pretty", "siblings", "solv", "subfields", "nilpotency", "num_conj_classes"])
gg_columns.dummy_download = True
gg_columns.below_download = r"<p>Results are complete for degrees $\leq 23$.</p>"

def gg_postprocess(res, info, query):
    # We want to cache latex forms both for the results and for any groups that show up as siblings or subfields
    others = sum([[tuple(pair[0]) for pair in rec["siblings"]] for rec in res], [])
    if info["show_subs"]:
        others += sum([[tuple(pair[0]) for pair in rec["subfields"]] for rec in res], [])
    others = sorted(set(others))
    others = ["T".join(str(c) for c in nt) for nt in others]
    others = list(db.gps_transitive.search({"label": {"$in": others}}, ["label", "order", "gapid", "pretty"]))
    cache = knowl_cache(results=res+others)
    for rec in res:
        pretty = cache[rec["label"]].get("pretty")
        if not pretty:
            pretty = rec["name"]
        rec["pretty"] = pretty
        rec["cache"] = cache
    return res

@search_wrap(table=db.gps_transitive,
             title='Galois group search results',
             err_title='Galois group search input error',
             columns=gg_columns,
             url_for_label=url_for_label,
             postprocess=gg_postprocess,
             learnmore=learnmore_list,
             bread=lambda: get_bread([("Search results", ' ')]))
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
    if info.get('jump','').strip():
        jump_list = ["1T1", "2T1", "3T1", "4T1", "4T2", "5T1", "6T1", "7T1",
          "8T1", "8T2", "8T3", "8T5", "9T1", "9T2", "10T1", "11T1", "12T1",
          "12T2", "12T5", "13T1", "14T1", "15T1", "16T1", "16T2", "16T3",
          "16T4", "16T5", "16T7", "16T8", "16T14", "17T1", "18T1", "18T2",
          "19T1", "20T1", "20T2", "20T3", "21T1", "22T1", "23T1", "24T1",
          "24T2", "24T3", "24T4", "24T5", "24T6", "24T8", "25T1", "25T2",
          "26T1", "27T1", "27T2", "27T4", "28T1", "28T2", "28T3", "29T1",
          "30T1", "31T1", "32T32", "32T33", "32T34", "32T35", "32T36",
          "32T37", "32T38", "32T39", "32T40", "32T41", "32T42", "32T43",
          "32T44", "32T45", "32T46", "32T47", "32T48", "32T49", "32T50",
          "32T51", "33T1", "34T1", "35T1", "36T1", "36T2", "36T3", "36T4",
          "36T7", "36T9", "37T1", "38T1", "39T1", "40T1", "40T2", "40T3",
          "40T4", "40T5", "40T7", "40T8", "40T13", "41T1", "42T1", "43T1",
          "44T1", "44T2", "44T3", "45T1", "45T2", "46T1", "47T1"]
        strip_label = info.get('jump','').strip().upper()
        # If the user entered a simple label
        if re.match(r'^\d+T\d+$',strip_label):
            return redirect(url_for_label(strip_label), 301)
        try:
            parse_galgrp(info, query, qfield=['label','n'],
                name='a Galois group label', field='jump', list_ok=False,
                err_msg="It needs to be a transitive group in nTj notation, such as 5T1, a GAP id, such as [4,1], or a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>")
        except ValueError:
            return redirect(url_for('.index'))

        if query.get('label', '') in jump_list:
            return redirect(url_for_label(query['label']), 301)

        else: # convert this to a regular search
            info['gal'] = info['jump']
    parse_ints(info,query,'n','degree')
    parse_ints(info,query,'t')
    parse_ints(info,query,'order')
    parse_ints(info,query,'arith_equiv')
    parse_ints(info,query,'nilpotency')
    parse_galgrp(info, query, qfield=['label','n'], name='Galois group', field='gal')
    for param in ('cyc', 'solv', 'prim'):
        parse_bool(info, query, param, process=int, blank=['0','Any'])
    if info.get("parity") == "even":
        query["parity"] = 1
    elif info.get("parity") == "odd":
        query["parity"] = -1
    #parse_restricted(info,query,'parity',allowed=[1,-1],process=int,blank=['0','Any'])

    degree_str = prep_ranges(info.get('n'))
    info['show_subs'] = degree_str is None or (LIST_RE.match(degree_str) and includes_composite(degree_str))

def yesno(val):
    if val:
        return 'yes'
    return 'no'


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
        title = 'Galois group: ' + label
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
            data['gapid'] = "not available"
        else:
            gp_label = f"{data['order']}.{data['gapid']}"
            data['gapid'] = abstract_group_display_knowl(gp_label, gp_label)
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
        if intreps:
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
        if db.lf_fields.exists({'n': n, 'galT': t}):
            friends.append(('$p$-adic fields with this Galois group', url_for('local_fields.index')+"?gal=%dT%d" % (n, t) ))
        prop2 = [('Label', label),
            ('Degree', prop_int_pretty(data['n'])),
            ('Order', prop_int_pretty(order)),
            ('Cyclic', yesno(data['cyc'])),
            ('Abelian', yesno(data['ab'])),
            ('Solvable', yesno(data['solv'])),
            ('Primitive', yesno(data['prim'])),
            ('$p$-group', yesno(pgroup)),
        ]
        pretty = group_display_short(n,t, emptyifnotpretty=True)
        if len(pretty)>0:
            prop2.extend([('Group:', pretty)])
            data['pretty_name'] = pretty
        data['name'] = re.sub(r'_(\d+)',r'_{\1}',data['name'])
        data['name'] = re.sub(r'\^(\d+)',r'^{\1}',data['name'])
        data['nilpotency'] = '$%s$' % data['nilpotency']
        if data['nilpotency'] == '$-1$':
            data['nilpotency'] += ' (not nilpotent)'
        downloads = [('Underlying data', url_for(".gg_data", label=label))]

        bread = get_bread([(label, ' ')])
        return render_template(
            "gg-show-group.html",
            title=title,
            bread=bread,
            info=data,
            properties=prop2,
            friends=friends,
            downloads=downloads,
            KNOWL_ID="gg.%s"%label,
            learnmore=learnmore_list())

@galois_groups_page.route("/data/<label>")
def gg_data(label):
    if not re.fullmatch(r'\d+T\d+', label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Transitive group data - {label}"
    return datapage(label, "gps_transitive", title=title, bread=bread)

@galois_groups_page.route("/random")
@redirect_no_cache
def random_group():
    return url_for_label(db.gps_transitive.random())

@galois_groups_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "gg",
        db.gps_transitive,
        url_for_label=url_for_label,
        title=r"Some interesting Galois groups",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list()
    )

@galois_groups_page.route("/stats")
def statistics():
    title = "Galois groups: statistics"
    bread = get_bread([("Statistics", " ")])
    return render_template("display_stats.html", info=GaloisStats(), title=title, bread=bread, learnmore=learnmore_list())

@galois_groups_page.route("/Completeness")
def cande():
    t = 'Completeness of Galois group data'
    bread = get_bread([("Completeness", )])
    learnmore = learnmore_list_remove('Completeness')
    return render_template("single.html", kid='rcs.cande.gg',
                           title=t, bread=bread,
                           learnmore=learnmore)

@galois_groups_page.route("/Labels")
def labels_page():
    t = 'Labels for Galois groups'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='gg.label',
           learnmore=learnmore_list_remove('label'),
           title=t, bread=bread)

@galois_groups_page.route("/Source")
def source():
    t = 'Source and acknowledgments for Galois group pages'
    bread = get_bread([("Source", '')])
    return render_template("multi.html", kids=['rcs.source.gg',
                                               'rcs.ack.gg',
                                               'rcs.cite.gg'],
                           title=t, bread=bread,
                           learnmore=learnmore_list_remove('Source'))

@galois_groups_page.route("/Reliability")
def reliability():
    t = 'Reliability of Galois group data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.rigor.gg',
                           title=t, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))

class GalSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    sorts = [("", "degree", ["n", "t"]),
             ("gp", "order", ["order", "gapid", "n", "t"]),
             ("nilpotency", "nilpotency class", ["nilpotency", "n", "t"]),
             ("num_conj_classes", "num. conjugacy classes", ["num_conj_classes", "order", "gapid", "n", "t"])]
    jump_example = "8T14"
    jump_egspan = "e.g. 8T14"
    jump_knowl = "gg.search_input"
    jump_prompt = "Label, name, or identifier"
    def __init__(self):
        parity = ParityBox(
            name="parity",
            label="Parity",
            knowl="gg.parity")
        cyc = YesNoBox(
            name="cyc",
            label="Cyclic",
            knowl="group.cyclic")
        solv = YesNoBox(
            name="solv",
            label="Solvable",
            knowl="group.solvable")
        prim = YesNoBox(
            name="prim",
            label="Primitive",
            knowl="gg.primitive")

        n = TextBox(
            name="n",
            label="Degree",
            knowl="gg.degree",
            example="6",
            example_span="6 or 4,6 or 2..5 or 4,6..8")
        t = TextBox(
            name="t",
            label="$T$-number",
            knowl="gg.tnumber",
            example="3",
            example_span="3 or 4,6 or 2..5 or 4,6..8")
        order = TextBox(
            name="order",
            label="Order",
            knowl="group.order",
            example="6",
            example_span="6 or 4,6 or 2..35 or 4,6..80")
        gal = TextBoxNoEg(
            name="gal",
            label="Group",
            knowl="group",
            example_span_colspan=8,
            example="[8,3]",
            example_span="list of %s, e.g. [8,3] or [16,7], group names from the %s, e.g. C5 or S12, and %s, e.g., 7T2 or 11T5" % (
                display_knowl("group.small_group_label", "GAP id's"),
                display_knowl("nf.galois_group.name", "list of group labels"),
                display_knowl("gg.label", "transitive group labels")))
        nilpotency = TextBox(
            name="nilpotency",
            label="Nilpotency class",
            knowl="group.nilpotent",
            example="1..100",
            example_span="-1, or 1..3")
        arith_equiv = TextBox(
            name="arith_equiv",
            label="Equivalent siblings",
            knowl="gg.arithmetically_equiv_input",
            example="1",
            example_span="1 or 2,3 or 1..5 or 1,3..10")
        count = CountBox()

        self.browse_array = [[n, parity], [t, cyc], [order, solv], [nilpotency, prim], [gal], [arith_equiv], [count]]

        self.refine_array = [[parity, cyc, solv, prim, arith_equiv], [n, t, order, gal, nilpotency]]

def yesone(s):
    return "yes" if s in ["yes", 1] else "no"

def fixminus1(s):
    return "not computed" if s == -1 else s

def eqyesone(col):
    def inner(s):
        return "%s=%s" % (col, yesone(s))
    return inner

def undominus1(s):
    if isinstance(s,int):
        return "arith_equiv=%s" % s
    return "arith_equiv=-1"

class GaloisStats(StatsDisplay):
    table = db.gps_transitive
    baseurl_func = ".index"

    stat_list = [
        {"cols": ["n", "order"],
         "totaler": totaler(),
         "proportioner": proportioners.per_row_total},
        {"cols": ["solv", "n"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["prim", "n"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["arith_equiv","n"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["n", "nilpotency"],
         "totaler": totaler(),
         "proportioner": proportioners.per_row_total},
    ]
    knowls = {"n": "gg.degree",
              "order": "group.order",
              "nilpotency": "group.nilpotent",
              "arith_equiv": "gg.arithmetically_equivalent",
              "solv": "group.solvable",
              "prim": "gg.primitive",
    }
    top_titles = {"nilpotency": "nilpotency classes",
                  "solv": "solvability",
                  "arith_equiv": "number of arithmetic equivalent siblings",
                  "prim": "primitivity"}
    short_display = {"n": "degree",
                     "nilpotency": "nilpotency class",
                     "solv": "solvable",
                     "arith_equiv": "arithmetic equivalent count",
                     "prim": "primitive",
    }
    formatters = {"solv": yesone,
                  "prim": yesone,
                  "arith_equiv": fixminus1}
    query_formatters = {"solv": eqyesone("solv"),
                        "prim": eqyesone("prim"),
                        "arith_equiv": undominus1}
    buckets = {
        "n": ["1-3", "4-7", "8", "9-11", "12", "13-15", "16", "17-23", "24", "25-31", "32", "33-35", "36", "37-39", "40", "41-47"],
        "order": ["1-15", "16-31", "32-63", "64-127", "128-255", "256-511", "512-1023", "1024-2047", "2048-65535", "65536-40000000000", "40000000000-"]
    }

    def __init__(self):
        self.ngroups = db.gps_transitive.count()

    @property
    def summary(self):
        return r"The database currently contains $%s$ transitive subgroups of $S_n$, including all subgroups (up to conjugacy) for $n \le 47$ and $n \ne 32$.  Among the $2{,}801{,}324$ groups in degree $32$, all those with order less than $512$ or greater than $40{,}000{,}000{,}000$ are included." % latex_comma(self.ngroups)

    @property
    def short_summary(self):
        return r'The database current contains $%s$ groups, including all transitive subgroups of $S_n$ (up to conjugacy) for $n \le 47$ and $n \ne 32$.  Here are some <a href="%s">further statistics</a>.' % (latex_comma(self.ngroups), url_for(".statistics"))
