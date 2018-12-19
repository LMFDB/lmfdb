#-*- coding: utf-8 -*-
# This Blueprint is about Local Number Fields
# Author: John Jones

from lmfdb.db_backend import db
from lmfdb.base import app
from flask import render_template, request, url_for, redirect
from lmfdb.utils import web_latex, coeff_to_poly, pol_to_html, display_multiset
from lmfdb.search_parsing import parse_galgrp, parse_ints, clean_input, parse_rats
from lmfdb.search_wrapper import search_wrap
from sage.all import PolynomialRing, QQ, RR
from lmfdb.local_fields import local_fields_page, logger

from lmfdb.transitive_group import group_display_short, group_display_knowl, group_display_inertia, small_group_data, WebGaloisGroup

LF_credit = 'J. Jones and D. Roberts'

def get_bread(breads=[]):
    bc = [("Local Number Fields", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def display_poly(coeffs):
    return web_latex(coeff_to_poly(coeffs))

def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))

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
        ans += group_display_knowl(f['gal'][0],f['gal'][1])
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
    ans = 'Local number field %s%s<br><br>'% (label, nicename)
    ans += 'Extension of $\Q_{%s}$ defined by %s<br>'%(str(f['p']),web_latex(coeff_to_poly(f['coeffs'])))
    gt = f['gal']
    gn = f['n']
    ans += 'Degree: %s<br>' % str(gt)
    ans += 'Ramification index $e$: %s<br>' % str(f['e'])
    ans += 'Residue field degree $f$: %s<br>' % str(f['f'])
    ans += 'Discriminant ideal:  $(p^{%s})$ <br>' % str(f['c'])
    ans += 'Galois group $G$: %s<br>' % group_display_knowl(gn, gt)
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
    if subdata == []:
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
    if len(request.args) != 0:
        return local_field_search(request.args)
    info = {'count': 20}
    learnmore = [#('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Local field labels', url_for(".labels_page"))]
    return render_template("lf-index.html", title="Local Number Fields", bread=bread, credit=LF_credit, info=info, learnmore=learnmore)


@local_fields_page.route("/<label>")
def by_label(label):
    clean_label = clean_input(label)
    if label != clean_label:
        return redirect(url_for('.by_label',label=clean_label), 301)
    return render_field_webpage({'label': label})

def local_field_jump(info):
    return redirect(url_for(".by_label",label=info['jump_to']), 301)

@search_wrap(template="lf-search.html",
             table=db.lf_fields,
             title='Local Number Field Search Results',
             err_title='Local Field Search Input Error',
             per_page=20,
             shortcuts={'jump_to': local_field_jump},
             bread=lambda:get_bread([("Search Results", ' ')]),
             credit=lambda:LF_credit)
def local_field_search(info,query):
    parse_galgrp(info,query,'gal',qfield=('n','galT'))
    parse_ints(info,query,'p',name='Prime p')
    parse_ints(info,query,'n',name='Degree')
    parse_ints(info,query,'c',name='Discriminant exponent c')
    parse_ints(info,query,'e',name='Ramification index e')
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top slope', process=ratproc)
    info['group_display'] = group_display_short
    info['display_poly'] = format_coeffs
    info['slopedisp'] = show_slope_content

def render_field_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        data = db.lf_fields.lookup(label)
        if data is None:
            bread = get_bread([("Search Error", ' ')])
            info['err'] = "Field " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        title = 'Local Number Field ' + prettyname(data)
        polynomial = coeff_to_poly(data['coeffs'])
        p = data['p']
        Qp = r'\Q_{%d}' % p
        e = data['e']
        f = data['f']
        cc = data['c']
        gt = data['gal']
        gn = data['n']
        the_gal = WebGaloisGroup.from_nt(gn,gt)
        isgal = ' Galois' if the_gal.order() == gn else ' not Galois'
        abelian = ' and abelian' if the_gal.is_abelian() else ''
        galphrase = 'This field is'+isgal+abelian+' over $\Q_{%d}$.'%p
        autstring = r'\Gal' if the_gal.order() == gn else r'\Aut'
        prop2 = [
            ('Label', label),
            ('Base', '\(%s\)' % Qp),
            ('Degree', '\(%s\)' % data['n']),
            ('e', '\(%s\)' % e),
            ('f', '\(%s\)' % f),
            ('c', '\(%s\)' % cc),
            ('Galois group', group_display_short(gn, gt)),
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
        Pxt=PolynomialRing(Px,'t')
        Pt = PolynomialRing(QQ, 't')
        Ptx = PolynomialRing(Pt, 'x')
        if data['f'] == 1:
            unramp = r'$%s$' % Qp
            # Eliminate t from the eisenstein polynomial
            eisenp = Pxt(str(data['eisen']).replace('y','x'))
            eisenp = Pt(str(data['unram'])).resultant(eisenp)
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
            gsm = web_latex(coeff_to_poly(gsm))


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
                    'gal': group_display_knowl(gn, gt),
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
        learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Local field labels', url_for(".labels_page"))]
        return render_template("lf-show-field.html", credit=LF_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends, learnmore=learnmore)


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
        return('$\Q_{%s}$' % p)
    if code == [1, 1]:
        return('$\Q_{%s}(\sqrt{*})$' % p)
    if code == [-1, 1]:
        return('$\Q_{%s}(\sqrt{-*})$' % p)
    s = code[0]
    if code[1] == 1:
        s = str(s) + '*'
    return('$\Q_{' + str(p) + '}(\sqrt{' + str(s) + '})$')


def search_input_error(info, bread):
    return render_template("lf-search.html", info=info, title='Local Field Search Input Error', bread=bread)

@local_fields_page.route("/random")
def random_field():
    label = db.lf_fields.random()
    return redirect(url_for(".by_label", label=label), 307)

@local_fields_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Local Field Data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Local field labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.lf.extent',
                           credit=LF_credit, title=t, bread=bread, 
                           learnmore=learnmore)

@local_fields_page.route("/Labels")
def labels_page():
    t = 'Labels for Local Number Fields'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='lf.field.label',learnmore=learnmore, credit=LF_credit, title=t, bread=bread)

@local_fields_page.route("/Source")
def how_computed_page():
    t = 'Source of the Local Field Data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                #('Source of the data', url_for(".how_computed_page")),
                ('Local field labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.lf.source',
                           credit=LF_credit, title=t, bread=bread, 
                           learnmore=learnmore)

