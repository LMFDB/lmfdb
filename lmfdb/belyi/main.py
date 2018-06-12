# -*- coding: utf8 -*-

import StringIO
from ast import literal_eval
import re
import time
from pymongo import ASCENDING, DESCENDING
from operator import mul
from flask import render_template, url_for, request, redirect, send_file, abort
from sage.all import ZZ
from sage.misc.cachefunc import cached_function

from lmfdb.utils import to_dict, comma, format_percentage, random_value_from_collection, attribute_value_counts, flash_error
from lmfdb.search_parsing import parse_bool, parse_ints, parse_bracketed_posints, parse_count, parse_start
from lmfdb.belyi import belyi_page
from lmfdb.belyi.web_belyi import WebBelyiGalmap, WebBelyiPassport, belyi_db_galmaps, belyi_db_passports

credit_string = "Edgar Costa, Michael Musty, Sam Schiavone, John Voight."

###############################################################################
# global database connection and stats objects
###############################################################################

the_belyistats = None
def belyistats():
    global the_belyistats
    if the_belyistats is None:
        the_belyistats = belyi_stats()
    return the_belyistats

###############################################################################
# List and dictionaries needed routing and searching
###############################################################################

geometry_types_dict = {'H':'Hyperbolic', 'S':'Spherical', 'E':'Euclidian'}
geometry_types_list = geometry_types_dict.keys();




###############################################################################
# Routing for top level, random_curve, and stats
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Belyi labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

@belyi_page.route("/")
def index():
    if len(request.args) > 0:
        return belyi_search(to_dict(request.args))
    info = {'counts' : belyistats().counts()}
    info["stats_url"] = url_for(".statistics")
    info["belyi_galmap_url"] =  lambda label: url_for_belyi_galmap_label(label)
    belyi_galmap_labels = ('4T5-[4,4,3]-4-4-31-g1-a','5T4-[5,3,3]-5-311-311-g0-a','9T34-[14,4,4]-72-42111-4221-g0-a')
    info["belyi_galmap_list"] = [ {'label':label,'url':url_for_belyi_galmap_label(label)} for label in belyi_galmap_labels ]
    info["degree_list"] = ('1-6', '7-8', '9-10','10-100')
    title = 'Belyi maps'
    bread = (('Belyi Maps', url_for(".index")))

    #search options
    info['geometry_types_list'] = geometry_types_list;
    info['geometry_types_dict'] = geometry_types_dict;

    return render_template("belyi_browse.html", info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread)

@belyi_page.route("/random")
def random_belyi_galmap():
    label = random_value_from_collection(belyi_db_galmaps(), 'label')
    return redirect(url_for_belyi_galmap_label(label), 307)

@belyi_page.route("/stats")
def statistics():
    info = { 'counts': belyistats().counts(), 'stats': belyistats().stats() }
    title = 'Belyi maps: statistics'
    bread = (('Belyi Maps', url_for(".index")), ('Statistics', ' '))
    return render_template("belyi_stats.html", info=info, credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())

###############################################################################
# Curve and isogeny class pages
###############################################################################

@belyi_page.route("/<group>/<abc>/<sigma0>/<sigma1>/<sigmaoo>/<g>/<letnum>")
def by_url_belyi_galmap_label(group, abc, sigma0, sigma1, sigmaoo, g, letnum):
    label = group+"-"+abc+"-"+sigma0+"-"+sigma1+"-"+sigmaoo+"-"+g+"-"+letnum
    return render_belyi_galmap_webpage(label)

@belyi_page.route("/<group>/<abc>/<sigma0>/<sigma1>/<sigmaoo>/<g>")
def by_url_belyi_passport_label(group, abc, sigma0, sigma1, sigmaoo, g):
    label = group+"-"+abc+"-"+sigma0+"-"+sigma1+"-"+sigmaoo+"-"+g
    return render_belyi_passport_webpage(label)

