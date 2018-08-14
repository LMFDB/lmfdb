# -*- coding: utf-8 -*-
# This Blueprint is about Elliptic Curves over Number Fields
# Authors: Harald Schilly and John Cremona

import re
import time
import ast
import StringIO
from operator import mul
from urllib import quote, unquote
from lmfdb.db_backend import db
from lmfdb.db_encoding import Json
from lmfdb.base import app
from flask import render_template, request, url_for, redirect, flash, send_file, make_response
from lmfdb.utils import to_dict
from lmfdb.search_parsing import parse_ints, parse_noop, nf_string_to_label, parse_nf_string, parse_nf_elt, parse_bracketed_posints
from lmfdb.search_wrapper import search_wrap
from lmfdb.ecnf import ecnf_page
from lmfdb.ecnf.ecnf_stats import ecnf_degree_summary, ecnf_signature_summary, sort_field
from lmfdb.ecnf.WebEllipticCurve import ECNF, web_ainvs, convert_IQF_label
from lmfdb.ecnf.isog_class import ECNF_isoclass
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField

from markupsafe import Markup

LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
TORS_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')

def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. It must be of the form (number field label) - (conductor label) - (isogeny class label) - (curve identifier) separated by dashes, such as 2.2.5.1-31.1-a1" % lab), "error")
        raise ValueError
    field_label = data[0]
    conductor_label = data[1]
    try:
        # field 3.1.23.1 uses upper case letters
        isoclass_label = re.search("(CM)?[a-zA-Z]+", data[2]).group()
        curve_number = re.search("\d+", data[2]).group()  # (a string)
    except AttributeError:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. The last part must contain both an isogeny class label (a sequence of letters), followed by a curve id (an integer), such as a1" % lab), "error")
        raise ValueError
    return (field_label, conductor_label, isoclass_label, curve_number)


def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    if len(data) != 2:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. It must be of the form (conductor label) - (isogeny class label) - (curve identifier) separated by dashes, such as 31.1-a1" % lab), "error")
        raise ValueError
    conductor_label = data[0]
    try:
        # field 3.1.23.1 uses upper case letters
        isoclass_label = re.search("[a-zA-Z]+", data[1]).group()
        curve_number = re.search("\d+", data[1]).group()  # (a string)
    except AttributeError:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. The last part must contain both an isogeny class label (a sequence of letters), followed by a curve id (an integer), such as a1" % lab), "error")
        raise ValueError
    return (conductor_label, isoclass_label, curve_number)


def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid isogeny class label. It must be of the form (number field label) - (conductor label) - (isogeny class label) (separated by dashes), such as 2.2.5.1-31.1-a" % lab), "error")
        raise ValueError
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label, conductor_label, isoclass_label)


def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    data = lab.split("-")
    if len(data) != 2:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid isogeny class label. It must be of the form (conductor label) - (isogeny class label) (separated by dashes), such as 31.1-a" % lab), "error")
        raise ValueError
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label, isoclass_label)

def conductor_label_norm(lab):
    r""" extract norm from conductor label (as a string)"""
    s = lab.replace(' ','')
    if re.match(r'\d+.\d+',s):
        return s.split('.')[0]
    else:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid conductor label. It must be of the form N.m or [N,c,d]" % lab), "error")
        raise ValueError

def get_nf_info(lab):
    r""" extract number field label from string and pretty"""
    try:
        label = nf_string_to_label(lab)
        pretty = field_pretty (label)
    except ValueError as err:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid number field. %s" % (lab,err)), "error")
        raise ValueError
    return label, pretty


ecnf_credit = "John Cremona, Alyson Deines, Steve Donelly, Paul Gunnells, Warren Moore, Haluk Sengun, Andrew V Sutherland, John Voight, Dan Yasaki"


def get_bread(*breads):
    bc = [("Elliptic Curves", url_for(".index"))]
    map(bc.append, breads)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Elliptic Curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

