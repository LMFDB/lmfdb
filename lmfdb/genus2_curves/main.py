# -*- coding: utf-8 -*-

import re
from ast import literal_eval

from flask import render_template, url_for, request, redirect, abort
from sage.all import ZZ

from lmfdb import db
from lmfdb.utils import (
    to_dict, comma, flash_error, display_knowl,
    parse_bool, parse_ints, parse_bracketed_posints, parse_bracketed_rats, parse_primes,
    search_wrap,
    Downloader,
    SearchArray, TextBox, SelectBox, TextBoxWithSelect,
    StatsDisplay, formatters)
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.genus2_curves import g2c_page
from lmfdb.genus2_curves.web_g2c import WebG2C, min_eqn_pretty, st0_group_name

credit_string = "Andrew Booker, Edgar Costa, Jeroen Sijsling, Michael Stoll, Andrew Sutherland, John Voight, Raymond van Bommel, Dan Yasaki"

###############################################################################
# List and dictionaries needed routing and searching
###############################################################################

# lists determine display order in drop down lists, dictionary key is the
# database entry, dictionary value is the display value
st_group_list = ['J(C_2)', 'J(C_4)', 'J(C_6)', 'J(D_2)', 'J(D_3)', 'J(D_4)',
        'J(D_6)', 'J(T)', 'J(O)', 'C_{2,1}', 'C_{6,1}', 'D_{2,1}', 'D_{3,2}',
        'D_{4,1}', 'D_{4,2}', 'D_{6,1}', 'D_{6,2}', 'O_1', 'E_1', 'E_2', 'E_3',
        'E_4', 'E_6', 'J(E_1)', 'J(E_2)', 'J(E_3)', 'J(E_4)', 'J(E_6)',
        'F_{a,b}', 'F_{ac}', 'N(G_{1,3})', 'G_{3,3}', 'N(G_{3,3})', 'USp(4)']
st_group_dict = {a:a for a in st_group_list}

# End_QQbar tensored with RR determines ST0 (which is the search parameter):
real_geom_end_alg_list = ['M_2(C)', 'M_2(R)', 'C x C', 'C x R', 'R x R', 'R']
real_geom_end_alg_to_ST0_dict = {
        'M_2(C)':'U(1)',
        'M_2(R)':'SU(2)',
        'C x C':'U(1) x U(1)',
        'C x R':'U(1) x SU(2)',
        'R x R':'SU(2) x SU(2)',
        'R':'USp(4)'
        }

# End_QQbar tensored with QQ
geom_end_alg_list = [ 'Q', 'RM', 'CM', 'QM', 'Q x Q', 'CM x Q', 'CM x CM', 'M_2(Q)', 'M_2(CM)']
geom_end_alg_dict = { x:x for x in geom_end_alg_list }

aut_grp_list = ['[2,1]', '[4,1]', '[4,2]', '[6,2]', '[8,3]', '[12,4]']
aut_grp_dict = {
        '[2,1]':'C2',
        '[4,1]':'C4',
        '[4,2]':'V4',
        '[6,2]':'C6',
        '[8,3]':'D4',
        '[12,4]':'D6'
        }

geom_aut_grp_list = ['[2,1]', '[4,2]', '[8,3]', '[10,2]', '[12,4]', '[24,8]', '[48,29]']
geom_aut_grp_dict = {
        '[2,1]':'C2',
        '[4,2]':'V4',
        '[8,3]':'D4',
        '[10,2]':'C10',
        '[12,4]':'D6',
        '[24,8]':'C3:D4',
        '[48,29]':'GL(2,3)'}

###############################################################################
# Routing for top level and random_curve
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".source_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Genus 2 curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


