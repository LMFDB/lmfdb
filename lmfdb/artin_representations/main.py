# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Authors: Paul-Olivier Dehaye, John Jones

import re
import random

from flask import render_template, request, url_for, redirect, abort
from sage.all import ZZ, cached_function

from lmfdb import db
from lmfdb.utils import (
    parse_primes, parse_restricted, parse_galgrp,
    parse_ints, parse_container, parse_bool, clean_input, flash_error,
    SearchArray, TextBox, TextBoxNoEg, ParityBox, CountBox,
    SubsetNoExcludeBox, TextBoxWithSelect, SelectBoxNoEg,
    display_knowl, search_wrap, to_dict, comma, prop_int_pretty, redirect_no_cache)
from lmfdb.utils.display_stats import StatsDisplay, totaler, proportioners, range_formatter
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.search_columns import SearchColumns, SearchCol, MathCol
from lmfdb.api import datapage
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.galois_groups.transitive_group import (
    complete_group_code, knowl_cache, galdata, galunformatter,
    group_pretty_and_nTj)

from lmfdb.artin_representations import artin_representations_page
#from lmfdb.artin_representations import artin_logger
from lmfdb.artin_representations.math_classes import (
    ArtinRepresentation, num2letters, artin_label_pretty)


LABEL_RE = re.compile(r'^\d+\.\d+\.\d+(t\d+)?\.[a-z]+\.[a-z]+$')
ORBIT_RE = re.compile(r'^\d+\.\d+\.\d+(t\d+)?\.[a-z]+$')
OLD_LABEL_RE = re.compile(r'^\d+\.\d+(e\d+)?(_\d+(e\d+)?)*\.\d+(t\d+)?\.\d+c\d+$')
OLD_ORBIT_RE = re.compile(r'^\d+\.\d+(e\d+)?(_\d+(e\d+)?)*\.\d+(t\d+)?\.\d+$')
Dn_RE = re.compile(r'^d\d+$')


# Utility for permutations
def cycle_string(lis):
    from sage.combinat.permutation import Permutation
    return Permutation(lis).cycle_string()