@ecnf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Elliptic Curve Data over Number Fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Completeness', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ecnf.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@ecnf_page.route("/Source")
def how_computed_page():
    t = 'Source of the Elliptic Curve Data over Number Fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Source', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ecnf.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ecnf_page.route("/Labels")
def labels_page():
    t = 'Labels for Elliptic Curves over Number Fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Labels', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='ec.curve_label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))


@ecnf_page.route("/")
def index():
    #    if 'jump' in request.args:
    #        return show_ecnf1(request.args['label'])
    if len(request.args) > 0:
        return elliptic_curve_search(request.args)
    bread = get_bread()

    # the dict data will hold additional information to be displayed on
    # the main browse and search page

    data = {}

    # data['fields'] holds data for a sample of number fields of different
    # signatures for a general browse:

    ecnfstats = db.ec_nfcurves.stats
    fields_by_deg = ecnfstats.get_oldstat('fields_by_degree')
    fields_by_sig = ecnfstats.get_oldstat('fields_by_signature')
    data['fields'] = []
    # Rationals
    data['fields'].append(['the rational field', (('1.1.1.1', [url_for('ec.rational_elliptic_curves'), '$\Q$']),)])

    # Real quadratics (sample)
    rqfs = ['2.2.{}.1'.format(d) for d in [5, 89, 229, 497]]
    niqfs = len(fields_by_sig['0,1'])
    nrqfs = len(fields_by_sig['2,0'])
    data['fields'].append(['{} real quadratic fields, including'.format(nrqfs),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in rqfs)])

    # Imaginary quadratics (sample)
    iqfs = ['2.0.{}.1'.format(d) for d in [4, 8, 3, 7, 11]]
    data['fields'].append(['{} imaginary quadratic fields, including'.format(niqfs),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in iqfs)])

    # Cubics (sample)
    cubics = ['3.1.23.1'] + ['3.3.{}.1'.format(d) for d in [49,148,1957]]
    ncubics = len(fields_by_deg['3'])
    data['fields'].append(['{} cubic fields, including'.format(ncubics),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in cubics)])

    # Quartics (sample)
    quartics = ['4.4.{}.1'.format(d) for d in [725,2777,9909,19821]]
    nquartics = len(fields_by_deg['4'])
    data['fields'].append(['{} totally real quartic fields, including'.format(nquartics),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in quartics)])

    # Quintics (sample)
    quintics = ['5.5.{}.1'.format(d) for d in [14641, 24217, 36497, 38569, 65657]]
    nquintics = len(fields_by_deg['5'])
    data['fields'].append(['{} totally real quintic fields, including'.format(nquintics),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in quintics)])

    # Sextics (sample)
    sextics = ['6.6.{}.1'.format(d) for d in [300125, 371293, 434581, 453789, 485125]]
    nsextics = len(fields_by_deg['6'])
    data['fields'].append(['{} totally real sextic fields, including'.format(nsextics),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in sextics)])

    data['degrees'] = sorted([int(d) for d in fields_by_deg.keys() if d!='_id'])

# data['highlights'] holds data (URL and descriptive text) for a
# sample of elliptic curves with interesting features:

    data['highlights'] = []
    data['highlights'].append(
        ['A curve with $C_3\\times C_3$ torsion',
         url_for('.show_ecnf', nf='2.0.3.1', class_label='a', conductor_label='2268.36.18', number=int(1))]
    )
    data['highlights'].append(
        ['A curve with $C_4\\times C_4$ torsion',
         url_for('.show_ecnf', nf='2.0.4.1', class_label='b', conductor_label='5525.870.5', number=int(9))]
    )
    data['highlights'].append(
        ['A curve with CM by $\\sqrt{-267}$',
         url_for('.show_ecnf', nf='2.2.89.1', class_label='a', conductor_label='81.1', number=int(1))]
    )
    data['highlights'].append(
        ['An isogeny class with isogenies of degree $3$ and $89$ (and $267$)',
         url_for('.show_ecnf_isoclass', nf='2.2.89.1', class_label='a', conductor_label='81.1')]
    )
    data['highlights'].append(
        ['A curve with everywhere good reduction, but no global minimal model',
         url_for('.show_ecnf', nf='2.2.229.1', class_label='a', conductor_label='1.1', number=int(1))]
    )

    return render_template("ecnf-index.html",
                           title="Elliptic Curves over Number Fields",
                           data=data,
                           bread=bread, learnmore=learnmore_list_remove('Completeness'))

