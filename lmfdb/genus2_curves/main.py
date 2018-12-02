# -*- coding: utf-8 -*-

from ast import literal_eval
import re
from operator import mul
from flask import render_template, url_for, request, redirect, abort
from sage.all import ZZ

from lmfdb.db_backend import db
from lmfdb.utils import to_dict, comma, flash_error, display_knowl
from lmfdb.search_parsing import parse_bool, parse_ints, parse_bracketed_posints
from lmfdb.search_wrapper import search_wrap
from lmfdb.downloader import Downloader
from lmfdb.genus2_curves import g2c_page
from lmfdb.genus2_curves.web_g2c import WebG2C, list_to_min_eqn, st0_group_name
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.display_stats import StatsDisplay, boolean_format

credit_string = "Andrew Booker, Jeroen Sijsling, Andrew Sutherland, John Voight,  Raymond van Bommel, Dan Yasaki"

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

aut_grp_list = ['[2,1]', '[4,1]', '[4,2]', '[6,2]', '[8,3]', '[12,4]']
aut_grp_dict = {
        '[2,1]':'C_2',
        '[4,1]':'C_4',
        '[4,2]':'V_4',
        '[6,2]':'C_6',
        '[8,3]':'D_4',
        '[12,4]':'D_6'
        }

geom_aut_grp_list = ['[2,1]', '[4,2]', '[8,3]', '[10,2]', '[12,4]', '[24,8]', '[48,29]']
geom_aut_grp_dict = {
        '[2,1]':'C_2',
        '[4,2]':'V_4',
        '[8,3]':'D_4',
        '[10,2]':'C_{10}',
        '[12,4]':'D_6',
        '[24,8]':'2D_6',
        '[48,29]':'\\tilde{S}_4'}

###############################################################################
# Routing for top level and random_curve
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Genus 2 curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

@g2c_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@g2c_page.route("/Q/")
def index_Q():
    if len(request.args) > 0:
        return genus2_curve_search(request.args)
    info = {'stats' : G2C_stats()}
    info["stats_url"] = url_for(".statistics")
    info["curve_url"] =  lambda label: url_for_curve_label(label)
    curve_labels = ('169.a.169.1', '277.a.277.1', '1116.a.214272.1','1369.a.50653.1', '11664.a.11664.1')
    info["curve_list"] = [ {'label':label,'url':url_for_curve_label(label)} for label in curve_labels ]
    info["conductor_list"] = ('1-499', '500-999', '1000-99999','100000-1000000')
    info["discriminant_list"] = ('1-499', '500-999', '1000-99999','100000-1000000')
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    title = 'Genus 2 Curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '))
    return render_template("g2c_browse.html", info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread)

@g2c_page.route("/Q/random")
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
        ('$\Q$', url_for(".index_Q")),
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
    data['bread'] = [('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index_Q")), ('%s' % cond, url_for(".by_conductor", cond=cond))]
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
                           properties2=g2c.properties,
                           credit=credit_string,
                           info={'aut_grp_dict':aut_grp_dict,'geom_aut_grp_dict':geom_aut_grp_dict},
                           data=g2c.data,
                           code=g2c.code,
                           bread=g2c.bread,
                           learnmore=learnmore_list(),
                           title=g2c.title,
                           friends=g2c.friends)

def render_isogeny_class_webpage(label):
    try:
        g2c = WebG2C.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("g2c_isogeny_class.html",
                           properties2=g2c.properties,
                           credit=credit_string,
                           data=g2c.data,
                           bread=g2c.bread,
                           learnmore=learnmore_list(),
                           title=g2c.title,
                           friends=g2c.friends)

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
    flash_error (errmsg, jump)
    return redirect(url_for(".index"))

class G2C_download(Downloader):
    table = db.g2c_curves
    title = 'Genus 2 curves'
    columns = 'eqn'
    data_format = ['[[f coeffs],[h coeffs]]']
    data_description = 'defining the hyperelliptic curve y^2+h(x)y=f(x).'
    function_body = {'magma':['R<x>:=PolynomialRing(Rationals());',
                              'return [HyperellipticCurve(R!r[1],R!r[2]):r in data];'],
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
                       "equation_formatted": lambda v: list_to_min_eqn(literal_eval(v.pop("eqn"))),
                       "st_group_link": lambda v: st_link_by_name(1,4,v.pop('st_group'))},
             bread=lambda:[('Genus 2 Curves', url_for(".index")),
                           ('$\Q$', url_for(".index_Q")),
                           ('Search Results', '.')],
             learnmore=learnmore_list,
             credit=lambda:credit_string)
