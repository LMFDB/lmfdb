#-*- coding: utf-8 -*-
# This Blueprint is about p-adic fields (aka local number fields)
# Author: John Jones

from flask import abort, render_template, request, url_for, redirect
from sage.all import (
    PolynomialRing, QQ, RR, latex, cached_function, Integers)

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    web_latex, coeff_to_poly, pol_to_html, display_multiset, display_knowl,
    parse_inertia,
    parse_galgrp, parse_ints, clean_input, parse_rats, flash_error,
    SearchArray, TextBox, TextBoxNoEg, CountBox, to_dict, comma,
    search_wrap, Downloader, StatsDisplay, totaler, proportioners,
    redirect_no_cache, raw_typeset)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.local_fields import local_fields_page, logger
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.galois_groups.transitive_group import (
    transitive_group_display_knowl, group_display_inertia,
    knowl_cache, galdata, galunformatter,
    group_pretty_and_nTj, WebGaloisGroup)
from lmfdb.number_fields.web_number_field import (
    WebNumberField, string2list, nf_display_knowl)

import re
LF_RE = re.compile(r'^\d+\.\d+\.\d+\.\d+$')

def get_bread(breads=[]):
    bc = [("$p$-adic fields", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Source and acknowledgments', url_for(".source")),
            ('Completeness of the data', url_for(".cande")),
            ('Reliability of the data', url_for(".reliability")),
            ('$p$-adic field labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def display_poly(coeffs):
    return web_latex(coeff_to_poly(coeffs))

def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))

def lf_formatfield(coef):
    coef = string2list(coef)
    thefield = WebNumberField.from_coeffs(coef)
    thepoly = coeff_to_poly(coef)
    thepolylatex = '$%s$' % latex(coeff_to_poly(coef))
    if thefield._data is None:
        return raw_typeset(thepoly, thepolylatex)
    return nf_display_knowl(thefield.get_label(),thepolylatex)

def local_algebra_data(labels):
    labs = labels.split(',')
    f1 = labs[0].split('.')
    labs = sorted(labs, key=lambda u: (int(j) for j in u.split('.')), reverse=True)
    ans = '<div align="center">'
    ans += '$%s$-adic algebra'%str(f1[0])
    ans += '</div>'
    ans += '<p>'
    ans += "<table class='ntdata'><th>Label<th>Polynomial<th>$e$<th>$f$<th>$c$<th>$G$<th>Slopes"
    fall = [db.lf_fields.lookup(label) for label in labs]
    for f in fall:
        l = str(f['label'])
        ans += '<tr><td><a href="%s">%s</a><td>'%(url_for_label(l),l)
        ans += format_coeffs(f['coeffs'])
        ans += '<td>%d<td>%d<td>%d<td>'%(f['e'],f['f'],f['c'])
        ans += transitive_group_display_knowl(f['galois_label'])
        ans += '<td>$'+ show_slope_content(f['slopes'],f['t'],f['u'])+'$'
    ans += '</table>'
    if len(labs) != len(set(labs)):
        ans +='<p>Fields which appear more than once occur according to their given multiplicities in the algebra'
    return ans

def local_field_data(label):
    f = db.lf_fields.lookup(label)
    nicename = ''
    if f['n'] < 3:
        nicename = ' = '+ prettyname(f)
    ans = '$p$-adic field %s%s<br><br>'% (label, nicename)
    ans += r'Extension of $\Q_{%s}$ defined by %s<br>'%(str(f['p']),web_latex(coeff_to_poly(f['coeffs'])))
    gt = int(f['galois_label'].split('T')[1])
    gn = f['n']
    ans += 'Degree: %s<br>' % str(gn)
    ans += 'Ramification index $e$: %s<br>' % str(f['e'])
    ans += 'Residue field degree $f$: %s<br>' % str(f['f'])
    ans += 'Discriminant ideal:  $(p^{%s})$ <br>' % str(f['c'])
    ans += 'Galois group $G$: %s<br>' % group_pretty_and_nTj(gn, gt, True)
    ans += '<div align="right">'
    ans += '<a href="%s">%s home page</a>' % (str(url_for("local_fields.by_label", label=label)),label)
    ans += '</div>'
    return ans


def lf_display_knowl(label, name=None):
    if name is None:
        name = label
    return '<a title = "%s [lf.field.data]" knowl="lf.field.data" kwargs="label=%s">%s</a>' % (label, label, name)

def local_algebra_display_knowl(labels):
    return '<a title = "{0} [lf.algebra.data]" knowl="lf.algebra.data" kwargs="labels={0}">{0}</a>' % (labels)

@app.context_processor
def ctx_local_fields():
    return {'local_field_data': local_field_data,
            'local_algebra_data': local_algebra_data}

# Utilities for subfield display
def format_lfield(coefmult,p):
    coefmult = [int(c) for c in coefmult.split(",")]
    data = db.lf_fields.lucky({'coeffs':coefmult, 'p': p}, projection=1)
    if data is None:
        # This should not happen, what do we do?
        # This is wrong
        return ''
    return lf_display_knowl(data['label'], name = prettyname(data))


# Input is a list of pairs, coeffs of field as string and multiplicity
def format_subfields(subdata, p):
    if not subdata:
        return ''
    return display_multiset(subdata, format_lfield, p)


# Encode string for rational into our special format
def ratproc(inp):
    if '.' in inp:
        inp = RR(inp)
    qs = QQ(inp)
    sstring = str(qs*1.)
    sstring += '0'*14
    if qs < 10:
        sstring = '0'+sstring
    sstring = sstring[0:12]
    sstring += str(qs)
    return sstring

def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return(sl)

def show_slope_content(sl,t,u):
    sc = str(sl)
    if sc == '[]':
        sc = r'[\ ]'
    if t>1:
        sc += '_{%d}'%t
    if u>1:
        sc += '^{%d}'%u
    return(sc)

@local_fields_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=LFSearchArray(), stats=LFStats())
    if len(request.args) != 0:
        return local_field_search(info)
    return render_template("lf-index.html", title="$p$-adic fields", titletag="p-adic fields", bread=bread, info=info, learnmore=learnmore_list())