@ecnf_page.route("/random")
def random_curve():
    E = db.ec_nfcurves.random(projection=['field_label', 'conductor_label', 'iso_label', 'number'])
    return redirect(url_for(".show_ecnf", nf=E['field_label'], conductor_label=E['conductor_label'], class_label=E['iso_label'], number=E['number']), 307)

@ecnf_page.route("/<nf>/")
def show_ecnf1(nf):
    try:
        nf_label, nf_pretty = get_nf_info(nf)
    except ValueError:
        return search_input_error()
    if nf_label == '1.1.1.1':
        return redirect(url_for("ec.rational_elliptic_curves", **request.args), 301)
    info = to_dict(request.args)
    info['title'] = 'Elliptic Curves over %s' % nf_pretty
    info['bread'] = [('Elliptic Curves', url_for(".index")), (nf_pretty, url_for(".show_ecnf1", nf=nf))]
    if len(request.args) > 0:
        # if requested field differs from nf, redirect to general search
        if 'field' in request.args and request.args['field'] != nf_label:
            return redirect (url_for(".index", **request.args), 307)
        info['title'] += ' Search Results'
        info['bread'].append(('Search Results',''))
    info['field'] = nf_label
    return elliptic_curve_search(info)

@ecnf_page.route("/<nf>/<conductor_label>/")
def show_ecnf_conductor(nf, conductor_label):
    conductor_label = unquote(conductor_label)
    conductor_label = convert_IQF_label(nf,conductor_label)
    try:
        nf_label, nf_pretty = get_nf_info(nf)
        conductor_norm = conductor_label_norm(conductor_label)
    except ValueError:
        return search_input_error()
    info = to_dict(request.args)
    info['title'] = 'Elliptic Curves over %s of Conductor %s' % (nf_pretty, conductor_label)
    info['bread'] = [('Elliptic Curves', url_for(".index")), (nf_pretty, url_for(".show_ecnf1", nf=nf)), (conductor_label, url_for(".show_ecnf_conductor",nf=nf,conductor_label=conductor_label))]
    if len(request.args) > 0:
        # if requested field or conductor norm differs from nf or conductor_lable, redirect to general search
        if ('field' in request.args and request.args['field'] != nf_label) or \
           ('conductor_norm' in request.args and request.args['conductor_norm'] != conductor_norm):
            return redirect (url_for(".index", **request.args), 307)
        info['title'] += ' Search Results'
        info['bread'].append(('Search Results',''))
    info['field'] = nf_label
    info['conductor_label'] = conductor_label
    info['conductor_norm'] = conductor_norm
    return elliptic_curve_search(info)

