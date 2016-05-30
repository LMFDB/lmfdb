# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import StringIO
from ast import literal_eval
import re
import time
from pymongo import ASCENDING, DESCENDING
from operator import mul
from lmfdb.base import app
from flask import flash, render_template, url_for, request, redirect, make_response, send_file
from markupsafe import Markup

from lmfdb.utils import to_dict, comma, random_object_from_collection
from lmfdb.search_parsing import parse_bool, parse_ints, parse_signed_ints, parse_bracketed_posints, parse_count, parse_start
from lmfdb.number_fields.number_field import make_disc_key
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.isogeny_class import G2Cisogeny_class, st_group_name, st_group_href
from lmfdb.genus2_curves.web_g2c import WebG2C, g2cdb, list_to_min_eqn, isogeny_class_label, st0_group_name, aut_group_name, boolean_name, globally_solvable_name

import sage.all
from sage.all import ZZ, QQ, latex, matrix, srange
credit_string = "Andrew Booker, Jeroen Sijsling, Andrew Sutherland, John Voight, and Dan Yasaki"

###############################################################################
# global database connection and stats objects
###############################################################################

the_g2cstats = None
def g2cstats():
    global the_g2cstats
    if the_g2cstats is None:
        the_g2cstats = G2C_stats()
    return the_g2cstats

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
        '[8,3]':'D_8',
        '[12,4]':'D_{12}'
        }

geom_aut_grp_list = ['[2,1]', '[4,2]', '[8,3]', '[10,2]', '[12,4]', '[24,8]', '[48,29]']
geom_aut_grp_dict = {
        '[2,1]':'C_2',
        '[4,2]':'V_4',
        '[8,3]':'D_8',
        '[10,2]':'C_{10}',
        '[12,4]':'D_{12}',
        '[24,8]':'2D_{12}',
        '[48,29]':'tilde{S}_4'}

###############################################################################
# Routing for top level, random_curve,  and stats
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
        return genus2_curve_search(data=request.args)
    info = {'counts' : g2cstats().counts()}
    info["stats_url"] = url_for(".statistics")
    info["curve_url"] =  lambda label: url_for_curve_label(label)
    curve_labels = ('169.a.169.1', '1116.a.214272.1', '1152.a.147456.1', '1369.a.50653.1', '15360.f.983040.2')
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
    title = 'Genus 2 curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '))
    return render_template("browse_search_g2.html", info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread)

@g2c_page.route("/Q/random")
def random_curve():
    label = random_object_from_collection(g2cdb().curves)['label']
    return redirect(url_for_curve_label(label), 301)

@g2c_page.route("/Q/stats")
def statistics():
    info = { 'counts': g2cstats().counts(), 'stats': g2cstats().stats() }
    title = 'Genus 2 curves over $\Q$: statistics'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index_Q")), ('statistics', ' '))
    return render_template("statistics_g2.html", info=info, credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())

###############################################################################
# Curve and isogeny class pages
###############################################################################

@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/<int:num>")
def by_url_curve_label(cond, alpha, disc, num):
    label = str(cond)+"."+alpha+"."+str(disc)+"."+str(num)
    return render_curve_webpage(label)

@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/")
def by_url_isogeny_class_discriminant(cond, alpha, disc):
    data = {}
    if len(request.args) > 0:
        # if changed conductor or discriminat, fall back to a general search
        if ('cond' in request.args and request.args['cond'] != str(cond)) or \
           ('abs_disc' in request.args and request.args['abs_disc'] != str(disc)):
            return redirect (url_for(".index", **request.args), 301)
        data = to_dict(request.args)
    class_label = str(cond)+"."+alpha
    data['cond'] = cond
    data['class'] = class_label
    data['abs_disc'] = disc
    data['bread'] = (('Genus 2 Curves', url_for(".index")),
        ('$\Q$', url_for(".index_Q")),
        ('%s' % cond, url_for(".by_conductor", cond=cond)),
        ('%s' % alpha, url_for(".by_url_isogeny_class_label", cond=cond, alpha=alpha)),
        ('%s' % disc, '.'))
    data['title'] = 'Genus 2 Curve search results for isogeny class %s and discriminant %s' % (class_label,disc)
    return genus2_curve_search(data=data, **request.args)