@local_fields_page.route("/<label>")
def by_label(label):
    clean_label = clean_input(label)
    if label != clean_label:
        return redirect(url_for_label(label=clean_label), 301)
    return render_field_webpage({'label': label})

def url_for_label(label):
    if label == "random":
        return url_for('.random_field')
    return url_for(".by_label", label=label)

def local_field_jump(info):
    return redirect(url_for_label(info['jump']), 301)

class LF_download(Downloader):
    table = db.lf_fields
    title = '$p$-adic fields'
    columns = ['p', 'coeffs']
    data_format = ['p', '[coeffs]']
    data_description = 'defining the $p$-adic field over Qp by adjoining a root of f(x).'
    function_body = {'magma':['Prec := 100; // Default precision of 100',
                              'return [LocalField( pAdicField(r[1], Prec) , PolynomialRing(pAdicField(r[1], Prec))![c : c in r[2]] ) : r in data];'],
                     'sage':['Prec = 100 # Default precision of 100',
                             "return [pAdicExtension(Qp(r[0], Prec), PolynomialRing(Qp(r[0], Prec),'x')(r[1]), var_name='x') for r in data]"],
                     'gp':['[[c[1], Polrev(c[2])]|c<-data];']}

lf_columns = SearchColumns([
    LinkCol("label", "lf.field.label", "Label", url_for_label, default=True),
    MathCol("n", "lf.degree", "$n$", short_title="degree"),
    ProcessedCol("coeffs", "lf.defining_polynomial", "Polynomial", format_coeffs, default=True),
    MathCol("p", "lf.qp", "$p$", default=True, short_title="prime"),
    MathCol("e", "lf.ramification_index", "$e$", default=True, short_title="ramification index"),
    MathCol("f", "lf.residue_field_degree", "$f$", default=True, short_title="residue field degree"),
    MathCol("c", "lf.discriminant_exponent", "$c$", default=True, short_title="discriminant exponent"),
    MultiProcessedCol("gal", "nf.galois_group", "Galois group",
                      ["n", "gal", "cache"],
                      lambda n, t, cache: group_pretty_and_nTj(n, t, cache=cache),
                      default=True),
    MathCol("u", "lf.unramified_degree", "$u$", short_title="unramified degree"),
    MathCol("t", "lf.tame_degree", "$t$", short_title="tame degree"),
    MultiProcessedCol("slopes", "lf.slope_content", "Slope content",
                      ["slopes", "t", "u"],
                      show_slope_content,
                      default=True, mathmode=True)],
    db_cols=["c", "coeffs", "e", "f", "gal", "label", "n", "p", "slopes", "t", "u"])