@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/")
def show_ecnf_isoclass(nf, conductor_label, class_label):
    conductor_label = unquote(conductor_label)
    conductor_label = convert_IQF_label(nf,conductor_label)
    try:
        nf_label, nf_pretty = get_nf_info(nf)
    except ValueError:
        return search_input_error()
    label = "-".join([nf_label, conductor_label, class_label])
    full_class_label = "-".join([conductor_label, class_label])
    cl = ECNF_isoclass.by_label(label)
    bread = [("Elliptic Curves", url_for(".index"))]
    if not isinstance(cl, ECNF_isoclass):
        info = {'query':{}, 'err':'No elliptic curve isogeny class in the database has label %s.' % label}
        return search_input_error(info, bread)
    title = "Elliptic Curve Isogeny Class %s over Number Field %s" % (full_class_label, cl.field_name)
    bread.append((nf_pretty, url_for(".show_ecnf1", nf=nf)))
    bread.append((conductor_label, url_for(".show_ecnf_conductor", nf=nf_label, conductor_label=conductor_label)))
    bread.append((class_label, url_for(".show_ecnf_isoclass", nf=nf_label, conductor_label=quote(conductor_label), class_label=class_label)))
    return render_template("ecnf-isoclass.html",
                           credit=ecnf_credit,
                           title=title,
                           bread=bread,
                           cl=cl,
                           properties2=cl.properties,
                           friends=cl.friends,
                           learnmore=learnmore_list())


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/<number>")
def show_ecnf(nf, conductor_label, class_label, number):
    conductor_label = unquote(conductor_label)
    conductor_label = convert_IQF_label(nf,conductor_label)
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])
    ec = ECNF.by_label(label)
    bread = [("Elliptic Curves", url_for(".index"))]
    if not ec:
        info = {'query':{}}
        info['err'] = 'No elliptic curve in the database has label %s.' % label
        return search_input_error(info, bread)

    title = "Elliptic Curve %s over Number Field %s" % (ec.short_label, ec.field.field_pretty())
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((ec.field.field_pretty(), ec.urls['field']))
    bread.append((ec.conductor_label, ec.urls['conductor']))
    bread.append((ec.iso_label, ec.urls['class']))
    bread.append((ec.number, ec.urls['curve']))
    code = ec.code()
    code['show'] = {'magma':'','pari':'','sage':''} # use default show names
    info = {}
    return render_template("ecnf-curve.html",
                           credit=ecnf_credit,
                           title=title,
                           bread=bread,
                           ec=ec,
                           code = code,
                           #        properties = ec.properties,
                           properties2=ec.properties,
                           friends=ec.friends,
                           downloads=ec.downloads,
                           info=info,
                           learnmore=learnmore_list())

