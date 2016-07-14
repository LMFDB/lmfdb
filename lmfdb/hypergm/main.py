# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones 

import re
import pymongo
ASC = pymongo.ASCENDING
from lmfdb import base
from flask import render_template, request, url_for
from lmfdb.utils import to_dict, image_callback
from lmfdb.search_parsing import parse_range2, clean_input, split_list
from sage.all import ZZ, QQ, latex, gp
from lmfdb.hypergm import hypergm_page

HGM_credit = 'D. Roberts'

# Helper functions

# A and B are lists, tn and td are num/den for t
def ab_label(A,B):
    return "A" + ".".join(map(str,A)) + "_B" + ".".join(map(str,B))
    
def make_abt_label(A,B,tn,td):
    AB_str = ab_label(A,B)
    t = QQ( "%d/%d" % (tn, td))
    t_str = "_t%s.%s" % (t.numerator(), t.denominator())
    return AB_str + t_str

def make_t_label(t):
    tsage = QQ("%d/%d" % (t[0], t[1]))
    return "t%s.%s" % (tsage.numerator(), tsage.denominator())

def get_bread(breads=[]):
    bc = [("Motives", url_for("motive.index")), ("Hypergeometric", url_for("motive.index2")), ("$\Q$", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def display_t(tn, td):
    t = QQ("%d/%d" % (tn, td))
    if t.denominator() == 1:
        return str(t.numerator())
    return "%s/%s" % (t.numerator(), t.denominator())

# For displaying factored conductors
def factorint(inp):
    return latex(ZZ(inp).factor())

# Returns a string of val if val = 0, 1, -1, or version with p factored out otherwise
def factor_out_p(val, p):
    val = ZZ(val)
    if val == 0 or val == -1:
        return str(val)
    if val==1:
        return '+1'
    s = 1
    if val<0:
        s = -1
        val = -val
    ord = val.valuation(p)
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

# Assume values have already been stripped of alphabetic
# characters and *'s inserted for multiplication
def myZZ(val):
    return int(ZZ(gp(val)))

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

# FIXME: delete or fix this code
# Apparently obsolete code that causes a server error if executed
#@hypergm_page.route("/search", methods=["GET", "POST"])
#def search():
#    if request.method == "GET":
#        val = request.args.get("val", "no value")
#        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
#        return render_template("hgm-search.html", title="Hypergeometric Motive Search", bread=bread, val=val)
#    elif request.method == "POST":
#        return "ERROR: we always do http get to explicitly display the search parameters"
#    else:
#        return flask.abort(404)
    

def hgm_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results", '')])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        return render_hgm_webpage({'label': info['jump_to']})

    family_search = False
    if info.get('Submit Family') or info.get('family'):
        family_search = True

    # generic, irreducible not in DB yet
    for param in ['A', 'B', 'hodge', 'a2', 'b2', 'a3', 'b3', 'a5', 'b5', 'a7', 'b7']:
        if info.get(param):
            info[param] = clean_input(info[param])
            if IF_RE.match(info[param]):
                query[param] = split_list(info[param])
                query[param].sort()
            else:
                name = param
                if name == 'hodge':
                    name = 'Hodge vector'
                info['err'] = 'Error parsing input for %s.  It needs to be a list of integers in square brackets, such as [2,3] or [1,1,1]' % name
                return search_input_error(info, bread)

    if info.get('t') and not family_search:
        info['t'] = clean_input(info['t'])
        try:
            tsage = QQ(str(info['t']))
            tlist = [int(tsage.numerator()), int(tsage.denominator())]
            query['t'] = tlist
        except:
            info['err'] = 'Error parsing input for t.  It needs to be a rational number, such as 2/3 or -3'

    # sign can only be 1, -1, +1
    if info.get('sign') and not family_search:
        sign = info['sign']
        sign = re.sub(r'\s','',sign)
        sign = clean_input(sign)
        if sign == '+1':
            sign = '1'
        if not (sign == '1' or sign == '-1'):
            info['err'] = 'Error parsing input %s for sign.  It needs to be 1 or -1' % sign
            return search_input_error(info, bread)
        query['sign'] = int(sign)


    for param in ['degree','weight','conductor']:
        # We don't look at conductor in family searches
        if info.get(param) and not (param=='conductor' and family_search):
            if param=='conductor':
                cond = info['conductor']
                try:
                    cond = re.sub(r'(\d)\s+(\d)', r'\1 * \2', cond) # implicit multiplication of numbers
                    cond = cond.replace(r'..', r'-') # all ranges use -
                    cond = re.sub(r'[a..zA..Z]', '', cond)
                    cond = clean_input(cond)
                    tmp = parse_range2(cond, 'cond', myZZ)
                except:
                    info['err'] = 'Error parsing input for conductor.  It needs to be an integer (e.g., 8), a range of integers (e.g. 10-100), or a list of such (e.g., 5,7,8,10-100).  Integers may be given in factored form (e.g. 2^5 3^2) %s' % cond
                    return search_input_error(info, bread)
            else: # not conductor
                info[param] = clean_input(info[param])
                ran = info[param]
                ran = ran.replace(r'..', r'-')
                if LIST_RE.match(ran):
                    tmp = parse_range2(ran, param)
                else:
                    names = {'weight': 'weight', 'degree': 'degree'}
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

    #print query
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
    if family_search:
        res = C.hgm.families.find(query).sort([('label', pymongo.ASCENDING)])
    else:
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
    info['make_label'] = make_abt_label
    info['make_t_label'] = make_t_label
    info['ab_label'] = ab_label
    info['display_t'] = display_t
    info['family'] = family_search
    info['factorint'] = factorint

    if family_search:
        return render_template("hgm-search.html", info=info, title="Hypergeometric Family over $\Q$ Search Result", bread=bread, credit=HGM_credit)
    else:
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
        # Now add factorization of conductor
        Cond = ZZ(data['cond'])
        if not (Cond.abs().is_prime() or Cond == 1):
            data['cond'] = "%s=%s" % (str(Cond), factorint(data['cond']))

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
        friends = [('Motives in the family', url_for('hypergm.index')+"?A=%s&B=%s" % (str(A), str(B)))]
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