@g2c_page.route("/Q/<int:cond>/<alpha>/")
def by_url_isogeny_class_label(cond, alpha):
    label = str(cond)+"."+alpha
    return render_isogeny_class_webpage(label)

@g2c_page.route("/Q/<int:cond>/")
def by_conductor(cond):
    data = {}
    if len(request.args) > 0:
        # if changed conductor or discriminat, fall back to a general search
        if 'cond' in request.args and request.args['cond'] != str(cond):
            return redirect (url_for(".index", **request.args), 301)
        data = to_dict(request.args)
    data['cond'] = cond
    data['bread'] = (('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index_Q")), ('%s' % cond, '.'))
    data['title'] = 'Genus 2 Curve search results for conductor %s' % cond
    return genus2_curve_search(data=data, **request.args)

@g2c_page.route("/Q/<label>")
def by_label(label):
    # handles curve, isogeny class, and Lhash labels
    return genus2_curve_search(data={'jump':label}, **request.args)

def render_curve_webpage(label):
    credit = credit_string
    data = WebG2C.by_label(label)
    # check for error message string
    if isinstance(data,str):
        return data
    return render_template("curve_g2.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           code=data.code,
                           bread=data.bread,
                           learnmore=learnmore_list(),
                           title=data.title,
                           friends=data.friends)
                           #downloads=data.downloads)

def render_isogeny_class_webpage(label):
    credit = credit_string
    class_data = G2Cisogeny_class.by_label(label)
    # check for error message string
    if isinstance(class_data,str):
        return class_data
    return render_template("isogeny_class_g2.html",
                           properties2=class_data.properties,
                           bread=class_data.bread,
                           learnmore=learnmore_list(),
                           credit=credit,
                           info=class_data,
                           title=class_data.title,
                           friends=class_data.friends)
                           #downloads=class_data.downloads)
                           

def url_for_curve_label(label):
    L = label.split(".")
    return url_for(".by_url_curve_label", cond=L[0], alpha=L[1], disc=L[2], num=L[3])

def url_for_isogeny_class_label(label):
    L = label.split(".")
    return url_for(".by_url_isogeny_class_label", cond=L[0], alpha=L[1])

def class_from_curve_label(label):
    return '.'.join(label.split(".")[:2])

################################################################################
# Searching
################################################################################

def genus2_curve_search(**args):
    info = to_dict(args['data'])
    if 'jump' in info:
        jump = info["jump"].strip()
        curve_label_regex = re.compile(r'\d+\.[a-z]+.\d+.\d+$')
        if curve_label_regex.match(jump):
            return redirect(url_for_curve_label(jump), 301)
        else:
            class_label_regex = re.compile(r'\d+\.[a-z]+$')
            if class_label_regex.match(jump):
                return redirect(url_for_isogeny_class_label(jump), 301)
            else:
                # Handle direct Lhash input
                class_label_regex = re.compile(r'#\d+$')
                if class_label_regex.match(jump) and ZZ(jump[1:]) < 2**61:
                    c = g2cdb().isogeny_classes.find_one({'hash':int(jump[1:])})
                    if c:
                        return redirect(url_for_isogeny_class_label(c["label"]), 301)
                    else:
                        errmsg = "Hash not found"
                else:
                    errmsg = "Invalid label"
        flash(Markup(errmsg + " <span style='color:black'>%s</span>"%(jump)),"error")
        return redirect(url_for(".index"))

    if 'download' in info and info['download'] == '1':
        return download_search(info)
    
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    bread = info.get('bread',(('Genus 2 Curves', url_for(".index")), ('$\Q$', url_for(".index_Q")), ('Search Results', '.')))

    query = {}
    try:
        parse_ints(info,query,'abs_disc','absolute discriminant')
        parse_bool(info,query,'is_gl2_type')
        parse_bool(info,query,'has_square_sha')
        parse_bool(info,query,'locally_solvable')
        parse_bracketed_posints(info, query, 'torsion', 'torsion structure', maxlength=4,check_divisibility="increasing")
        parse_ints(info,query,'cond')
        parse_ints(info,query,'num_rat_wpts','Weierstrass points')
        parse_ints(info,query,'torsion_order')
        if 'torsion' in query and not 'torsion_order' in query:
            query['torsion_order'] = reduce(mul,[int(n) for n in query['torsion']],1)
        parse_ints(info,query,'two_selmer_rank','2-Selmer rank')
        parse_ints(info,query,'analytic_rank','analytic rank')
        # G2 invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
        if 'g20' in info and 'g21' in info and 'g22' in info:
            query['g2inv'] = [ info['g20'], info['g21'], info['g22'] ]
        if 'class' in info:
            query['class'] = info['class']
        for fld in ('st_group', 'real_geom_end_alg', 'aut_grp_id', 'geom_aut_grp_id'):
            if info.get(fld): query[fld] = info[fld]
    except ValueError as err:
        info['err'] = str(err)
        return render_template("search_results_g2.html", info=info, title='Genus 2 Curves Search Input Error', bread=bread, credit=credit_string)
    info["query"] = dict(query)
    
    # Database query happens here
    cursor = g2cdb().curves.find(query,{'_id':int(0),'label':int(1),'min_eqn':int(1),'st_group':int(1),'is_gl2_type':int(1),'analytic_rank':int(1)})

    count = parse_count(info, 50)
    start = parse_start(info)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    res = cursor.sort([("cond", ASCENDING), ("class", ASCENDING),  ("disc_key", ASCENDING),  ("label", ASCENDING)]).skip(start).limit(count)
    nres = res.count()

    if nres == 1:
        info["report"] = "unique match"
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    res_clean = []

    for v in res:
        v_clean = {}
        v_clean["label"] = v["label"]
        v_clean["class"] = class_from_curve_label(v["label"])
        v_clean["is_gl2_type"] = v["is_gl2_type"] 
        v_clean["is_gl2_type_display"] = '&#10004;' if v["is_gl2_type"] else '' # display checkmark if true, blank otherwise
        v_clean["equation_formatted"] = list_to_min_eqn(v["min_eqn"])
        v_clean["st_group_name"] = st_group_name(v['st_group'])
        v_clean["st_group_href"] = st_group_href(v['st_group'])
        v_clean["analytic_rank"] = v["analytic_rank"]
        res_clean.append(v_clean)

    info["curves"] = res_clean
    info["curve_url"] = lambda label: url_for_curve_label(label)
    info["class_url"] = lambda label: url_for_isogeny_class_label(label)
    info["start"] = start
    info["count"] = count
    info["more"] = int(start+count<nres)
    
    title = info.get('title','Genus 2 Curve search results')
    credit = credit_string
    
    return render_template("search_results_g2.html", info=info, credit=credit,learnmore=learnmore_list(), bread=bread, title=title)

################################################################################
# Statistics
################################################################################

stats_attribute_list = [
    {'name':'num_rat_wpts','top_title':'rational Weierstrass points','row_title':'Weierstrass points','knowl':'g2c.num_rat_wpts','avg':True},
    {'name':'aut_grp_id','top_title':'$\mathrm{Aut}(X)$','row_title':'automorphism group','knowl':'g2c.aut_grp','format':aut_group_name},
    {'name':'geom_aut_grp_id','top_title':'$\mathrm{Aut}(X_{\mathbb{Q}})$','row_title':'automorphism group','knowl':'g2c.geom_aut_grp','format':aut_group_name},
    {'name':'analytic_rank','top_title':'analytic ranks','row_title':'analytic rank','knowl':'g2c.analytic_rank','avg':True},
    {'name':'two_selmer_rank','top_title':'2-Selmer ranks','row_title':'2-Selmer rank','knowl':'g2c.two_selmer_rank','avg':True},
    {'name':'has_square_sha','top_title':'squareness of &#1064;','row_title':'has square Sha','knowl':'g2c.has_square_sha', 'format':boolean_name},
    {'name':'locally_solvable','top_title':'local solvability','row_title':'locally solvable','knowl':'g2c.locally_solvable', 'format':boolean_name},
    {'name':'is_gl2_type','top_title':'$\mathrm{GL}_2$-type','row_title':'is of GL2-type','knowl':'g2c.gl2type', 'format':boolean_name},
    {'name':'real_geom_end_alg','top_title':'Sato-Tate group identity components','row_title':'identity component','knowl':'g2c.st_group_identity_component', 'format':st0_group_name},
    {'name':'st_group','top_title':'Sato-Tate groups','row_title':'Sato-Tate groups','knowl':'g2c.st_group', 'format':st_group_name},
    {'name':'torsion_order','top_title':'torsion subgroup orders','row_title':'torsion order','knowl':'g2c.torsion_order','avg':True},
]

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

class G2C_stats(object):
    """
    Class for creating and displaying statistics for genus 2 curves over Q
    """

    def __init__(self):
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_g2c_count()
        return self._counts

    def stats(self):
        self.init_g2c_count()
        self.init_g2c_stats()
        return self._stats

    def init_g2c_count(self):
        if self._counts:
            return
        counts = {}
        ncurves = g2cdb().curves.count()
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = g2cdb().isogeny_classes.count()
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        max_D = g2cdb().curves.find().sort('abs_disc', DESCENDING).limit(1)[0]['abs_disc']
        counts['max_D'] = max_D
        counts['max_D_c'] = comma(max_D)
        self._counts  = counts

    def init_g2c_stats(self):
        if self._stats:
            return
        g2c_logger.debug("Computing genus 2 curve stats...")
        counts = self._counts
        total = counts["ncurves"]
        stats = {}
        dists = []
        for attr in stats_attribute_list:
            values = g2cdb().curves.distinct(attr['name'])
            values.sort()
            vcounts = []
            rows = []
            colcount = 0
            avg = 0
            for value in values:
                n = g2cdb().curves.find({attr['name']:value}).count()
                prop = format_percentage(n,total)
                if 'avg' in attr and attr['avg']:
                    avg += n*value
                value_string = attr['format'](value) if 'format' in attr else value
                vcounts.append({'value': value_string, 'curves': n, 'query':url_for(".index_Q")+'?'+attr['name']+'='+str(value),'proportion': prop})
                if len(vcounts) == 10:
                    rows.append(vcounts)
                    vcounts = []
            if len(vcounts):
                rows.append(vcounts)
            if 'avg' in attr and attr['avg']:
                vcounts.append({'value':'\\mathrm{avg}\\ %.2f'%(float(avg)/total), 'curves':total, 'query':url_for(".index_Q") +'?'+attr['name'],'proportion':format_percentage(1,1)})
            dists.append({'attribute':attr,'rows':rows})
        stats["distributions"] = dists
        self._stats = stats
        g2c_logger.debug("... finished computing genus 2 curve stats.")

download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data :=[','sage':'data =[','gp':'data =['}
download_assignment_end = {'magma':'];','sage':']','gp':']'}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}
download_make_data = {
'magma':'function make_data()\n  R<x>:=PolynomialRing(Rationals());\n  return [HyperellipticCurve(R!r[1],R!r[2]):r in data];\nend function;\n',
'sage':'def make_data():\n\tR.<x>=PolynomialRing(QQ)\n\treturn [HyperellipticCurve(R(r[0]),R(r[1])) for r in data]\n\n',
'gp':''
}
download_make_data_comment = {'magma': 'To create a list of curves, type "curves:= make_data();"','sage':'To create a list of curves, type "curves = make_data()"', 'gp':''}

def download_search(info):
    lang = info["submit"]
    filename = 'genus2_curves' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here
    res = g2cdb().curves.find(literal_eval(info["query"]),{'_id':int(0),'min_eqn':int(1)})
    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Genus 2 curves downloaded from the LMFDB downloaded on %s. Found %s curves.\n'%(mydate, res.count())
    s += c + ' Below is a list called data. Each entry has the form:\n'
    s += c + '   [[f coeffs],[h coeffs]]\n'
    s += c + ' defining the hyperelliptic curve y^2+h(x)y=f(x)\n'
    s += c + '\n'
    s += c + ' ' + download_make_data_comment[lang] + '\n'
    s += '\n'
    s += download_assignment_start[lang] + '\\\n'
    # loop through all search results and grab the curve equations
    for r in res:
        entry = str(r['min_eqn'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        s += entry + ',\\\n'
    s = s[:-3]
    s += download_assignment_end[lang]
    s += '\n\n'
    s += download_make_data[lang]
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True)


@g2c_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of genus 2 curve data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Completeness',''))
    return render_template("single.html", kid='dq.g2c.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@g2c_page.route("/Source")
def how_computed_page():
    t = 'Source of genus 2 curve data over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Source',''))
    return render_template("single.html", kid='dq.g2c.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@g2c_page.route("/Labels")
def labels_page():
    t = 'Labels for genus 2 curves over $\Q$'
    bread = (('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Labels',''))
    return render_template("single.html", kid='g2c.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