def download_search(info):
    dltype = info['submit']
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'elliptic_curves.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'elliptic_curves.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'elliptic_curves.m'
    s = com1 + "\n"
    s += com + ' Elliptic curves downloaded from the LMFDB downloaded on %s.\n'%(mydate)
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [[field_poly],[Weierstrass Coefficients, constant first in increasing degree]]\n'
    s += '\n' + com2
    s += '\n'

    if dltype == 'magma':
        s += 'P<x> := PolynomialRing(Rationals()); \n'
        s += 'data := ['
    elif dltype == 'sage':
        s += 'R.<x> = QQ[]; \n'
        s += 'data = [ '
    else:
        s += 'data = [ '
    s += '\\\n'
    nf_dict = {}
    for f in db.ec_nfcurves.search(ast.literal_eval(info["query"]), ['field_label', 'ainvs']):
        nf = str(f['field_label'])
        # look up number field and see if we already have the min poly
        if nf in nf_dict:
            poly = nf_dict[nf]
        else:
            poly = str(WebNumberField(f['field_label']).poly())
            nf_dict[nf] = poly
        entry = str(f['ainvs'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        entry = entry.replace(';','],[')
        s += '[[' + poly + '], [[' + entry + ']]],\\\n'
    s = s[:-3]
    s += ']\n'

    if delim == 'brace':
        s = s.replace('[', '{')
        s = s.replace(']', '}')
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)

def elliptic_curve_jump(info):
    label = info.get('label', '').replace(" ", "")
    # This label should be a full isogeny class label or a full
    # curve label (including the field_label component)
    try:
        nf, cond_label, iso_label, number = split_full_label(label.strip())
    except ValueError:
        info['err'] = ''
        bread = [('Elliptic Curves', url_for(".index")), ('Search Results', '.')]
        return search_input_error(info, bread)

    return redirect(url_for(".show_ecnf", nf=nf, conductor_label=cond_label, class_label=iso_label, number=number), 301)

@search_wrap(template="ecnf-search-results.html",
             table=db.ec_nfcurves,
             title='Elliptic Curve Search Results',
             err_title='Elliptic Curve Search Input Error',
             shortcuts={'jump':elliptic_curve_jump,
                        'download':download_search},
             cleaners={'numb':lambda e: str(e['number']),
                       'field_knowl':lambda e: nf_display_knowl(e['field_label'], field_pretty(e['field_label']))},
             bread=lambda:[('Elliptic Curves', url_for(".index")), ('Search Results', '.')],
             credit=lambda:ecnf_credit)
def elliptic_curve_search(info, query):
    parse_nf_string(info,query,'field',name="base number field",qfield='field_label')
    if query.get('field_label') == '1.1.1.1':
        return redirect(url_for("ec.rational_elliptic_curves", **request.args), 301)

    parse_ints(info,query,'conductor_norm')
    parse_noop(info,query,'conductor_label')
    parse_ints(info,query,'torsion',name='Torsion order',qfield='torsion_order')
    parse_bracketed_posints(info,query,'torsion_structure',maxlength=2)
    if 'torsion_structure' in query and not 'torsion_order' in query:
        query['torsion_order'] = reduce(mul,[int(n) for n in query['torsion_structure']],1)
    parse_ints(info,query,field='isodeg',qfield='isogeny_degrees')

    if 'jinv' in info:
        if info.get('field','').strip() == '2.2.5.1':
            info['jinv'] = info['jinv'].replace('phi','a')
        if info.get('field','').strip() == '2.0.4.1':
            info['jinv'] = info['jinv'].replace('i','a')
    parse_nf_elt(info,query,'jinv',name='j-invariant')
    if query.get('jinv'):
        query['jinv'] =','.join(query['jinv'])

    if 'include_isogenous' in info and info['include_isogenous'] == 'off':
        info['number'] = 1
        query['number'] = 1

    if 'include_base_change' in info and info['include_base_change'] == 'off':
        query['base_change'] = []
    else:
        info['include_base_change'] = "on"

    if 'include_Q_curves' in info:
        if info['include_Q_curves'] == 'exclude':
            query['q_curve'] = False
        elif info['include_Q_curves'] == 'only':
            query['q_curve'] = True

    if 'include_cm' in info:
        if info['include_cm'] == 'exclude':
            query['cm'] = 0
        elif info['include_cm'] == 'only':
            query['cm'] = {'$ne' : 0}

    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs

def search_input_error(info=None, bread=None):
    if info is None: info = {'err':'','query':{}}
    if bread is None: bread = [('Elliptic Curves', url_for(".index")), ('Search Results', '.')]
    return render_template("ecnf-search-results.html", info=info, title='Elliptic Curve Search Input Error', bread=bread)


@ecnf_page.route("/browse/")
def browse():
    data = db.ec_nfcurves.stats.get_oldstat('signatures_by_degree')
    # We could use the dict directly but then could not control the order
    # of the keys (degrees), so we use a list
    info = [[d,data[str(d)]] for d in sorted([int(d) for d in data.keys()])]
    credit = 'John Cremona'
    t = 'Elliptic Curves over Number Fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Browse', ' ')]
    return render_template("ecnf-stats.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/browse/<int:d>/")