def lf_postprocess(res, info, query):
    cache = knowl_cache(list(set(f"{rec['n']}T{rec['gal']}" for rec in res)))
    for rec in res:
        rec["cache"] = cache
    return res

@search_wrap(table=db.lf_fields,
             title='$p$-adic field search results',
             titletag=lambda:'p-adic field search results',
             err_title='Local field search input error',
             columns=lf_columns,
             per_page=50,
             shortcuts={'jump': local_field_jump, 'download': LF_download()},
             postprocess=lf_postprocess,
             bread=lambda:get_bread([("Search results", ' ')]),
             learnmore=learnmore_list,
             url_for_label=url_for_label)
def local_field_search(info,query):
    parse_ints(info,query,'p',name='Prime p')
    parse_ints(info,query,'n',name='Degree')
    parse_ints(info,query,'u',name='Unramified degree')
    parse_ints(info,query,'t',name='Tame degree')
    parse_galgrp(info,query,'gal',qfield=('galois_label','n'))
    parse_ints(info,query,'c',name='Discriminant exponent c')
    parse_ints(info,query,'e',name='Ramification index e')
    parse_ints(info,query,'f',name='Residue field degree f')
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top slope', process=ratproc)
    parse_inertia(info,query,qfield=('inertia_gap','inertia'))
    parse_inertia(info,query,qfield=('wild_gap','wild_gap'), field='wild_gap')
    info['search_array'] = LFSearchArray()