@g2c_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@g2c_page.route("/Q/")
def index_Q():
    if len(request.args) > 0:
        return genus2_curve_search(request.args)
    info = {'stats': G2C_stats()}
    info["search_array"] = G2CSearchArray()
    info["stats_url"] = url_for(".statistics")
    info["curve_url"] = lambda label: url_for_curve_label(label)
    curve_labels = ('169.a.169.1', '277.a.277.1', '1116.a.214272.1','1369.a.50653.1', '11664.a.11664.1', '563011.a.563011.1')
    info["curve_list"] = [{'label': label, 'url': url_for_curve_label(label)} for label in curve_labels]
    info["conductor_list"] = ('1-499', '500-999', '1000-99999', '100000-1000000')
    info["discriminant_list"] = ('1-499', '500-999', '1000-99999', '100000-1000000')
    #info["st_group_list"] = st_group_list
    #info["st_group_dict"] = st_group_dict
    #info["real_geom_end_alg_list"] = real_geom_end_alg_list
    #info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    #info["aut_grp_list"] = aut_grp_list
    #info["aut_grp_dict"] = aut_grp_dict
    #info["geom_aut_grp_list"] = geom_aut_grp_list
    #info["geom_aut_grp_dict"] = geom_aut_grp_dict
    #info["geom_end_alg_list"] = geom_end_alg_list
    #info["geom_end_alg_dict"] = geom_end_alg_dict
    title = r'Genus 2 Curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), (r'$\Q$', ' '))
    return render_template("g2c_browse.html", info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread)

@g2c_page.route("/Q/random/")
def random_curve():
    label = db.g2c_curves.random()
    return redirect(url_for_curve_label(label), 307)

###############################################################################
# Curve and isogeny class pages
###############################################################################

@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/<int:num>")
def by_url_curve_label(cond, alpha, disc, num):
    label = str(cond)+"."+alpha+"."+str(disc)+"."+str(num)
    return render_curve_webpage(label)

@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/")
def by_url_isogeny_class_discriminant(cond, alpha, disc):
    data = to_dict(request.args)
    clabel = str(cond)+"."+alpha
    # if the isogeny class is not present in the database, return a 404 (otherwise title and bread crumbs refer to a non-existent isogeny class)
    if not db.g2c_curves.exists({'class':clabel}):
        return abort(404, 'Genus 2 isogeny class %s not found in database.'%clabel)
    data['title'] = 'Genus 2 Curves in Isogeny Class %s of Discriminant %s' % (clabel,disc)
    data['bread'] = [('Genus 2 Curves', url_for(".index")),
        (r'$\Q$', url_for(".index_Q")),
        ('%s' % cond, url_for(".by_conductor", cond=cond)),
        ('%s' % alpha, url_for(".by_url_isogeny_class_label", cond=cond, alpha=alpha)),
        ('%s' % disc, url_for(".by_url_isogeny_class_discriminant", cond=cond, alpha=alpha, disc=disc))]
    if len(request.args) > 0:
        # if conductor or discriminant changed, fall back to a general search
        if ('cond' in request.args and request.args['cond'] != str(cond)) or \
           ('abs_disc' in request.args and request.args['abs_disc'] != str(disc)):
            return redirect (url_for(".index", **request.args), 307)
        data['title'] += ' Search Results'
        data['bread'].append(('Search Results',''))
    data['cond'] = cond
    data['class'] = clabel
    data['abs_disc'] = disc
    return genus2_curve_search(data)

@g2c_page.route("/Q/<int:cond>/<alpha>/")
def by_url_isogeny_class_label(cond, alpha):
    return render_isogeny_class_webpage(str(cond)+"."+alpha)

@g2c_page.route("/Q/<int:cond>/")
def by_conductor(cond):
    data = to_dict(request.args)
    data['title'] = 'Genus 2 Curves of Conductor %s' % cond
    data['bread'] = [('Genus 2 Curves', url_for(".index")), (r'$\Q$', url_for(".index_Q")), ('%s' % cond, url_for(".by_conductor", cond=cond))]
    if len(request.args) > 0:
        # if conductor changed, fall back to a general search
        if 'cond' in request.args and request.args['cond'] != str(cond):
            return redirect (url_for(".index", **request.args), 307)
        data['title'] += ' Search Results'
        data['bread'].append(('Search Results',''))
    data['cond'] = cond
    return genus2_curve_search(data)