def statistics_by_degree(d):
    if d==1:
        return redirect(url_for("ec.statistics"))
    info = {}

    ecnfstats = db.ec_nfcurves.stats
    sigs_by_deg = ecnfstats.get_oldstat('signatures_by_degree')
    if not str(d) in sigs_by_deg:
        info['error'] = "The database does not contain any elliptic curves defined over fields of degree %s" % d
    else:
        info['degree'] = d

    fields_by_sig = ecnfstats.get_oldstat('fields_by_signature')
    counts_by_sig = ecnfstats.get_oldstat('conductor_norm_by_signature')
    counts_by_field = ecnfstats.get_oldstat('conductor_norm_by_field')

    def field_counts(f):
        ff = f.replace(".",":")
        return [f,counts_by_field[ff]]

    def sig_counts(sig):
        sorted_fields = sorted(fields_by_sig[sig], key=sort_field)
        return [sig, counts_by_sig[sig], [field_counts(f) for f in sorted_fields]]

    info['summary'] = ecnf_degree_summary(d)
    info['sig_stats'] = [sig_counts(sig) for sig in sigs_by_deg[str(d)]]
    credit = 'John Cremona'
    if d==2:
        t = 'Elliptic Curves over Quadratic Number Fields'
    elif d==3:
        t = 'Elliptic Curves over Cubic Number Fields'
    elif d==4:
        t = 'Elliptic Curves over Quartic Number Fields'
    elif d==5:
        t = 'Elliptic Curves over Quintic Number Fields'
    elif d==6:
        t = 'Elliptic Curves over Sextic Number Fields'
    else:
        t = 'Elliptic Curves over Number Fields of Degree {}'.format(d)

    bread = [('Elliptic Curves', url_for("ecnf.index")),
              ('Degree %s' % d,' ')]
    return render_template("ecnf-by-degree.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/browse/<int:d>/<int:r>/")
def statistics_by_signature(d,r):
    if d==1:
        return redirect(url_for("ec.statistics"))

    info = {}

    ecnfstats = db.ec_nfcurves.stats
    sigs_by_deg = ecnfstats.get_oldstat('signatures_by_degree')
    if not str(d) in sigs_by_deg:
        info['error'] = "The database does not contain any elliptic curves defined over fields of degree %s" % d
    else:
        info['degree'] = d

    if not r in range(d%2,d+1,2):
        info['error'] = "Invalid signature %s" % info['sig']
    s = (d-r)//2
    info['sig'] = sig = '%s,%s' % (r,s)
    info['summary'] = ecnf_signature_summary(sig)

    fields_by_sig = ecnfstats.get_oldstat('fields_by_signature')
    counts_by_field = ecnfstats.get_oldstat('conductor_norm_by_field')

    def field_counts(f):
        ff = f.replace(".",":")
        return [f,counts_by_field[ff]]

    sorted_fields = sorted(fields_by_sig[sig], key=sort_field)
    info['sig_stats'] = [field_counts(f) for f in sorted_fields]
    credit = 'John Cremona'
    if info['sig'] == '2,0':
        t = 'Elliptic Curves over Real Quadratic Number Fields'
    elif info['sig'] == '0,1':
        t = 'Elliptic Curves over Imaginary Quadratic Number Fields'
    elif info['sig'] == '3,0':
        t = 'Elliptic Curves over Totally Real Cubic Number fields'
    elif info['sig'] == '1,1':
        t = 'Elliptic Curves over Mixed Cubic Number Fields'
    elif info['sig'] == '4,0':
        t = 'Elliptic Curves over Totally Real Quartic Number Fields'
    elif info['sig'] == '5,0':
        t = 'Elliptic Curves over Totally Real Quintic Number Fields'
    elif info['sig'] == '6,0':
        t = 'Elliptic Curves over Totally Real Sextic Number Fields'
    else:
        t = 'Elliptic Curves over Number Fields of Degree %s, Signature (%s)' % (d,info['sig'])
    bread = [('Elliptic Curves', url_for("ecnf.index")),
              ('Degree %s' % d,url_for("ecnf.statistics_by_degree", d=d)),
              ('Signature (%s)' % info['sig'],' ')]
    return render_template("ecnf-by-signature.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())

def get_torsion_structures():
    ecnfstats = db.ec_nfcurves.stats
    torsion_structures = [t[0] for t in ecnfstats.get_oldstat('torsion_structure')['counts']]
    torsion_structures = [[int(str(n)) for n in t.split(",")] for t in torsion_structures if t]
    torsion_structures.sort()
    return torsion_structures

def tor_struct_search_nf(prefill="any"):
    def fix(t):
        return t + ' selected = "yes"' if prefill==t else t
    def cyc(n):
        return [fix("["+str(n)+"]"), "$C_{{{}}}$".format(n)]
    def cyc2(m,n):
        return [fix("[{},{}]".format(m,n)), "$C_{{{}}}\\times C_{{{}}}$".format(m,n)]
    gps = [[fix(""), "any"], [fix("[]"), "trivial"]]

    tors = get_torsion_structures()

    # The following was the set as of 24/4/2017:
    # assert tors == [[2], [2, 2], [2, 4], [2, 6], [2, 8], [2, 10], [2, 12], [2, 14], [2, 16], [2, 18], [3], [3, 3], [3, 6], [4], [4, 4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14], [15], [16], [17], [18], [19], [20], [21], [22], [25], [27], [37]]

    for t in tors:
        if len(t)==1:
            gps.append(cyc(t[0]))
        elif len(t)==2:
            gps.append(cyc2(*t))

    return "\n".join(["<select name='torsion_structure'>"] + ["<option value={}>{}</option>".format(a,b) for a,b in gps] + ["</select>"])

# the following allows the preceding function to be used in any template via {{...}}
app.jinja_env.globals.update(tor_struct_search_nf=tor_struct_search_nf)

@ecnf_page.route("/download_all/<nf>/<conductor_label>/<class_label>/<number>")
def download_ECNF_all(nf,conductor_label,class_label,number):
    conductor_label = unquote(conductor_label)
    conductor_label = convert_IQF_label(nf,conductor_label)
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])
    data = db.ec_nfcurves.lookup(label)
    if data is None:
        return search_input_error()

    response = make_response(Json.dumps(data))
    response.headers['Content-type'] = 'text/plain'
    return response