def render_field_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        data = db.lf_fields.lookup(label)
        if data is None:
            if LF_RE.fullmatch(label):
                flash_error("Field %s was not found in the database.", label)
            else:
                flash_error("%s is not a valid label for a $p$-adic field.", label)
            return redirect(url_for(".index"))
        title = '$p$-adic field ' + prettyname(data)
        titletag = 'p-adic field ' + prettyname(data)
        polynomial = coeff_to_poly(data['coeffs'])
        p = data['p']
        Qp = r'\Q_{%d}' % p
        e = data['e']
        f = data['f']
        cc = data['c']
        gt = int(data['galois_label'].split('T')[1])
        gn = data['n']
        the_gal = WebGaloisGroup.from_nt(gn,gt)
        isgal = ' Galois' if the_gal.order() == gn else ' not Galois'
        abelian = ' and abelian' if the_gal.is_abelian() else ''
        galphrase = 'This field is'+isgal+abelian+r' over $\Q_{%d}.$'%p
        autstring = r'\Gal' if the_gal.order() == gn else r'\Aut'
        prop2 = [
            ('Label', label),
            ('Base', r'\(%s\)' % Qp),
            ('Degree', r'\(%s\)' % data['n']),
            ('e', r'\(%s\)' % e),
            ('f', r'\(%s\)' % f),
            ('c', r'\(%s\)' % cc),
            ('Galois group', group_pretty_and_nTj(gn, gt)),
        ]
        # Look up the unram poly so we can link to it
        unramlabel = db.lf_fields.lucky({'p': p, 'n': f, 'c': 0}, projection=0)
        if unramlabel is None:
            logger.fatal("Cannot find unramified field!")
            unramfriend = ''
        else:
            unramfriend = url_for_label(unramlabel)
            unramdata = db.lf_fields.lookup(unramlabel)

        Px = PolynomialRing(QQ, 'x')
        Pt = PolynomialRing(QQ, 't')
        Ptx = PolynomialRing(Pt, 'x')
        if data['f'] == 1:
            unramp = r'$%s$' % Qp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = raw_typeset(eisenp, web_latex(eisenp))

        else:
            unramp = data['unram'].replace('t','x')
            unramp = raw_typeset(unramp, web_latex(Px(str(unramp))))
            unramp = prettyname(unramdata)+' $\\cong '+Qp+'(t)$ where $t$ is a root of '+unramp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = raw_typeset(str(eisenp), web_latex(eisenp), extra=r'$\ \in'+Qp+'(t)[x]$')


        rflabel = db.lf_fields.lucky({'p': p, 'n': {'$in': [1, 2]}, 'rf': data['rf']}, projection=0)
        if rflabel is None:
            logger.fatal("Cannot find discriminant root field!")
            rffriend = ''
        else:
            rffriend = url_for_label(rflabel)
        gsm = data['gsm']
        if gsm == [0]:
            gsm = 'Not computed'
        elif gsm == [-1]:
            gsm = 'Does not exist'
        else:
            gsm = lf_formatfield(','.join(str(b) for b in gsm))

        if 'wild_gap' in data:
            wild_inertia = abstract_group_display_knowl(f"{data['wild_gap'][0]}.{data['wild_gap'][1]}")
        else:
            wild_inertia = 'data not computed'

        info.update({
                    'polynomial': raw_typeset(polynomial),
                    'n': data['n'],
                    'p': p,
                    'c': data['c'],
                    'e': data['e'],
                    'f': data['f'],
                    't': data['t'],
                    'u': data['u'],
                    'rf': lf_display_knowl( rflabel, name=printquad(data['rf'], p)),
                    'base': lf_display_knowl(str(p)+'.1.0.1', name='$%s$'%Qp),
                    'hw': data['hw'],
                    'slopes': show_slopes(data['slopes']),
                    'gal': group_pretty_and_nTj(gn, gt, True),
                    'gt': gt,
                    'inertia': group_display_inertia(data['inertia']),
                    'wild_inertia': wild_inertia,
                    'unram': unramp,
                    'eisen': eisenp,
                    'gms': data['gms'],
                    'gsm': gsm,
                    'galphrase': galphrase,
                    'autstring': autstring,
                    'subfields': format_subfields(data['subfields'],p),
                    'aut': data['aut'],
                    })
        friends = [('Galois group', "/GaloisGroup/%dT%d" % (gn, gt))]
        if unramfriend != '':
            friends.append(('Unramified subfield', unramfriend))
        if rffriend != '':
            friends.append(('Discriminant root field', rffriend))
        if data['is_completion']:
            friends.append(('Number fields with this completion',
                url_for('number_fields.number_field_render_webpage')+"?completions={}".format(label) ))
        downloads = [('Underlying data', url_for('.lf_data', label=label))]

        bread = get_bread([(label, ' ')])
        return render_template(
            "lf-show-field.html",
            title=title,
            titletag=titletag,
            bread=bread,
            info=info,
            properties=prop2,
            friends=friends,
            downloads=downloads,
            learnmore=learnmore_list(),
            KNOWL_ID="lf.%s" % label,
        )

def prettyname(ent):
    if ent['n'] <= 2:
        return printquad(ent['rf'], ent['p'])
    return ent['label']

@cached_function
def getu(p):
    if p == 2:
        return 5
    return int(Integers(p).quadratic_nonresidue())

def printquad(code, p):
    if code == [1, 0]:
        return(r'$\Q_{%s}$' % p)
    u = getu(p)
    if code == [1, 1]:
        return(r'$\Q_{%s}(\sqrt{%s})$' % (p,u))
    if code == [-1, 1]:
        return(r'$\Q_{%s}(\sqrt{-%s})$' % (p,u))
    s = code[0]
    if code[1] == 1:
        s = str(s) + r'\cdot '+str(u)
    return(r'$\Q_{' + str(p) + r'}(\sqrt{' + str(s) + '})$')

@local_fields_page.route("/data/<label>")
def lf_data(label):
    if not LF_RE.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    title = f"Local field data - {label}"
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    return datapage(label, "lf_fields", title=title, bread=bread)

@local_fields_page.route("/random")
@redirect_no_cache
def random_field():
    label = db.lf_fields.random()
    return url_for(".by_label", label=label)

@local_fields_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "lf",
        db.lf_fields,
        url_for_label,
        title=r"Some interesting $p$-adic fields",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list()
    )