@g2c_page.route("/Q/<label>")
def by_label(label):
    # handles curve, isogeny class, and Lhash labels
    return genus2_curve_search({'jump':label})

def render_curve_webpage(label):
    try:
        g2c = WebG2C.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("g2c_curve.html",
                           properties=g2c.properties,
                           credit=credit_string,
                           info={'aut_grp_dict':aut_grp_dict,'geom_aut_grp_dict':geom_aut_grp_dict},
                           data=g2c.data,
                           code=g2c.code,
                           bread=g2c.bread,
                           learnmore=learnmore_list(),
                           title=g2c.title,
                           friends=g2c.friends,
                           KNOWL_ID="g2c.%s"%label)

def render_isogeny_class_webpage(label):
    try:
        g2c = WebG2C.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("g2c_isogeny_class.html",
                           properties=g2c.properties,
                           credit=credit_string,
                           data=g2c.data,
                           bread=g2c.bread,
                           learnmore=learnmore_list(),
                           title=g2c.title,
                           friends=g2c.friends,
                           KNOWL_ID="g2c.%s"%label)

def url_for_curve_label(label):
    slabel = label.split(".")
    return url_for(".by_url_curve_label", cond=slabel[0], alpha=slabel[1], disc=slabel[2], num=slabel[3])

def url_for_isogeny_class_label(label):
    slabel = label.split(".")
    return url_for(".by_url_isogeny_class_label", cond=slabel[0], alpha=slabel[1])

def class_from_curve_label(label):
    return '.'.join(label.split(".")[:2])

################################################################################
# Searching
################################################################################

def genus2_jump(info):
    jump = info["jump"].strip()
    if re.match(r'^\d+\.[a-z]+\.\d+\.\d+$',jump):
        return redirect(url_for_curve_label(jump), 301)
    else:
        if re.match(r'^\d+\.[a-z]+$', jump):
            return redirect(url_for_isogeny_class_label(jump), 301)
        else:
            # Handle direct Lhash input
            if re.match(r'^\#\d+$',jump) and ZZ(jump[1:]) < 2**61:
                c = db.g2c_curves.lucky({'Lhash': jump[1:].strip()}, projection="class")
                if c:
                    return redirect(url_for_isogeny_class_label(c), 301)
                else:
                    errmsg = "hash %s not found"
            else:
                errmsg = "%s is not a valid genus 2 curve or isogeny class label"
        flash_error(errmsg, jump)
    return redirect(url_for(".index"))

class G2C_download(Downloader):
    table = db.g2c_curves
    title = 'Genus 2 curves'
    columns = 'eqn'
    column_wrappers = {'eqn':literal_eval}
    data_format = ['[[f coeffs],[h coeffs]]']
    data_description = 'defining the hyperelliptic curve y^2+h(x)y=f(x).'
    function_body = {'magma':['R<x>:=PolynomialRing(Rationals());',
                              'return [HyperellipticCurve(R![c:c in r[1]],R![c:c in r[2]]):r in data];'],
                     'sage':['R.<x>=PolynomialRing(QQ)',
                             'return [HyperellipticCurve(R(r[0]),R(r[1])) for r in data]'],
                     'gp':['[apply(Polrev,c)|c<-data];']}

@search_wrap(template="g2c_search_results.html",
             table=db.g2c_curves,
             title='Genus 2 Curve Search Results',
             err_title='Genus 2 Curves Search Input Error',
             shortcuts={'jump':genus2_jump,
                        'download':G2C_download()},
             projection=['label','eqn','st_group','is_gl2_type','is_simple_geom','analytic_rank'],
             cleaners={"class": lambda v: class_from_curve_label(v["label"]),
                       "equation_formatted": lambda v: min_eqn_pretty(literal_eval(v.pop("eqn"))),
                       "st_group_link": lambda v: st_link_by_name(1,4,v.pop('st_group'))},
             bread=lambda:[('Genus 2 Curves', url_for(".index")),
                           (r'$\Q$', url_for(".index_Q")),
                           ('Search Results', '.')],
             learnmore=learnmore_list,
             credit=lambda:credit_string,
             url_for_label=lambda label: url_for(".by_label", label=label)
             )
