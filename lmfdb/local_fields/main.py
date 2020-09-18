#-*- coding: utf-8 -*-
# This Blueprint is about p-adic fields (aka local number fields)
# Author: John Jones

from flask import render_template, request, url_for, redirect
from sage.all import PolynomialRing, QQ, RR, latex

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    web_latex, coeff_to_poly, pol_to_html, display_multiset, display_knowl,
    parse_galgrp, parse_ints, clean_input, parse_rats, flash_error,
    SearchArray, TextBox, TextBoxNoEg, CountBox, to_dict,
    search_wrap, Downloader)
from lmfdb.local_fields import local_fields_page, logger
from lmfdb.galois_groups.transitive_group import (
    group_display_knowl, group_display_inertia,
    group_pretty_and_nTj, small_group_data, WebGaloisGroup)
from lmfdb.number_fields.web_number_field import (
    WebNumberField, string2list, nf_display_knowl)

import re

LF_credit = 'J. Jones and D. Roberts'

def get_bread(breads=[]):
    bc = [("$p$-adic fields", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".cande")),
            ('Source of the data', url_for(".source")),
            ('Reliability of the data', url_for(".reliability")),
            ('Local field labels', url_for(".labels_page"))]

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
    thepoly = '$%s$' % latex(coeff_to_poly(coef))
    if thefield._data is None:
        return thepoly
    return nf_display_knowl(thefield.get_label(),thepoly)

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
        ans += '<tr><td><a href="/LocalNumberField/%s">%s</a><td>'%(l,l)
        ans += format_coeffs(f['coeffs'])
        ans += '<td>%d<td>%d<td>%d<td>'%(f['e'],f['f'],f['c'])
        galnt = [int(z) for z in f['galois_label'].split('T')]
        ans += group_display_knowl(galnt[0],galnt[1])
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
            'small_group_data': small_group_data,
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

@local_fields_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=LFSearchArray())
    if len(request.args) != 0:
        return local_field_search(info)
    return render_template("lf-index.html", title="$p$-adic fields", bread=bread, credit=LF_credit, info=info, learnmore=learnmore_list())


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
    data_description = 'defining the local field over Qp by adjoining a root of f(x).'
    function_body = {'magma':['Prec := 100; // Default precision of 100',
                              'return [LocalField( pAdicField(r[1], Prec) , PolynomialRing(pAdicField(r[1], Prec))![c : c in r[2]] ) : r in data];'],
                     'sage':['Prec = 100 # Default precision of 100',
                             "return [pAdicExtension(Qp(r[0], Prec), PolynomialRing(Qp(r[0], Prec),'x')(r[1]), var_name='x') for r in data]"],
                     'gp':['[[c[1], Polrev(c[2])]|c<-data];']}


@search_wrap(template="lf-search.html",
             table=db.lf_fields,
             title='$p$-adic field search results',
             err_title='Local field search input error',
             per_page=50,
             shortcuts={'jump': local_field_jump, 'download': LF_download()},
             bread=lambda:get_bread([("Search results", ' ')]),
             learnmore=learnmore_list,
             url_for_label=url_for_label,
             credit=lambda:LF_credit)
def local_field_search(info,query):
    parse_ints(info,query,'p',name='Prime p')
    parse_ints(info,query,'n',name='Degree')
    parse_galgrp(info,query,'gal',qfield=('galois_label','n'))
    parse_ints(info,query,'c',name='Discriminant exponent c')
    parse_ints(info,query,'e',name='Ramification index e')
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top slope', process=ratproc)
    info['group_display'] = group_pretty_and_nTj
    info['display_poly'] = format_coeffs
    info['slopedisp'] = show_slope_content
    info['search_array'] = LFSearchArray()