@ecnf_page.route('/<nf>/<conductor_label>/<class_label>/<number>/download/<download_type>')
def ecnf_code_download(**args):
    response = make_response(ecnf_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response

sorted_code_names = ['field', 'curve', 'is_min', 'cond', 'cond_norm',
                     'disc', 'disc_norm', 'jinv', 'cm', 'rank', 'ntors',
                     'gens', 'reg', 'tors', 'torgens', 'localdata']

code_names = {'field': 'Define the base number field',
              'curve': 'Define the curve',
              'is_min': 'Test whether it is a global minimal model',
              'cond': 'Compute the conductor',
              'cond_norm': 'Compute the norm of the conductor',
              'disc': 'Compute the discriminant',
              'disc_norm': 'Compute the norm of the discriminant',
              'jinv': 'Compute the j-invariant',
              'cm': 'Test for Complex Multiplication',
              'rank': 'Compute the Mordell-Weil rank',
              'ntors': 'Compute the order of the torsion subgroup',
              'gens': 'Compute the generators (of infinite order)',
              'reg': 'Compute the regulator',
              'tors': 'Compute the torsion subgroup',
              'torgens': 'Compute the generators of the torsion subgroup',
              'localdata': 'Compute the local reduction data at primes of bad reduction'
}

Fullname = {'magma': 'Magma', 'sage': 'SageMath', 'gp': 'Pari/GP'}
Comment = {'magma': '//', 'sage': '#', 'gp': '\\\\', 'pari': '\\\\'}

def ecnf_code(**args):
    label = "".join(["-".join([args['nf'], args['conductor_label'], args['class_label']]), args['number']])
    E = ECNF.by_label(label)
    Ecode = E.code()
    lang = args['download_type']
    code = "{} {} code for working with elliptic curve {}\n\n".format(Comment[lang],Fullname[lang],label)
    code += "{} (Note that not all these functions may be available, and some may take a long time to execute.)\n".format(Comment[lang])
    if lang=='gp':
        lang = 'pari'
    for k in sorted_code_names:
        if lang in Ecode[k]:
            code += "\n{} {}: \n".format(Comment[lang],code_names[k])
            code += Ecode[k][lang] + ('\n' if not '\n' in Ecode[k][lang] else '')
    return code