def genus2_curve_search(info, query):
    info["search_array"] = G2CSearchArray()
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    info["geom_end_alg_list"] = geom_end_alg_list
    info["geom_end_alg_dict"] = geom_end_alg_dict
    parse_ints(info,query,'abs_disc','absolute discriminant')
    parse_bool(info,query,'is_gl2_type','is of GL2-type')
    parse_bool(info,query,'has_square_sha','has square Sha')
    parse_bool(info,query,'locally_solvable','is locally solvable')
    parse_bool(info,query,'is_simple_geom','is geometrically simple')
    parse_ints(info,query,'cond','conductor')
    if info.get('analytic_sha') == "None":
        query['analytic_sha'] = None;
    else:
        parse_ints(info,query,'analytic_sha','analytic order of sha')
    parse_ints(info,query,'num_rat_pts','rational points')
    parse_ints(info,query,'num_rat_wpts','rational Weierstrass points')
    parse_bracketed_posints(info, query, 'torsion', 'torsion structure', maxlength=4,check_divisibility="increasing")
    parse_ints(info,query,'torsion_order','torsion order')
    if 'torsion' in query and not 'torsion_order' in query:
        t_o = 1
        for n in query['torsion']:
            t_o *= int(n)
        query['torsion_order'] = t_o
    if 'torsion' in query:
        query['torsion_subgroup'] = str(query['torsion']).replace(" ","")
        query.pop('torsion') # search using string key, not array of ints
    geom_inv_type = info.get('geometric_invariants_type', 'igusa_clebsch_inv')
    if geom_inv_type == 'igusa_clebsch_inv':
        invlength = 4
    elif geom_inv_type == 'igusa_inv':
        invlength = 5
    else:
        invlength = 3
    parse_bracketed_rats(info,query,'geometric_invariants',qfield=geom_inv_type,exactlength=invlength,split=False,keepbrackets=True)
    parse_ints(info,query,'two_selmer_rank','2-Selmer rank')
    parse_ints(info,query,'analytic_rank','analytic rank')
    # G2 invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
    if 'g20' in info and 'g21' in info and 'g22' in info:
        query['g2_inv'] = "['%s','%s','%s']"%(info['g20'], info['g21'], info['g22'])
    if 'class' in info:
        query['class'] = info['class']
    for fld in ('st_group', 'real_geom_end_alg', 'aut_grp_id', 'geom_aut_grp_id', 'geom_end_alg'):
        if info.get(fld): query[fld] = info[fld]
    if info.get('bad_quantifier') == 'exactly':
        mode = 'exact'
    elif info.get('bad_quantifier') == 'exclude':
        mode = 'complement'
    elif info.get('bad_quantifier') == 'subset':
        mode = 'subsets'
    else:
        mode = 'append'
    parse_primes(info, query, 'bad_primes', name='bad primes',qfield='bad_primes',mode=mode)
    info["curve_url"] = lambda label: url_for_curve_label(label)
    info["class_url"] = lambda label: url_for_isogeny_class_label(label)

################################################################################
# Statistics
################################################################################