def render_field_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        data = db.lf_fields.lookup(label)
        if data is None:
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', label):
                flash_error("Field %s was not found in the database.", label)
            else:
                flash_error("%s is not a valid label for a $p$-adic field.", label)
            return redirect(url_for(".index"))
        title = '$p$-adic field ' + prettyname(data)
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
        galphrase = 'This field is'+isgal+abelian+r' over $\Q_{%d}$.'%p
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
            unramfriend = "/LocalNumberField/%s" % unramlabel
            unramdata = db.lf_fields.lookup(unramlabel)

        Px = PolynomialRing(QQ, 'x')
        Pt = PolynomialRing(QQ, 't')
        Ptx = PolynomialRing(Pt, 'x')
        if data['f'] == 1:
            unramp = r'$%s$' % Qp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = web_latex(eisenp)

        else:
            unramp = data['unram'].replace('t','x')
            unramp = web_latex(Px(str(unramp)))
            unramp = prettyname(unramdata)+' $\\cong '+Qp+'(t)$ where $t$ is a root of '+unramp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = '$'+web_latex(eisenp, False)+'\\in'+Qp+'(t)[x]$'


        rflabel = db.lf_fields.lucky({'p': p, 'n': {'$in': [1, 2]}, 'rf': data['rf']}, projection=0)
        if rflabel is None:
            logger.fatal("Cannot find discriminant root field!")
            rffriend = ''
        else:
            rffriend = "/LocalNumberField/%s" % rflabel
        gsm = data['gsm']
        if gsm == [0]:
            gsm = 'Not computed'
        elif gsm == [-1]:
            gsm = 'Does not exist'
        else:
            gsm = lf_formatfield(','.join([str(b) for b in gsm]))


        info.update({
                    'polynomial': web_latex(polynomial),
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

        bread = get_bread([(label, ' ')])
        return render_template("lf-show-field.html", credit=LF_credit, title=title, bread=bread, info=info, properties=prop2, friends=friends, learnmore=learnmore_list())


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

def prettyname(ent):
    if ent['n'] <= 2:
        return printquad(ent['rf'], ent['p'])
    return ent['label']

def printquad(code, p):
    if code == [1, 0]:
        return(r'$\Q_{%s}$' % p)
    if code == [1, 1]:
        return(r'$\Q_{%s}(\sqrt{*})$' % p)
    if code == [-1, 1]:
        return(r'$\Q_{%s}(\sqrt{-*})$' % p)
    s = code[0]
    if code[1] == 1:
        s = str(s) + '*'
    return(r'$\Q_{' + str(p) + r'}(\sqrt{' + str(s) + '})$')


def search_input_error(info, bread):
    return render_template("lf-search.html", info=info, title='Local field search input error', bread=bread)

@local_fields_page.route("/random")
def random_field():
    label = db.lf_fields.random()
    return redirect(url_for(".by_label", label=label), 307)

@local_fields_page.route("/Completeness")
def cande():
    t = 'Completeness of local field data'
    bread = get_bread([("Completeness", )])
    return render_template("single.html", kid='rcs.cande.lf',
                           credit=LF_credit, title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Completeness'))

@local_fields_page.route("/Labels")
def labels_page():
    t = 'Labels for $p$-adic fields'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='lf.field.label',
                  learnmore=learnmore_list_remove('label'), 
                  credit=LF_credit, title=t, bread=bread)

@local_fields_page.route("/Source")
def source():
    t = 'Source of local field data'
    bread = get_bread([("Source", '')])
    return render_template("single.html", kid='rcs.source.lf',
                           credit=LF_credit, title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'))

@local_fields_page.route("/Reliability")
def reliability():
    t = 'Reliability of local field data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.source.lf',
                           credit=LF_credit, title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'))

class LFSearchArray(SearchArray):
    noun = "field"
    plural_noun = "fields"
    jump_example = "2.4.6.7"
    jump_egspan = "e.g. 2.4.6.7"
    def __init__(self):
        degree = TextBox(
            name='n',
            label='Degree',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        qp = TextBox(
            name='p',
            label=r'Prime $p$ for base field $\Q_p$',
            short_label='Prime $p$',
            knowl='lf.qp',
            example='3',
            example_span='3, or a range like 3..7')
        c = TextBox(
            name='c',
            label='Discriminant exponent $c$',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e = TextBox(
            name='e',
            label='Ramification index $e$',
            knowl='lf.ramification_index',
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
            label='Galois group $G$',
            short_label='Galois group',
            knowl='nf.galois_group',
            example='5T3',
            example_span='list of %s, e.g. [8,3] or [16,7], group names from the %s, e.g. C5 or S12, and %s, e.g., 7T2 or 11T5' % (
                display_knowl('group.small_group_label', "GAP id's"),
                display_knowl('nf.galois_group.name', 'list of group labels'),
                display_knowl('gg.label', 'transitive group labels')))
        results = CountBox()

        self.browse_array = [[degree], [qp], [c], [e], [topslope], [gal], [results]]
        self.refine_array = [[degree, c, gal], [qp, e, topslope]]