def get_bread(breads=[]):
    bc = [("Artin representations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Source and acknowledgments', url_for(".source")),
            ('Completeness of the data', url_for(".cande")),
            ('Reliability of the data', url_for(".reliability")),
            ('Artin representations labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def make_cond_key(D):
    D1 = ZZ(D)
    if D1 < 1:
        D1 = ZZ.one()
    D1 = int(D1.log(10))
    return '%04d%s' % (D1, str(D))


def parse_artin_orbit_label(label, safe=False):
    try:
        label = clean_input(label)
        if ORBIT_RE.match(label):
            return label
        if OLD_ORBIT_RE.match(label):
            newlabel = db.artin_old2new_labels.lookup(label)['new']
            if newlabel:
                return newlabel
    except Exception:
        if safe:
            return ''
    raise ValueError

def parse_artin_label(label, safe=False):
    try:
        label = clean_input(label)
        if LABEL_RE.match(label):
            return label
        if OLD_LABEL_RE.match(label):
            newlabel = db.artin_old2new_labels.lookup(label)['new']
        if newlabel:
            return newlabel
    except Exception:
        if safe:
            return ''
    raise ValueError

def both_labels(label):
    both = db.artin_old2new_labels.lucky({'$or': [{'old':label}, {'new': label}]})
    if both:
        return list(both.values())
    else:
        return [label]

# Is it a rep'n or an orbit, supporting old and new styles
def parse_any(label):
    try:
        newlabel = parse_artin_label(label)
        return ['rep', newlabel]
    except Exception:
        try:
            newlabel = parse_artin_orbit_label(label)
            return ['orbit', newlabel]
        except Exception:
            return ['malformed', label]


def add_lfunction_friends(friends, label):
    for label in both_labels(label):
        rec = db.lfunc_instances.lucky({'type':'Artin','url':'ArtinRepresentation/'+label})
        if rec:
            num = 10 if 'c' in label.split('.')[-1] else 8 # number of components of CMF label based on artin label (rep or orbit)
            for r in db.lfunc_instances.search({'Lhash':rec["Lhash"]}):
                s = r['url'].split('/')
                if r['type'] == 'CMF' and len(s) == num:
                    cmf_label = '.'.join(s[4:])
                    url = r['url'] if r['url'][0] == '/' else '/' + r['url']
                    friends.append(("Modular form " + cmf_label, url))
    return friends

@artin_representations_page.route("/")
def index():
    info = to_dict(request.args, search_array=ArtinSearchArray(), stats=ArtinStats())
    info['dim_list'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 20, 21, 24, 25, 27, 28, 30, 35, 40, 44, 45, 55, 56, 64, 70]
    bread = get_bread()
    if not request.args:
        return render_template("artin-representation-index.html", title="Artin representations", bread=bread, learnmore=learnmore_list(), info=info)
    else:
        return artin_representation_search(info)

def artin_representation_jump(info):
    label = info['jump']
    try:
        label = parse_artin_label(label)
    except ValueError:
        try:
            label = parse_artin_orbit_label(label)
        except ValueError:
            flash_error("%s is not in a valid form for an Artin representation label", label)
            return redirect(url_for(".index"))
    return redirect(url_for(".render_artin_representation_webpage", label=label), 307)

dihedrals =[ [4,2], [6,1], [8, 3], [10,1], [12,4], [14,1], [16,7],
  [ 18, 1 ], [ 20, 4 ], [ 22, 1 ], [ 24, 6 ], [ 26, 1 ], [ 28, 3 ], [ 30, 3 ],
  [ 32, 18 ], [ 34, 1 ], [ 36, 4 ], [ 38, 1 ], [ 40, 6 ], [ 42, 5 ], [ 44, 3 ],
  [ 46, 1 ], [ 48, 7 ], [ 50, 1 ], [ 52, 4 ], [ 54, 1 ], [ 56, 5 ], [ 58, 1 ],
  [ 60, 12 ], [ 62, 1 ], [ 64, 52 ], [ 66, 3 ], [ 68, 4 ], [ 70, 3 ], [ 72, 6 ],
  [ 74, 1 ], [ 76, 3 ], [ 78, 5 ], [ 80, 7 ], [ 82, 1 ], [ 84, 14 ], [ 86, 1 ],
  [ 88, 5 ], [ 90, 3 ], [ 92, 3 ], [ 94, 1 ], [ 96, 6 ], [ 98, 1 ], [ 100, 4 ],
  [ 102, 3 ], [ 104, 6 ], [ 106, 1 ], [ 108, 4 ], [ 110, 5 ], [ 112, 6 ],
  [ 114, 5 ], [ 116, 4 ], [ 118, 1 ], [ 120, 28 ], [ 122, 1 ], [ 124, 3 ],
  [ 126, 5 ], [ 128, 161 ], [ 130, 3 ], [ 132, 9 ], [ 134, 1 ], [ 136, 6 ],
  [ 138, 3 ], [ 140, 10 ], [ 142, 1 ], [ 144, 8 ], [ 146, 1 ], [ 148, 4 ],
  [ 150, 3 ], [ 152, 5 ], [ 154, 3 ], [ 156, 17 ], [ 158, 1 ], [ 160, 6 ],
  [ 162, 1 ], [ 164, 4 ], [ 166, 1 ], [ 168, 36 ], [ 170, 3 ], [ 172, 3 ],
  [ 174, 3 ], [ 176, 6 ], [ 178, 1 ], [ 180, 11 ], [ 182, 3 ], [ 184, 5 ],
  [ 186, 5 ], [ 188, 3 ], [ 190, 3 ], [ 192, 7 ], [ 194, 1 ], [ 196, 3 ],
  [ 198, 3 ], [ 200, 6 ] ]

@search_parser(clean_info=True, error_is_safe=True)
def parse_projective_group(inp, query, qfield):
    inp = inp.lower()
    inp = inp.replace('_','')
    if inp in ['v4', 'c2^2']:
        inp = 'd2'
    if inp == 's3':
        inp = 'd3'
    if inp == 'a5':
        query[qfield] = [60,5]
    elif inp == 'a4':
        query[qfield] = [12,3]
    elif inp == 's4':
        query[qfield] = [24,12]
    elif Dn_RE.match(inp):
        n = int(inp.replace('d',''))-2
        if n>=0 and n<len(dihedrals):
            query[qfield] = dihedrals[n]
        elif n>=0:
            query[qfield] = [-1,-2] # we don't have it
    else:
        try:
            mycode = complete_group_code(inp.upper())[0]
            query['Proj_nTj'] = [mycode[0],mycode[1]]
        except Exception:
            raise ValueError("Allowed values are A4, S4, A5, or Dn for an integer n>1, a GAP id, such as [4,1] or [12,5], a transitive group in nTj notation, such as 5T1, or a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>.")

@search_parser(clean_info=True)
def parse_projective_type(inp, query, qfield):
    #Deal with that we may have already set this field
    current = None
    if qfield in query:
        current = query[qfield]
    inp = inp.lower()
    if inp == 'a5':
        query[qfield] = [60,5]
        if current and current != query[qfield]:
            raise ValueError('Projective image and projective image type are inconsistent')
    elif inp == 'a4':
        query[qfield] = [12,3]
        if current and current != query[qfield]:
            raise ValueError('Projective image and projective image type are inconsistent')
    elif inp == 's4':
        query[qfield] = [24,12]
        if current and current != query[qfield]:
            raise ValueError('Projective image and projective image type are inconsistent')
    elif inp == 'dn':
        dih_list = [{qfield: z} for z in dihedrals]
        query[qfield] = {'$or': dih_list}
        #query[qfield] = {'$in': dihedrals}
        if current and current not in dihedrals:
            raise ValueError('Projective image and projective image type are inconsistent')
        elif current:
            query[qfield] = current

def url_for_label(label):
    return url_for(".render_artin_representation_webpage", label=label)

artin_columns = SearchColumns([
    SearchCol("galois_links", "artin.label", "Label", default=True),
    MathCol("dimension", "artin.dimension", "Dimension", default=True),
    MathCol("factored_conductor_latex", "artin.conductor", "Conductor", default=True),
    MathCol("num_ramps", "artin.ramified_primes", "Ramified prime count"),
    SearchCol("field_knowl", "artin.stem_field", "Artin stem field", default=True, short_title="Artin stem field"),
    SearchCol("pretty_galois_knowl", "artin.gg_quotient", "$G$", default=True, align="center", short_title="image"),
    SearchCol("projective_group", "artin.projective_image", "Projective image", align="center"),
    SearchCol("container", "artin.permutation_container", "Container", align="center"),
    MathCol("indicator", "artin.frobenius_schur_indicator", "Ind", default=True, short_title="indicator"),
    MathCol("trace_complex_conjugation", "artin.trace_of_complex_conj", r"$\chi(c)$", default=True, short_title="trace of complex conj.")],[
        "Baselabel", "GaloisConjugates", "Dim", "Conductor", "BadPrimes", "NFGal", "GaloisLabel", "Indicator", "Is_Even", "Container", "NumBadPrimes", "Proj_GAP", "Proj_nTj"])

artin_columns.above_table = "<div>Galois conjugate representations are grouped into single lines.</div>"
artin_columns.dummy_download = True

def artin_postprocess(res, info, query):
    gp_labels = list(set([rec["GaloisLabel"] for rec in res] + [rec["Container"].upper() for rec in res] + ["T".join(str(c) for c in rec["Proj_nTj"]) for rec in res]))
    cache = knowl_cache(gp_labels)
    return [ArtinRepresentation(data=x, knowl_cache=cache) for x in res]

@search_wrap(table=db.artin_reps,
             title='Artin representation search results',
             err_title='Artin representation search error',
             per_page=50,
             columns=artin_columns,
             learnmore=learnmore_list,
             url_for_label=url_for_label,
             shortcuts={'jump':artin_representation_jump},
             postprocess=artin_postprocess,
             bread=lambda:[('Artin representations', url_for(".index")), ('Search results', ' ')])
def artin_representation_search(info, query):
    query['Hide'] = 0
    info['sign_code'] = 0
    parse_primes(info,query,"unramified",name="Unramified primes",
                 qfield="BadPrimes",mode="exclude")
    parse_primes(info,query,"ramified",name="Ramified primes",
                 qfield="BadPrimes",mode=info.get("ram_quantifier"))
    parse_restricted(info,query,"root_number",qfield="GalConjSigns",allowed=[-1,1],process=lambda x:{"$contains":[int(x)]})
    parse_restricted(info,query,"frobenius_schur_indicator",qfield="Indicator",
                     allowed=[1,0,-1],process=int)
    parse_container(info,query, 'container',qfield='Container', name="Smallest permutation representation")
    parse_galgrp(info,query,"group",name="Group",qfield=("GaloisLabel",None))
    parse_ints(info,query,'dimension',qfield='Dim')
    parse_ints(info,query,'conductor',qfield='Conductor')
    parse_ints(info,query,'num_ram',qfield='NumBadPrimes')
    parse_projective_group(info, query, 'projective_image', qfield='Proj_GAP')
    parse_projective_type(info, query, 'projective_image_type', qfield='Proj_GAP')
    # Backward support for old URLs
    if 'Is_Even' in info:
        info['parity'] = info.pop('Is_Even')
    parse_bool(info,query,'parity',qfield='Is_Even')

@artin_representations_page.route("/<dim>/<conductor>/")
def by_partial_data(dim, conductor):
    return artin_representation_search({'dimension': dim, 'conductor': conductor, 'search_array': ArtinSearchArray()})


@artin_representations_page.route("/<label>/")
@artin_representations_page.route("/<label>")
def render_artin_representation_webpage(label):
    if re.compile(r'^\d+$').match(label):
        return artin_representation_search(**{'dimension': label, 'search_array': ArtinSearchArray()})

    # label=dim.cond.nTt.indexcj, c is literal, j is index in conj class
    # Should we have a big try around this to catch bad labels?
    clean_label = clean_input(label)
    if clean_label != label:
        return redirect(url_for('.render_artin_representation_webpage', label=clean_label), 301)
    # We could have a single representation or a Galois orbit
    case = parse_any(label)
    if case[0] == 'malformed':
        try:
            raise ValueError
        except Exception:
            flash_error("%s is not in a valid form for the label for an Artin representation or a Galois orbit of Artin representations", label)
            return redirect(url_for(".index"))
    # Do this twice to customize error messages
    newlabel = case[1]
    case = case[0]
    if case == 'rep':
        try:
            the_rep = ArtinRepresentation(newlabel)
        except Exception:
            newlabel = parse_artin_label(label)
            flash_error("Artin representation %s is not in database", label)
            return redirect(url_for(".index"))
    else: # it is an orbit
        try:
            the_rep = ArtinRepresentation(newlabel+'.a')
        except Exception:
            newlabel = parse_artin_orbit_label(newlabel)
            flash_error("Galois orbit of Artin representations %s is not in database", label)
            return redirect(url_for(".index"))
        # in this case we want all characters
        num_conj = the_rep.galois_conjugacy_size()
        allchars = [ ArtinRepresentation(newlabel+'.'+num2letters(j)).character_formatted() for j in range(1,num_conj+1)]

    label = newlabel
    bread = get_bread([(artin_label_pretty(label), ' ')])

    #artin_logger.info("Found %s" % (the_rep._data))

    if case=='rep':
        title = "Artin representation %s" % label
    else:
        title = "Galois orbit of Artin representations %s" % label
    the_nf = the_rep.number_field_galois_group()
    if the_rep.sign() == 0:
        processed_root_number = "not computed"
    else:
        processed_root_number = '$%s$' % the_rep.sign()
    properties = [("Label", artin_label_pretty(label)),
                  ("Dimension", prop_int_pretty(the_rep.dimension())),
                  ("Group", the_rep.group()),
                  ("Conductor", prop_int_pretty(the_rep.conductor()))]
    if case == 'rep':
        properties.append( ("Root number", processed_root_number) )
    properties.append( ("Indicator", prop_int_pretty(the_rep.indicator())) )

    friends = []
    wnf = None
    proj_wnf = None
    nf_url = the_nf.url_for()
    if nf_url:
        friends.append(("Field {}".format(the_nf.label()), nf_url))
        wnf = the_nf.wnf()
    proj_wnf = WebNumberField.from_coeffs(the_rep._data['Proj_Polynomial'])
    if proj_wnf.is_in_db():
        proj_coefs = [int(z) for z in proj_wnf.coeffs()]
        if proj_coefs != the_nf.polynomial():
            friends.append(("Field {}".format(proj_wnf.get_label()),
                str(url_for("number_fields.by_label", label=proj_wnf.get_label()))))
    if case == 'rep':
        cc = the_rep.central_character()
        if cc is not None:
            if the_rep.dimension()==1:
                if cc.order == 2:
                    cc_name = cc.symbol
                else:
                    cc_name = cc.texname
                friends.append(("Dirichlet character "+cc_name, url_for("characters.render_Dirichletwebpage", modulus=cc.modulus, number=cc.number)))
            else:
                detrep = the_rep.central_character_as_artin_rep()
                friends.append(("Determinant "+detrep.label(), detrep.url_for()))
        add_lfunction_friends(friends,label)

        # once the L-functions are in the database, the link can always be shown
        #if the_rep.dimension() <= 6:
        if the_rep.dimension() == 1:
            # Zeta is loaded differently
            if cc.modulus == 1 and cc.number == 1:
                friends.append(("L-function", url_for("l_functions.l_function_dirichlet_page", modulus=cc.modulus, number=cc.number)))
            else:
                # looking for Lhash dirichlet_L_modulus.number
                mylhash = 'dirichlet_L_%d.%d'%(cc.modulus,cc.number)
                lres = db.lfunc_instances.lucky({'Lhash': mylhash})
                if lres is not None:
                    friends.append(("L-function", url_for("l_functions.l_function_dirichlet_page", modulus=cc.modulus, number=cc.number)))

        # Dimension > 1
        elif int(the_rep.conductor())**the_rep.dimension() <= 729000000000000:
            friends.append(("L-function", url_for("l_functions.l_function_artin_page",
                                              label=the_rep.label())))
        orblabel = re.sub(r'\.[a-z]+$', '', label)
        friends.append(("Galois orbit " + artin_label_pretty(orblabel),
            url_for(".render_artin_representation_webpage", label=orblabel)))
    else:
        add_lfunction_friends(friends,label)
        friends.append(("L-function", url_for("l_functions.l_function_artin_page", label=the_rep.label())))
        for j in range(1,1+the_rep.galois_conjugacy_size()):
            newlabel = label+'.'+num2letters(j)
            friends.append(("Artin representation " + artin_label_pretty(newlabel),
                url_for(".render_artin_representation_webpage", label=newlabel)))

    info={} # for testing

    if case == 'rep':
        return render_template(
            "artin-representation-show.html",
            title=title,
            bread=bread,
            friends=friends,
            object=the_rep,
            cycle_string=cycle_string,
            wnf=wnf,
            proj_wnf=proj_wnf,
            properties=properties,
            downloads=[("Underlying data", url_for(".artin_data", label=orblabel))],
            info=info,
            learnmore=learnmore_list(),
            KNOWL_ID="artin.%s" % label,
        )
    # else we have an orbit
    return render_template(
        "artin-representation-galois-orbit.html",
        title=title,
        bread=bread,
        allchars=allchars,
        friends=friends,
        object=the_rep,
        cycle_string=cycle_string,
        wnf=wnf,
        proj_wnf=proj_wnf,
        properties=properties,
        downloads=[("Underlying data", url_for(".artin_data", label=label))],
        info=info,
        learnmore=learnmore_list(),
        KNOWL_ID="artin.%s" % label,
    )

@artin_representations_page.route("/data/<label>")
def artin_data(label):
    poly = db.artin_reps.lookup(label, "NFGal")
    if poly is None:
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    return datapage([label, poly], ["artin_reps", "artin_field_data"], bread=bread, title=f"Artin representation data - {label}", label_cols=["Baselabel", "Polynomial"])

@artin_representations_page.route("/random")
@redirect_no_cache
def random_representation():
    rep = db.artin_reps.random(projection=2)
    num = random.randrange(len(rep['GaloisConjugates']))
    label = rep['Baselabel']+"."+num2letters(num+1)
    return url_for(".render_artin_representation_webpage", label=label)

@artin_representations_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "artin",
        db.artin_reps,
        url_for_label,
        label_col="Baselabel",
        title=r"Some interesting Artin representations",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list(),
    )

@artin_representations_page.route("/stats")
def statistics():
    title = "Artin representations: statistics"
    bread = get_bread([("Statistics", " ")])
    return render_template("display_stats.html", info=ArtinStats(), title=title, bread=bread, learnmore=learnmore_list())

@artin_representations_page.route("/Labels")
def labels_page():
    t = 'Labels for Artin representations'
    bread = get_bread([("Labels", '')])
    learnmore = learnmore_list_remove('labels')
    return render_template("single.html", kid='artin.label',learnmore=learnmore, title=t, bread=bread)

@artin_representations_page.route("/Source")
def source():
    t = 'Source and acknowledgments for Artin representation pages'
    bread = get_bread([("Source", '')])
    learnmore = learnmore_list_remove('Source')
    return render_template("multi.html",
                           kids=['rcs.source.artin',
                                 'rcs.ack.artin',
                                 'rcs.cite.artin'],
                           title=t, bread=bread,
                           learnmore=learnmore)

@artin_representations_page.route("/Reliability")
def reliability():
    t = 'Reliability of Artin representation data'
    bread = get_bread([("Reliability", '')])
    learnmore = learnmore_list_remove('Reliability')
    return render_template("single.html", kid='rcs.rigor.artin',
                           title=t, bread=bread,
                           learnmore=learnmore)

@artin_representations_page.route("/Completeness")
def cande():
    t = 'Completeness of Artin representation data'
    bread = get_bread([("Completeness", '')])
    learnmore = learnmore_list_remove('Completeness')
    return render_template("single.html", kid='rcs.cande.artin',
                           title=t, bread=bread,
                           learnmore=learnmore)

class ArtinSearchArray(SearchArray):
    noun = "representation"
    plural_noun = "representations"
    sorts = [("", "dimension", ["Dim", "Conductor", "Galn", "Galt", "Baselabel"]),
             ("con", "conductor", ["Conductor", "Dim", "Galn", "Galt", "Baselabel"]),
             ("group", "group", ["Galn", "Galt", "Dim", "Conductor", "Baselabel"]),
             #("container", "container", ["Container", "Galn", "Galt", "Dim", "Conductor", "Baselabel"]),
             ("num_ramps", "ramified prime count", ["NumBadPrimes", "Conductor", "Dim", "Galn", "Galt", "Baselabel"]),
             ("projective_group", "projective image", ["Proj_nTj", "Proj_Polynomial", "Dim", "Conductor", "Galn", "Galt", "Baselabel"])]
    jump_example = "4.5648.6t13.b.a"
    jump_egspan = "e.g. 4.5648.6t13.b.a"
    jump_knowl = "artin.search_input"
    jump_prompt = "Label"
    def __init__(self):
        dimension = TextBox(
            name="dimension",
            label="Dimension",
            knowl="artin.dimension",
            example="2",
            example_span="1, 2-4")
        conductor = TextBox(
            name="conductor",
            label="Conductor",
            knowl="artin.conductor",
            example="51,100-200")
        group = TextBoxNoEg(
            name="group",
            label="Group",
            knowl="artin.gg_quotient",
            example="A5",
            example_span="%s, e.g. [8,3] or [16,7];%s, e.g. C5 or S12; %s, e.g., 7T2 or 11T5" % (
                display_knowl("group.small_group_label", "GAP id's"),
                display_knowl("nf.galois_group.name", "group names"),
                display_knowl("gg.label", "transitive group labels")))
        parity = ParityBox(
            name="parity",
            label="Parity",
            knowl="artin.parity")
        container = TextBox(
            name="container",
            label="Smallest permutation container",
            short_label="Smallest permutation",
            knowl="artin.permutation_container",
            example="6T13",
            example_span="6T13 or 7T6")
        ram_quantifier = SubsetNoExcludeBox(
            name="ram_quantifier")
        ramified = TextBoxWithSelect(
            name="ramified",
            label="Ramified primes",
            short_label="Ramified",
            knowl="artin.ramified_primes",
            example="2, 3",
            select_box=ram_quantifier,
            example_span="2, 3 (no range allowed)")
        unramified = TextBox(
            name="unramified",
            label="Unramified primes",
            knowl="artin.unramified_primes",
            example="5,7",
            example_span="5, 7, 13 (no range allowed)")
        num_ram = TextBox(
            name="num_ram",
            label="Ramified prime count",
            knowl="artin.ramified_primes",
            example="1")
        root_number = TextBoxNoEg(
            name="root_number",
            label="Root number",
            knowl="artin.root_number",
            example="1",
            example_span="at the moment, one of 1 or -1")
        fsind = TextBoxNoEg(
            name="frobenius_schur_indicator",
            label="Frobenius-Schur indicator",
            short_label="Frobenius-Schur",
            knowl="artin.frobenius_schur_indicator",
            example="1",
            example_span="+1 for orthogonal, -1 for symplectic, 0 for non-real character")
        projective_image = TextBoxNoEg(
            name='projective_image',
            label='Projective image',
            knowl='artin.projective_image',
            example_span="a GAP id, such as [4,1] or [12,5], a transitive group in nTj notation, such as 5T1, or a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>.",
            example='D5')
        projective_image_type = SelectBoxNoEg(
            name='projective_image_type',
            knowl='artin.projective_image_type',
            label='Projective image type',
            example_span='',
            options=[('', ''),
                     ('Dn', 'Dn'),
                     ('A4', 'A4'),
                     ('S4', 'S4'),
                     ('A5','A5')])
        count = CountBox()

        self.browse_array = [
            [dimension],
            [conductor],
            [group],
            [parity],
            [container],
            [ramified],
            [unramified],
            [num_ram],
            [root_number],
            [fsind],
            [projective_image],
            [projective_image_type],
            [count]]

        self.refine_array = [
            [dimension, conductor, group, root_number, parity],
            [container, ramified, unramified, num_ram, fsind],
            [projective_image, projective_image_type]]

def scinot(rng, minlen=None):
    if "^" in rng or not rng:
        return rng
    if "-" in rng:
        pieces = rng.split("-")
        minlen = min(len(piece) for piece in pieces if piece)
        return "-".join(scinot(piece, minlen) for piece in pieces)
    if minlen is None:
        minlen = len(rng)
    if minlen > 3 and rng[0] == "1" and rng[-1] in ["0", "1"] and all(ch == "0" for ch in rng[1:-1]):
        return "$10^{%s}$" % (len(rng)-1)
    return "$%s$" % rng

tpow = re.compile(r"10\^\{(\d+)\}")
def unsci(rng, first=False):
    if "^" not in rng:
        return rng
    if "-" in rng:
        pieces = "-".split(rng)
        fz = [True] + [False]*(len(pieces)-1)
        return "-".join(unsci(piece, z) for (piece, z) in zip(pieces, fz))
    e = tpow.findall(rng)
    if not e:
        return rng
    if first:
        return str(1 + 10**int(e[0]))
    else:
        return str(10**int(e[0]))

def trange(a, b):
    if b is None:
        return str(10**a) + "-"
    elif a == 0:
        return "1-" + str(10**b)
    return str(10**a+1) + "-" + str(10**b)
def intervals(start, end, step):
    return [(a, a+step) for a in range(start, end, step)]

@cached_function
def galcache():
    return knowl_cache(db.artin_reps.distinct("GaloisLabel"))
def galformatter(gal):
    n, t = galdata(gal)
    return group_pretty_and_nTj(n, t, True, cache=galcache())

@cached_function
def projcache():
    return knowl_cache(["%sT%s" % tuple(label) for label in db.artin_reps.distinct("Proj_nTj")])
def projformatter(proj):
    if isinstance(proj, list):
        proj = "%sT%s" % tuple(proj)
    n, t = galdata(proj)
    return group_pretty_and_nTj(n, t, True, cache=projcache(), skip_nTj=True)

@cached_function
def contcache():
    return knowl_cache([label for label in db.artin_reps.distinct("Container") if "T" in label])
def contformatter(cont):
    n, t = galdata(cont)
    if t == 0: # no T number
        return cont
    return group_pretty_and_nTj(n, t, True, cache=contcache())

class ArtinStats(StatsDisplay):
    table = db.artin_reps
    baseurl_func = ".index"

    stat_list = [
        {"cols": ["Dim", "Conductor"],
         "constraint": {"Hide": 0},
         "totaler": totaler(),
         "proportioner": proportioners.per_row_total},
        {"cols": ["Dim", "NumBadPrimes"],
         "constraint": {"Hide": 0},
         "totaler": totaler(),
         "proportioner": proportioners.per_row_total},
        {"cols": ["Indicator", "Dim"],
         "constraint": {"Hide": 0}},
        {"cols": ["Is_Even", "Dim"],
         "constraint": {"Hide": 0}},
        {"cols": ["GaloisLabel"],
         "constraint": {"Hide": 0}},
        {"cols": ["Proj_nTj"],
         "constraint": {"Hide": 0}},
        {"cols": ["Container"],
         "constraint": {"Hide": 0}}
    ]
    knowls = {"Dim": "artin.dimension",
              "Conductor": "artin.conductor",
              "GaloisLabel": "artin.gg_quotient",
              "Is_Even": "artin.parity",
              "Proj_nTj": "artin.projective_image",
              "NumBadPrimes": "artin.ramified_primes",
              "Container": "artin.permutation_container",
              "Indicator": "artin.frobenius_schur_indicator"}
    top_titles = {"Indicator": "Frobenius-Schur indicators",
                  "Container": "smallest permutation containers",
                  "Is_Even": "parities"}
    short_display = {"Dim": "dimension",
                     "Conductor": "conductor",
                     "GaloisLabel": "Galois group",
                     "Is_Even": "parity",
                     "Proj_nTj": "projective image",
                     "Container": "container",
                     "NumBadPrimes": "number of ramified primes",
                     "Indicator": "indicator"}
    sort_keys = {"GaloisLabel": galdata,
                 "Proj_nTj": galdata,
                 "Container": galdata}
    formatters = {"Conductor": lambda N: scinot(range_formatter(N)),
                  "Is_Even": lambda x: "even" if x in ["even", True] else "odd",
                  "GaloisLabel": galformatter,
                  "Container": contformatter,
                  "Proj_nTj": projformatter}
    query_formatters = {
        "Dim": (lambda d: "dimension=%s" % range_formatter(d)),
        "Conductor": (lambda N: "conductor=%s" % (unsci(range_formatter(N)))),
        "NumBadPrimes": (lambda N: "num_ram=%s" % range_formatter(N)),
        "GaloisLabel": (lambda gal: r"group=%s" % (galunformatter(gal))),
        "Proj_nTj": (lambda proj: r"projective_image=%s" % (galunformatter(proj))),
        "Container": (lambda cont: r"container=%s" % (galunformatter(cont))),
        "Is_Even": (lambda x: r"parity=%s" % ("even" if x in ["even", True] else "odd")),
        "Indicator": (lambda ind: r"frobenius_schur_indicator=%s" % ind),
    }
    buckets = {
        "Conductor": [trange(a, b) for (a,b) in intervals(0,8,2) + intervals(8,24,4) + intervals(24,56,8) + intervals(56,88,16)] + [trange(88,None)],
        "Dim": [str(x) for x in range(1,13)] + ["14-21", "24-30", "35", "40-70"]
    }

    def __init__(self):
        hide = {"Hide": 0}
        self.nreps = db.artin_reps.count(hide)
        self.nfields = db.artin_reps.count_distinct("NFGal", hide)
        self.ngroups = db.artin_reps.count_distinct("GaloisLabel", hide)
        self.maxdim = db.artin_reps.max("Dim")
        maxcond = ZZ(db.artin_reps.max("Conductor"))
        self.maxcond = maxcond.factor()._latex_()
        self.amaxcond = maxcond.n(digits=2)._latex_()

    @property
    def summary(self):
        return r"The database currently contains {nreps} Galois conjugacy classes of {repknowl}, for a total of {nfields} {nfknowl} with {ngroups} {gpknowl}.  The largest {dimknowl} is ${mdim}$ and the largest {condknowl} is ${mcond} \approx {amcond}$.".format(
            nreps=comma(self.nreps),
            repknowl=display_knowl("artin", "Artin representations"),
            nfields=comma(self.nfields),
            nfknowl=display_knowl("artin.number_field", "number fields"),
            ngroups=self.ngroups,
            gpknowl=display_knowl("artin.gg_quotient", "Galois groups"),
            dimknowl=display_knowl("artin.dimension", "dimension"),
            mdim=self.maxdim,
            condknowl=display_knowl("artin.conductor", "conductor"),
            mcond=self.maxcond,
            amcond=self.amaxcond)

    @property
    def short_summary(self):
        return r'The database currently contains {nreps} Galois conjugacy classes of {repknowl}, for a total of {nfields} {nfknowl}.  Here are some <a href="{url}">further statistics</a>.'.format(
            nreps=comma(self.nreps),
            repknowl=display_knowl("artin", "Artin representations"),
            nfields=comma(self.nfields),
            nfknowl=display_knowl("artin.number_field", "number fields"),
            url=url_for(".statistics"))