class G2C_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for genus 2 curves over Q
    """
    def __init__(self):
        self.ncurves = comma(db.g2c_curves.count())
        self.max_D = comma(db.g2c_curves.max('abs_disc'))
        self.disc_knowl = display_knowl('g2c.abs_discriminant', title = "absolute discriminant")

    @property
    def short_summary(self):
        stats_url = url_for(".statistics")
        g2c_knowl = display_knowl('g2c.g2curve', title='genus 2 curves')
        return r'The database currently contains %s %s over $\Q$ of %s up to %s.  Here are some <a href="%s">further statistics</a>.' % (self.ncurves, g2c_knowl, self.disc_knowl, self.max_D, stats_url)

    @property
    def summary(self):
        nclasses = comma(db.lfunc_instances.count({'type':'G2Q'}))
        return 'The database currently contains %s genus 2 curves in %s isogeny classes, with %s at most %s.' % (self.ncurves, nclasses, self.disc_knowl, self.max_D)

    table = db.g2c_curves
    baseurl_func = ".index_Q"
    knowls = {'num_rat_pts': 'g2c.num_rat_pts',
              'num_rat_wpts': 'g2c.num_rat_wpts',
              'aut_grp_id': 'g2c.aut_grp',
              'geom_aut_grp_id': 'g2c.geom_aut_grp',
              'analytic_rank': 'g2c.analytic_rank',
              'two_selmer_rank': 'g2c.two_selmer_rank',
              'analytic_sha': 'g2c.analytic_sha',
              'has_square_sha': 'g2c.has_square_sha',
              'locally_solvable': 'g2c.locally_solvable',
              'is_gl2_type': 'g2c.gl2type',
              'real_geom_end_alg': 'g2c.st_group_identity_component',
              'st_group': 'g2c.st_group',
              'torsion_order': 'g2c.torsion_order'}
    row_titles = {'num_rat_pts': 'rational points',
                  'num_rat_wpts': 'Weierstrass points',
                 'aut_grp_id': 'automorphism group',
                  'geom_aut_grp_id': 'automorphism group',
                  'two_selmer_rank': '2-Selmer rank',
                  'analytic_sha': 'analytic order of &#1064;',
                  'has_square_sha': 'has square &#1064;',
                  'is_gl2_type': 'is of GL2-type',
                  'real_geom_end_alg': 'identity component',
                  'st_group': 'Sato-Tate group',
                  'torsion_order': 'torsion order'}
    top_titles = {'num_rat_pts': 'rational points',
                  'num_rat_wpts': 'rational Weierstrass points',
                  'aut_grp_id': r'$\mathrm{Aut}(X)$',
                  'geom_aut_grp_id': r'$\mathrm{Aut}(X_{\overline{\mathbb{Q}}})$',
                  'analytic_sha': 'analytic order of &#1064;',
                  'has_square_sha': 'squareness of &#1064;',
                  'locally_solvable': 'local solvability',
                  'is_gl2_type': r'$\mathrm{GL}_2$-type',
                  'real_geom_end_alg': 'Sato-Tate group identity components',
                  'st_group': 'Sato-Tate groups',
                  'torsion_order': 'torsion subgroup orders'}
    formatters = {'aut_grp_id': lambda x: aut_grp_dict[x],
                  'geom_aut_grp_id': lambda x: geom_aut_grp_dict[x],
                  'has_square_sha': formatters.boolean,
                  'is_gl2_type': formatters.boolean,
                  'real_geom_end_alg': lambda x: "\\("+st0_group_name(x)+"\\)",
                  'st_group': lambda x: st_link_by_name(1,4,x)}
    query_formatters = {'aut_grp_id': lambda x: 'aut_grp_id=%s' % x,
                        'geom_aut_grp_id': lambda x: 'geom_aut_grp_id=%s' % x,
                        'real_geom_end_alg': lambda x: 'real_geom_end_alg=%s' % x,
                        'st_group': lambda x: 'st_group=%s' % x,
                        }

    stat_list = [
        {'cols': 'num_rat_pts', 'totaler': {'avg': True}},
        {'cols': 'num_rat_wpts', 'totaler': {'avg': True}},
        {'cols': 'aut_grp_id'},
        {'cols': 'geom_aut_grp_id'},
        {'cols': 'analytic_rank', 'totaler': {'avg': True}},
        {'cols': 'two_selmer_rank', 'totaler': {'avg': True}},
        {'cols': 'has_square_sha'},
        {'cols': 'analytic_sha', 'totaler': {'avg': True}},
        {'cols': 'locally_solvable'},
        {'cols': 'is_gl2_type'},
        {'cols': 'real_geom_end_alg'},
        {'cols': 'st_group'},
        {'cols': 'torsion_order', 'totaler': {'avg': True}},
    ]

@g2c_page.route("/Q/stats")
def statistics():
    title = r'Genus 2 curves over $\Q$: Statistics'
    bread = (('Genus 2 Curves', url_for(".index")), (r'$\Q$', url_for(".index_Q")), ('Statistics', ' '))
    return render_template("display_stats.html", info=G2C_stats(), credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())



@g2c_page.route("/Q/Completeness")
def completeness_page():
    t = r'Completeness of Genus 2 Curve Data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), (r'$\Q$', url_for(".index")),('Completeness',''))
    return render_template("single.html", kid='rcs.cande.g2c',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@g2c_page.route("/Q/Source")
def source_page():
    t = r'Source of Genus 2 Curve Data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), (r'$\Q$', url_for(".index")),('Source',''))
    return render_template("single.html", kid='rcs.source.g2c',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@g2c_page.route("/Q/Reliability")
def reliability_page():
    t = r'Reliability of Genus 2 Curve Data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), (r'$\Q$', url_for(".index")),('Reliability',''))
    return render_template("single.html", kid='rcs.rigor.g2c',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@g2c_page.route("/Q/Labels")
def labels_page():
    t = r'Labels for Genus 2 Curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\\Q$', url_for(".index")),('Labels',''))
    return render_template("single.html", kid='g2c.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))



class G2CSearchArray(SearchArray):
    def __init__(self):
        geometric_invariants_type = SelectBox(
            name="geometric_invariants_type",
            width=100,
            options=[("", "Igusa-Clebsh"), ("igusa_inv", "Igusa"), ("g2_inv", "G2")],
        )

        geometric_invariants = TextBoxWithSelect(
            name="geometric_invariants",
            knowl="g2c.geometric_invariants",
            label=r"\(\overline{\Q}\)-invariants",
            example="[8,3172,30056,-692224]",
            select_box=geometric_invariants_type,
            width=4 * 190 - 30,
            colspan=(1, 4, 1),
            example_col=False,
        )  # the last 1 is irrelevant

        conductor = TextBox(
            name="cond",
            knowl="ag.conductor",
            label="Conductor",
            example="169",
            example_span="169, 100-1000",
        )

        discriminant = TextBox(
            name="abs_disc",
            knowl="g2c.abs_discriminant",
            label="Absolute Discriminant",
            short_label="Discriminant",
            example="169",
            example_span="169, 0-1000",
        )

        rational_points = TextBox(
            name="num_rat_pts",
            knowl="g2c.num_rat_pts",
            label="Rational points*",
            example="1",
            example_span="0, 20-26",
        )

        rational_weirstrass_points = TextBox(
            name="num_rat_wpts",
            knowl="g2c.num_rat_wpts",
            label="Rational Weierstrass points",
            short_label="Weierstrass",
            example="1",
            example_span="1, 0-6",
        )

        torsion_order = TextBox(
            name="torsion_order",
            knowl="g2c.torsion_order",
            label="Torsion order",
            example="2",
        )

        torsion_structure = TextBox(
            name="torsion_structure",
            knowl="g2c.torsion_structure",
            label="Torsion structure",
            short_label="Torsion",
            example="[2,2,2]",
        )

        two_selmer_rank = TextBox(
            name="two_selmer_rank",
            knowl="g2c.two_selmer_rank",
            label="2-Selmer rank",
            example="1",
        )

        analytic_sha = TextBox(
            name="analytic_sha",
            knowl="g2c.analytic_sha",
            label="Analytic order of &#1064;*",
            short_label="Analytic &#1064;*",
            example="2",
        )

        analytic_rank = TextBox(
            name="analytic_rank",
            knowl="g2c.analytic_rank",
            label="Analytic rank*",
            example="1",
        )

        bad_quantifier = SelectBox(
            name="bad_quantifier",
            width=85,
            options=[
                ("", "include"),
                ("exclude", "exclude"),
                ("exactly", "exactly"),
                ("subset", "subset"),
            ],
        )

        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            knowl="g2c.good_reduction",
            label="Bad primes",
            short_label=r"Bad \(p\)",
            example="5,13",
            select_box=bad_quantifier,
        )

        is_gl2_type = SelectBox(
            name="is_gl2_type",
            knowl="g2c.gl2type",
            label="$\GL_2$-type",
            options=[("", ""), ("True", "True"), ("False", "False")],
        )

        st_group = SelectBox(
            name="st_group",
            knowl="g2c.st_group",
            label="Sato-Tate group",
            short_label=r"\(\mathrm{ST}\)",
            options=([("", "")] + [(elt, st_group_dict[elt]) for elt in st_group_list]),
        )

        st_group_identity_component = SelectBox(
            name="real_geom_end_alg",
            knowl="g2c.st_group_identity_component",
            label="Sate-Tate identity component",
            short_label=r"\(\mathrm{ST}^0\)",
            options=(
                [("", "")]
                + [
                    (elt, real_geom_end_alg_to_ST0_dict[elt])
                    for elt in real_geom_end_alg_list
                ]
            ),
        )

        Q_automorphism = SelectBox(
            name="aut_grp_id",
            knowl="g2c.aut_grp",
            label=r"\(\Q\)-automorphism group",
            short_label=r"\(\mathrm{Aut}(X)\)",
            options=([("", "")] + [(elt, aut_grp_dict[elt]) for elt in aut_grp_list]),
        )

        geometric_automorphism = SelectBox(
            name="geom_aut_grp_id",
            knowl="g2c.aut_grp",
            label=r"\(\overline{\Q}\)-automorphism group",
            short_label=r"\(\mathrm{Aut}(X_{\overline{\Q}})\)",
            options=(
                [("", "")]
                + [(elt, geom_aut_grp_dict[elt]) for elt in geom_aut_grp_list]
            ),
        )

        geometric_endomorphism = SelectBox(
            name="geom_end_alg",
            knowl="g2c.geom_end_alg",
            label=r"\(\overline{\Q}\)-endomorphism algebra",
            short_label=r"\(\overline{\Q}\)-end algebra",
            options=(
                [("", "")]
                + [(elt, geom_end_alg_dict[elt]) for elt in geom_end_alg_list]
            ),
        )

        locally_solvable = SelectBox(
            name="locally_solvable",
            knowl="g2c.locally_solvable",
            label="Locally solvable",
            options=[("", ""), ("True", "True"), ("False", "False")],
        )

        has_square_sha = SelectBox(
            name="has_square_sha",
            knowl="g2c.analytic_sha",
            label=r"Order of &#1064; is square*",
            short_label=r"Square &#1064;*",
            options=[("", ""), ("True", "True"), ("False", "False")],
        )

        geometrically_simple = SelectBox(
            name="is_simple_geom",
            knowl="ag.geom_simple",
            label="Geometrically simple",
            short_label=r"\(\overline{\Q}\)-simple",
            options=[("", ""), ("True", "True"), ("False", "False")],
        )

        count = TextBox(
            "count", label="Results to display", example=50, example_col=False
        )

        browse_array = [
            [geometric_invariants],
            [conductor, is_gl2_type],
            [discriminant, st_group],
            [rational_points, st_group_identity_component],
            [rational_weirstrass_points, Q_automorphism],
            [torsion_order, geometric_automorphism],
            [torsion_structure, geometric_endomorphism],
            [two_selmer_rank, locally_solvable],
            [analytic_sha, has_square_sha],
            [analytic_rank, geometrically_simple],
            [bad_primes, count],
        ]

        refine_array = [
            [
                conductor,
                discriminant,
                rational_points,
                rational_weirstrass_points,
                torsion_order,
            ],
            [
                bad_primes,
                two_selmer_rank,
                analytic_rank,
                analytic_sha,
                torsion_structure,
            ],
            [
                is_gl2_type,
                st_group,
                Q_automorphism,
                has_square_sha,
                geometrically_simple,
            ],
            [
                geometric_endomorphism,
                st_group_identity_component,
                geometric_automorphism,
                locally_solvable,
            ],
        ]
        SearchArray.__init__(self, browse_array, refine_array)