@local_fields_page.route("/stats")
def statistics():
    title = "Local fields: statistics"
    bread = get_bread([("Statistics", " ")])
    return render_template("display_stats.html", info=LFStats(), title=title, bread=bread, learnmore=learnmore_list())

@local_fields_page.route("/Completeness")
def cande():
    t = 'Completeness of $p$-adic field data'
    tt = 'Completeness of p-adic field data'
    bread = get_bread([("Completeness", )])
    return render_template("single.html", kid='rcs.cande.lf',
                           title=t, titletag=tt, bread=bread,
                           learnmore=learnmore_list_remove('Completeness'))

@local_fields_page.route("/Labels")
def labels_page():
    t = 'Labels for $p$-adic fields'
    tt = 'Labels for p-adic fields'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='lf.field.label',
                  learnmore=learnmore_list_remove('label'),
                  title=t, titletag=tt, bread=bread)

@local_fields_page.route("/Source")
def source():
    t = 'Source and acknowledgments for $p$-adic field pages'
    ttag = 'Source and acknowledgments for p-adic field pages'
    bread = get_bread([("Source", '')])
    return render_template("multi.html", kids=['rcs.source.lf',
                           'rcs.ack.lf','rcs.cite.lf'],
                           title=t,
                           titletag=ttag, bread=bread,
                           learnmore=learnmore_list_remove('Source'))

@local_fields_page.route("/Reliability")
def reliability():
    t = 'Reliability of $p$-adic field data'
    ttag = 'Reliability of p-adic field data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.source.lf',
                           title=t, titletag=ttag, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))