def genus2_curve_search(info, query):
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    parse_ints(info,query,'abs_disc','absolute discriminant')
    parse_bool(info,query,'is_gl2_type','is of GL2-type')
    parse_bool(info,query,'has_square_sha','has square Sha')
    parse_bool(info,query,'locally_solvable','is locally solvable')
    parse_bool(info,query,'is_simple_geom','is geometrically simple')
    parse_ints(info,query,'cond','conductor')
    parse_ints(info,query,'num_rat_pts','rational points')
    parse_ints(info,query,'num_rat_wpts','rational Weierstrass points')
    parse_bracketed_posints(info, query, 'torsion', 'torsion structure', maxlength=4,check_divisibility="increasing")
    parse_ints(info,query,'torsion_order','torsion order')
    if 'torsion' in query and not 'torsion_order' in query:
        query['torsion_order'] = reduce(mul,[int(n) for n in query['torsion']],1)
    if 'torsion' in query:
        query['torsion_subgroup'] = str(query['torsion']).replace(" ","")
        query.pop('torsion') # search using string key, not array of ints
    parse_ints(info,query,'two_selmer_rank','2-Selmer rank')
    parse_ints(info,query,'analytic_rank','analytic rank')
    # G2 invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
    if 'g20' in info and 'g21' in info and 'g22' in info:
        query['g2_inv'] = "['%s','%s','%s']"%(info['g20'], info['g21'], info['g22'])
    if 'class' in info:
        query['class'] = info['class']
    for fld in ('st_group', 'real_geom_end_alg', 'aut_grp_id', 'geom_aut_grp_id'):
        if info.get(fld): query[fld] = info[fld]
    info["curve_url"] = lambda label: url_for_curve_label(label)
    info["class_url"] = lambda label: url_for_isogeny_class_label(label)

################################################################################
# Statistics
################################################################################

def aut_grp_format(id):
    return "\("+aut_grp_dict[id]+"\)"

def geom_aut_grp_format(id):
    return "\("+geom_aut_grp_dict[id]+"\)"

def st0_group_format(name):
    return "\("+st0_group_name(name)+"\)"

def st_group_format(name):
    return st_link_by_name(1,4,name)

class G2C_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for genus 2 curves over Q
    """
    def __init__(self):
        ncurves = comma(db.g2c_curves.count())
        nclasses = comma(db.lfunc_instances.count({'type':'G2Q'}))
        max_D = comma(db.g2c_curves.max('abs_disc'))
        g2c_knowl = display_knowl('g2c.g2curve', title='genus 2 curves')
        disc_knowl = display_knowl('g2c.abs_discriminant', title = "absolute discriminant")
        stats_url = url_for(".statistics")
        self.short_summary = 'The database currently contains %s %s over $\Q$ of %s up to %s.  Here are some <a href="%s">further statistics</a>.' % (ncurves, g2c_knowl, disc_knowl, max_D, stats_url)
        self.summary = 'The database currently contains %s genus 2 curves in %s isogeny classes, with %s at most %s.' % (ncurves, nclasses, disc_knowl, max_D)

    table = db.g2c_curves
    baseurl_func = ".index_Q"

    stat_list = [
        {'cols': 'num_rat_pts',
         'row_title': 'rational points',
         'knowl': 'g2c.num_rat_pts',
         'avg': True},
        {'cols': 'num_rat_wpts',
         'top_title': 'rational Weierstrass points',
         'row_title': 'Weierstrass points',
         'knowl': 'g2c.num_rat_wpts',
         'avg': True},
        {'cols': 'aut_grp_id',
         'top_title': '$\mathrm{Aut}(X)$',
         'row_title': 'automorphism group',
         'knowl': 'g2c.aut_grp',
         'formatter': aut_grp_format},
        {'cols': 'geom_aut_grp_id',
         'top_title': '$\mathrm{Aut}(X_{\overline{\mathbb{Q}}})$',
         'row_title': 'automorphism group',
         'knowl': 'g2c.geom_aut_grp',
         'formatter': geom_aut_grp_format},
        {'cols': 'analytic_rank',
         'row_title': 'analytic rank',
         'knowl': 'g2c.analytic_rank',
         'avg': True},
        {'cols': 'two_selmer_rank',
         'row_title': '2-Selmer rank',
         'knowl': 'g2c.two_selmer_rank',
         'avg': True},
        {'cols': 'has_square_sha',
         'top_title': 'squareness of &#1064;',
         'row_title': 'has square Sha',
         'knowl': 'g2c.has_square_sha',
         'formatter': boolean_format},
        {'cols': 'locally_solvable',
         'top_title': 'local solvability',
         'row_title': 'locally solvable',
         'knowl': 'g2c.locally_solvable',
         'formatter': boolean_format},
        {'cols': 'is_gl2_type',
         'top_title': '$\mathrm{GL}_2$-type',
         'row_title': 'is of GL2-type',
         'knowl': 'g2c.gl2type',
         'formatter': boolean_format},
        {'cols': 'real_geom_end_alg',
         'top_title': 'Sato-Tate group identity components',
         'row_title': 'identity component',
         'knowl': 'g2c.st_group_identity_component',
         'formatter': st0_group_format},
        {'cols': 'st_group',
         'row_title': 'Sato-Tate group',
         'knowl': 'g2c.st_group',
         'formatter': st_group_format},
        {'cols': 'torsion_order',
         'top_title': 'torsion subgroup orders',
         'row_title': 'torsion order',
         'knowl': 'g2c.torsion_order',
         'avg': True},
    ]

@g2c_page.route("/Q/stats")
def statistics():
    title = 'Genus 2 curves over $\Q$: Statistics'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index_Q")), ('Statistics', ' '))
    return render_template("display_stats.html", info=G2C_stats(), credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())



@g2c_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Genus 2 Curve Data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index")),('Completeness',''))
    return render_template("single.html", kid='dq.g2c.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@g2c_page.route("/Source")
def how_computed_page():
    t = 'Source of Genus 2 Curve Data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index")),('Source',''))
    return render_template("single.html", kid='dq.g2c.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@g2c_page.route("/Labels")
def labels_page():
    t = 'Labels for Genus 2 Curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index")),('Labels',''))
    return render_template("single.html", kid='g2c.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