def render_belyi_galmap_webpage(label):
    try:
        belyi_galmap = WebBelyiGalmap.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("belyi_galmap.html",
                           properties2=belyi_galmap.properties,
                           credit=credit_string,
                           info={},
                           data=belyi_galmap.data,
                           code=belyi_galmap.code,
                           bread=belyi_galmap.bread,
                           learnmore=learnmore_list(),
                           title=belyi_galmap.title,
                           friends=belyi_galmap.friends)

def render_belyi_passport_webpage(label):
    try:
        belyi_passport = WebBelyiPassport.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("belyi_passport.html",
                           properties2=belyi_passport.properties,
                           credit=credit_string,
                           data=belyi_passport.data,
                           bread=belyi_passport.bread,
                           learnmore=learnmore_list(),
                           title=belyi_passport.title,
                           friends=belyi_passport.friends)

def url_for_belyi_galmap_label(label):
    slabel = label.split("-")
    return url_for(".by_url_belyi_galmap_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5], letnum=slabel[6])

def url_for_belyi_passport_label(label):
    slabel = label.split("-")
    return url_for(".by_url_belyi_passport_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5])

def belyi_passport_from_belyi_galmap_label(label):
    return '-'.join(label.split("-")[:-1])


#either a passport label or a galmap label
@cached_function
def break_label(label):
    """
    >>> break_label("4T5-[4,4,3]-4-4-31-g1-a")
    "4T5", [4,4,3], [[4],[4],[3,1]], 1, "a"
    >>> break_label("4T5-[4,4,3]-4-4-31-g1")
    "4T5", [4,4,3], [[4],[4],[3,1]], 1, None
    >>> break_label("12T5-[4,4,3]-10,4-11,1-31-g1")
    "12T5", [4,4,3], [[10,4],[11,1],[3,1]], 1, None
    """
    splitlabel = label.split("-");
    if len(splitlabel) == 6:
        group, abc, l0, l1, l2, genus = splitlabel;
        gal = None
    elif len(splitlabel) == 7:
        group, abc, l0, l1, l2, genus, gal = splitlabel;
    else:
        raise ValueError("the label must have 5 or 6 dashes");

    abc = map(int, abc[1:-1].split(","));
    lambdas = [l0, l1, l2];
    for i, elt in lambdas:
        if "," in elt:
            elt = map(int, elt.split(","));
        else:
            elt = map(int, list(elt));
    genus = int(genus[1:]);
    return group, abc, lambdas, genus, gal;


def belyi_group_from_label(label):
    return break_label(label)[0];

def belyi_degree_from_label(label):
    return int(break_label(label)[0].split("T")[0]);

def belyi_abc_from_label(label):
    return break_label(label)[1];

def belyi_lambdas_from_label(label):
    return break_label(label)[2];

def belyi_genus_from_label(label):
    return break_label(label)[3];

def belyi_orbit_from_label(label):
    return break_label(label)[-1];



################################################################################
# Searching
################################################################################

def belyi_search(info):
    if 'jump' in info:
        jump = info["jump"].strip()
        if re.match(r'^\d+T\d+-\[\d+,\d+,\d+\]-\d+-\d+-\d+-g\d+[a-z]+$', jump):
            return redirect(url_for_belyi_galmap_label(jump), 301)
        else:
            if re.match(r'^\d+T\d+-\[\d+,\d+,\d+\]-\d+-\d+-\d+-g\d$', jump):
                return redirect(url_for_belyi_passport_label(jump), 301)
            else:
                errmsg = "%s is not a valid Belyi map or passport label"
        flash_error (errmsg, jump)
        return redirect(url_for(".index"))
#     if info.get('download','').strip():
#         return download_search(info)

    #search options
    info['geometry_types_list'] = geometry_types_list;
    info['geometry_types_dict'] = geometry_types_dict;

    bread = info.get('bread',(('Belyi Maps', url_for(".index")), ('Search Results', '.')))

    query = {}
    try:
        if 'group' in query:
            info['group'] = query['group']
        #FIXME search every possible permutation
        parse_bracketed_posints(info, query, 'abc', 'a, b, c', maxlength=3)
        parse_ints(info, query, 'g','g')
        parse_ints(info, query, 'deg', 'deg')
        parse_ints(info, query, 'orbit_size', 'orbit_size')
        # invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
        for fld in ['geomtype']:
            if info.get(fld):
                query[fld] = info[fld]
    except ValueError as err:
        info['err'] = str(err)
        return render_template("belyi_search_results.html", info=info, title='Belyi Maps Search Input Error', bread=bread, credit=credit_string)

    # Database query happens here
    info["query"] = query # save query for reuse in download_search
    cursor = belyi_db_galmaps().find(query, {'_id':False, 'label':True, 'group': True, 'abc':True, 'g':True, 'deg':True, 'geomtype' : True, 'orbit_size' : True})

    count = parse_count(info, 50)
    start = parse_start(info)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    res = cursor.sort([("deg", ASCENDING), ("group_num", ASCENDING), ("g", ASCENDING),  ("label", ASCENDING)]).skip(start).limit(count)
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
        print v
        v_clean = {}
        for key in ('label', 'group', 'deg', 'g','orbit_size' ):
            v_clean[key] = v[key]
        v_clean['geomtype'] = geometry_types_dict[v['geomtype']];
        # clean some other stuff
        res_clean.append(v_clean)

    info["belyi_galmaps"] = res_clean
    info["belyi_galmap_url"] = lambda label: url_for_belyi_galmap_label(label)
    info["start"] = start
    info["count"] = count
    info["more"] = int(start+count<nres)

    title = info.get('title','Belyi map search results')
    credit = credit_string

    return render_template("belyi_search_results.html", info=info, credit=credit,learnmore=learnmore_list(), bread=bread, title=title)

################################################################################
# Statistics
################################################################################

def boolean_format(value):
    return 'True' if value else 'False'

stats_attribute_list = [
    {'name':'size','top_title':'Galois orbit size','row_title':'size','knowl':'belyi.galmap.size','avg':True}
]

class belyi_stats(object):
    """
    Class for creating and displaying statistics for Belyi maps
    """

    def __init__(self):
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_belyi_count()
        return self._counts

    def stats(self):
        self.init_belyi_count()
        self.init_belyi_stats()
        return self._stats

    def init_belyi_count(self):
        if self._counts:
            return
        galmaps = belyi_db_galmaps()
        counts = {}
        ngalmaps = galmaps.count()
        counts['ngalmaps']  = ngalmaps
        counts['ngalmaps_c'] = comma(ngalmaps)
        passports = belyi_db_passports()
        npassports = passports.count()
        counts['npassports'] = npassports
        counts['npassports_c'] = comma(npassports)
        max_deg = passports.find().sort('deg', DESCENDING).limit(1)[0]['deg']
        counts['max_deg'] = max_deg
        counts['max_deg_c'] = comma(max_deg)
        self._counts = counts

    def init_belyi_stats(self):
        if self._stats:
            return
        #curves = belyi_db_curves()
        curves = None
        counts = self._counts
        total = counts["ncurves"]
        stats = {}
        dists = []
        # TODO use aggregate $group to speed this up and/or just store these counts in the database
        for attr in stats_attribute_list:
            counts = attribute_value_counts(curves, attr['name'])
            counts = [c for c in counts if c[0] != None]
            if len(counts) == 0:
                continue
            vcounts = []
            rows = []
            avg = 0
            total = sum([c[1] for c in counts])
            for value,n in counts:
                prop = format_percentage(n,total)
                if 'avg' in attr and attr['avg'] and (type(value) == int or type(value) == float):
                    avg += n*value
                value_string = attr['format'](value) if 'format' in attr else value
                vcounts.append({'value': value_string, 'curves': n, 'query':url_for(".index_Q")+'?'+attr['name']+'='+str(value),'proportion': prop})
                if len(vcounts) == 10:
                    rows.append(vcounts)
                    vcounts = []
            if len(vcounts):
                rows.append(vcounts)
            if 'avg' in attr and attr['avg']:
                vcounts.append({'value':'\(\\mathrm{avg}\\ %.2f\)'%(float(avg)/total), 'curves':total, 'query':url_for(".index_Q") +'?'+attr['name'],'proportion':format_percentage(1,1)})
            dists.append({'attribute':attr,'rows':rows})
        stats["distributions"] = dists
        self._stats = stats












# download_languages = ['magma', 'sage', 'gp', 'text']
# download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\','text':'#'}
# download_assignment_start = {'magma':'data :=[','sage':'data =[','gp':'data = {[','text':'data - ['}
# download_assignment_end = {'magma':'];','sage':']','gp':']}','text':']'}
# download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp','text':'.txt'}
# download_make_data = {
# 'magma':'function make_data()\n  R<x>:=PolynomialRing(Rationals());\n  return [HyperellipticCurve(R!r[1],R!r[2]):r in data];\nend function;\n',
# 'sage':'def make_data():\n\tR.<x>=PolynomialRing(QQ)\n\treturn [HyperellipticCurve(R(r[0]),R(r[1])) for r in data]\n\n',
# 'gp':'make_data()=[apply(Polrev,c)|c<-data];\n\n',
# 'text':''
# }
# download_make_data_comment = {
#         'magma': 'To create a list of curves, type "curves:= make_data();"',
#         'sage':'To create a list of curves, type "curves = make_data()"',
#         'gp':'To create a list of curves [f,h], type "curves = make_data()"',
#         'text':''}
# 
# def download_search(info):
#     lang = info.get('download','text').strip()
#     filename = 'genus2_curves' + download_file_suffix[lang]
#     mydate = time.strftime("%d %B %Y")
#     # reissue query here
#     try:
#         res = g2c_db_curves().find(literal_eval(info.get('query','{}')),{'_id':False,'eqn':True})
#     except Exception as err:
#         return "Unable to parse query: %s"%err
#     c = download_comment_prefix[lang]
#     s =  '\n'
#     s += c + ' Genus 2 curves downloaded from the LMFDB downloaded on %s.\n'% mydate
#     s += c + ' Query "%s" returned %d curves.\n\n' %(str(info.get('query')), res.count())
#     s += c + ' Below is a list called data. Each entry has the form:\n'
#     s += c + '   [[f coeffs],[h coeffs]]\n'
#     s += c + ' defining the hyperelliptic curve y^2+h(x)y=f(x)\n'
#     s += c + '\n'
#     s += c + ' ' + download_make_data_comment[lang] + '\n'
#     s += '\n'
#     s += download_assignment_start[lang] + '\\\n'
#     s += str(',\n'.join([str(r['eqn']) for r in res])) # list of curve equations
#     s += download_assignment_end[lang]
#     s += '\n\n'
#     s += download_make_data[lang]
#     strIO = StringIO.StringIO()
#     strIO.write(s)
#     strIO.seek(0)
#     return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)


@belyi_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Belyi map data'
    bread = (('Belyi Maps', url_for(".index")), ('Completeness',''))
    return render_template("single.html", kid='dq.belyi.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@belyi_page.route("/Source")
def how_computed_page():
    t = 'Source of Belyi map data'
    bread = (('Belyi Maps', url_for(".index")), ('Source',''))
    return render_template("single.html", kid='dq.belyi.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@belyi_page.route("/Labels")
def labels_page():
    t = 'Labels for Belyi maps'
    bread = (('Belyi Maps', url_for(".index")), ('Labels',''))
    return render_template("single.html", kid='belyi.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