class LFSearchArray(SearchArray):
    noun = "field"
    plural_noun = "fields"
    sorts = [("", "prime", ['p', 'n', 'c', 'label']),
             ("n", "degree", ['n', 'p', 'c', 'label']),
             ("c", "discriminant exponent", ['c', 'p', 'n', 'label']),
             ("e", "ramification index", ['e', 'n', 'p', 'c', 'label']),
             ("f", "residue degree", ['f', 'n', 'p', 'c', 'label']),
             ("gal", "Galois group", ['n', 'galT', 'p', 'c', 'label']),
             ("u", "Galois unramified degree", ['u', 'n', 'p', 'c', 'label']),
             ("t", "Galois tame degree", ['t', 'n', 'p', 'c', 'label']),
             ("s", "top slope", ['top_slope', 'p', 'n', 'c', 'label'])]
    jump_example = "2.4.6.7"
    jump_egspan = "e.g. 2.4.6.7"
    jump_knowl = "lf.search_input"
    jump_prompt = "Label"
    def __init__(self):
        degree = TextBox(
            name='n',
            label='Degree',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        qp = TextBox(
            name='p',
            label=r'Residue field characteristic',
            short_label='Residue characteristic',
            knowl='lf.residue_field',
            example='3',
            example_span='3, or a range like 3..7')
        c = TextBox(
            name='c',
            label='Discriminant exponent',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e = TextBox(
            name='e',
            label='Ramification index',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f = TextBox(
            name='f',
            label='Residue field degree',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        topslope = TextBox(
            name='topslope',
            label='Top slope',
            knowl='lf.top_slope',
            example='4/3',
            example_span='0, 1, 2, 4/3, 3.5, or a range like 3..5')
        gal = TextBoxNoEg(
            name='gal',
            label='Galois group',
            short_label='Galois group',
            knowl='nf.galois_group',
            example='5T3',
            example_span='list of %s, e.g. [8,3] or [16,7], group names from the %s, e.g. C5 or S12, and %s, e.g., 7T2 or 11T5' % (
                display_knowl('group.small_group_label', "GAP id's"),
                display_knowl('nf.galois_group.name', 'list of group labels'),
                display_knowl('gg.label', 'transitive group labels')))
        u = TextBox(
            name='u',
            label='Galois unramified degree',
            knowl='lf.unramified_degree',
            example='3',
            example_span='3, or a range like 1..4'
            )
        t = TextBox(
            name='t',
            label='Galois tame degree',
            knowl='lf.tame_degree',
            example='2',
            example_span='2, or a range like 2..3'
            )
        inertia = TextBox(
            name='inertia_gap',
            label='Inertia subgroup',
            knowl='lf.inertia_group_search',
            example='[3,1]',
            example_span='a %s, e.g. [8,3] or [16,7], a group name from the %s, e.g. C5 or S12, or a %s, e.g., 7T2 or 11T5' % (
                display_knowl('group.small_group_label', "GAP id"),
                display_knowl('nf.galois_group.name', 'list of group labels'),
                display_knowl('gg.label', 'transitive group label'))
            )
        wild = TextBox(
            name='wild_gap',
            label='Wild inertia subgroup',
            knowl='lf.wild_inertia_group_search',
            example='[4,1]',
            example_span='a %s, e.g. [8,3] or [16,7], a group name from the %s, e.g. C5 or S12, or a %s, e.g., 7T2 or 11T5' % (
                display_knowl('group.small_group_label', "GAP id"),
                display_knowl('nf.galois_group.name', 'list of group labels'),
                display_knowl('gg.label', 'transitive group label'))
            )
        results = CountBox()

        self.browse_array = [[degree], [qp], [c], [e], [f], [topslope], [u],
            [t], [gal], [inertia], [wild], [results]]
        self.refine_array = [[degree, qp, gal, u],
            [e, c, inertia, t],
            [f, topslope, wild]]

def ramdisp(p):
    return {'cols': ['n', 'e'],
            'constraint': {'p': p, 'n': {'$lte': 15}},
            'top_title':[('degree', 'lf.degree'),
                         ('and', None),
                         ('ramification index', 'lf.ramification_index'),
                         ('for %s-adic fields'%p, None)],
            'totaler': totaler(col_counts=False),
            'proportioner': proportioners.per_row_total}

def discdisp(p):
    return {'cols': ['n', 'c'],
            'constraint': {'p': p, 'n': {'$lte': 15}},
            'top_title':[('degree', 'lf.degree'),
                         ('and', None),
                         ('discriminant exponent', 'lf.discriminant_exponent'),
                         ('for %s-adic fields'%p, None)],
            'totaler': totaler(col_counts=False),
            'proportioner': proportioners.per_row_query(lambda n: {'n':int(n)})}

def galdisp(p, n):
    return {'cols': ['galois_label'],
            'constraint': {'p': p, 'n': n},
            'top_title':[('Galois groups', 'nf.galois_group'),
                         ('for %s-adic fields of'%p, None),
                         ('degree', 'lf.degree'),
                         (str(n), None)]}

# We want to look up gap ids and names only once, rather than once for each Galois group
@cached_function
def galcache():
    return knowl_cache(db.lf_fields.distinct("galois_label"))
def galformatter(gal):
    n, t = galdata(gal)
    return group_pretty_and_nTj(n, t, True, cache=galcache())
class LFStats(StatsDisplay):
    table = db.lf_fields
    baseurl_func = ".index"
    short_display = {'galois_label': 'Galois group',
                     'n': 'degree',
                     'e': 'ramification index',
                     'c': 'discriminant exponent'}
    sort_keys = {'galois_label': galdata}
    formatters = {
        'galois_label': galformatter
    }
    query_formatters = {
        'galois_label': (lambda gal: r'gal=%s' % (galunformatter(gal)))
    }

    stat_list = [
        ramdisp(2),
        ramdisp(3),
        discdisp(2),
        discdisp(3),
        galdisp(2, 4),
        galdisp(2, 6),
        galdisp(2, 8),
        galdisp(2, 10),
        galdisp(2, 12),
        galdisp(2, 14),
        galdisp(3, 6),
        galdisp(3, 9),
        galdisp(3, 12),
        galdisp(3, 15),
        galdisp(5, 10),
        galdisp(5, 15),
        galdisp(7, 14)
    ]

    def __init__(self):
        self.numfields = db.lf_fields.count()

    @property
    def short_summary(self):
        return self.summary + '  Here are some <a href="%s">further statistics</a>.' % (url_for(".statistics"))

    @property
    def summary(self):
        return r'The database currently contains %s %s, including all with $p < 200$ and %s $n < 16$.' % (
            comma(self.numfields),
            display_knowl("lf.padic_field", r"$p$-adic fields"),
            display_knowl("lf.degree", "degree")
        )
