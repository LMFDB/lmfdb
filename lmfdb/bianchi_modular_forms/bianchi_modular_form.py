# -*- coding: utf-8 -*-

import re

from pymongo import ASCENDING
from flask import render_template, url_for, request, redirect, flash
from markupsafe import Markup

from sage.all import ZZ, latex

from lmfdb.utils import to_dict, random_object_from_collection
from lmfdb.search_parsing import parse_range, parse_range2, parse_nf_string
from lmfdb.hilbert_modular_forms.hilbert_modular_form import teXify_pol
from lmfdb.bianchi_modular_forms import bmf_page
from lmfdb.bianchi_modular_forms.web_BMF import WebBMF, db_dims, db_forms
from lmfdb.WebNumberField import field_pretty, WebNumberField


bianchi_credit = 'John Cremona, Aurel Page, Alexander Rahm, Haluk Sengun'

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')

# parse field label, which can either be a coded label such as
# '2.0.8.1' or a nickname such as 'Qi' or 'Qsqrt-1'
def parse_field_label(lab):
    if "-" in lab:
        return False
    if field_label_regex.match(lab):
        lab_parts = lab.split('.')
        if len(lab_parts)!=4:
            return False
        if int(lab_parts[2])%4 in [0,3]:
            return lab
        else:
            return False
    return False

@bmf_page.route("/")
def bianchi_modular_form_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = bianchi_credit
        t = 'Bianchi modular forms'
        bread = [('Bianchi modular forms', url_for(".bianchi_modular_form_render_webpage"))]
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return bianchi_modular_form_search(**args)

@bmf_page.route("/random")
def random_bmf():    # Random Hilbert modular form
    return bianchi_modular_form_by_label( random_object_from_collection( db_forms() ) )

def bianchi_modular_form_search(**args):

    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        args = {'label': info['label']}
        return render_bmf_webpage(**args)
    query = {}
    for field in ['field_label', 'weight', 'level_norm', 'dimension']:
        print("parsing field {} in {}".format(field, info))
        if info.get(field):
            if field == 'weight':
                query['weight'] = '2'
            elif field == 'field_label':
                print("parsing {}".format(info[field]))
                parse_nf_string(info,query,field,'base number field',field)
            elif field == 'label':
                query[field] = info[field]
            elif field == 'dimension':
                query['dimension'] = '1'
            elif field == 'level_norm':
                query[field] = parse_range(info[field])
            else:
                query[field] = info[field]

    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = 100
    else:
        info['count'] = 100
        count = 100

    info['query'] = dict(query)
    res = db_forms().find(
        query).sort([('level_norm', ASCENDING), ('label', ASCENDING)]).limit(count)
    nres = res.count()

    if nres > 0:
        info['field_pretty_name'] = field_pretty(res[0]['field_label'])
    else:
        info['field_pretty_name'] = ''
    info['number'] = nres
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count:
            info['report'] = 'displaying first %s of %s matches' % (count, nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    res_clean = []
    for v in res:
        v_clean = {}
        v_clean['field_label'] = v['field_label']
        v_clean['short_label'] = v['short_label']
        v_clean['label'] = v['label']
        v_clean['level_ideal'] = teXify_pol(v['level_ideal'])
        v_clean['dimension'] = v['dimension']
        res_clean.append(v_clean)

    info['forms'] = res_clean

    t = 'Bianchi modular form search results'

    bread = [('Bianchi Modular Forms', url_for(".bianchi_modular_form_render_webpage")), (
        'Search results', ' ')]
    properties = []
    return render_template("bmf-search_results.html", info=info, title=t, properties=properties, bread=bread)

@bmf_page.route('/<field_label>')
def render_bmf_field_dim_table(**args):
    argsdict = to_dict(args)
    field_label=argsdict['field_label']

    if parse_field_label(field_label):
        print("Matched field label {}".format(field_label))
    else:
        print("label {} not a field".format(field_label))
        return render_bmf_webpage(field_label)
    start = 0
    if 'start' in request.args:
        start = int(request.args['start'])
    count = 30
    if 'count' in request.args:
        count = int(request.args['count'])
    info={}

    # parse field label, which can either be a coded label such as
    # '2.0.8.1' or a nickname such as 'Qi' or 'Qsqrt-1'
    print("field label = {}".format(field_label))
    pretty_field_label = field_pretty(field_label)
    bread = [('Bianchi Modular Forms', url_for(".bianchi_modular_form_render_webpage")), (
        pretty_field_label, ' ')]
    properties = []
    t = ' '.join(['Dimensions of spaces of Bianchi modular forms over', pretty_field_label])
    query = {}
    query['field_label'] = field_label
    if argsdict.get('level_norm'):
        ran = argsdict['level_norm']
        ran = ran.replace('..', '-').replace(' ', '')
        if not LIST_RE.match(ran):
            info['err'] = 'Error parsing input for the level norm.  It needs to be blank or an integer (such as 5), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 2,3,8 or 3-5, 7, 8-11).'
        # Past input check
        tmp = parse_range2(ran, 'level_norm')
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
    data = db_dims().find(query)
    data = data.sort([('level_norm', ASCENDING)])
    info['number'] = nrec = data.count()
    print "found %s records in Bianchi dimension table for field %s" % (nrec,field_label)
    data = list(data.skip(start).limit(count))
    info['field'] = field_label
    info['field_pretty'] = pretty_field_label
    nf = WebNumberField(field_label)
    info['base_galois_group'] = nf.galois_string()
    info['field_degree'] = nf.degree()
    info['field_disc'] = str(nf.disc())
    info['field_poly'] = teXify_pol(str(nf.poly()))
    weights = set()
    for dat in data:
        weights = weights.union(set(dat['gl2_dims'].keys()))
    weights = list([int(w) for w in weights])
    weights.sort()
    info['weights'] = weights
    info['nweights'] = len(weights)
    info['count'] = count
    info['start'] = start
    info['complete'] = int(info['number'] < info['count'])
    info['next_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(start+count), count=str(count), level_norm=argsdict.get('level_norm',''))
    info['prev_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(max(0,start-count)), count=str(count))

    dims = {}
    for dat in data:
        dims[dat['level_label']] = d = {}
        for w in weights:
            sw = str(w)
            if sw in dat['gl2_dims']:
                d[w] = {'d': dat['gl2_dims'][sw]['cuspidal_dim'],
                        'n': dat['gl2_dims'][sw]['new_dim']}
            else:
                d[w] = {'d': '?', 'n': '?'}

    dimtable = [{'level_label': dat['level_label'],
                 'level_norm': dat['level_norm'],
                 'level_space': url_for(".render_bmf_space_webpage", field_label=field_label, level_label=dat['level_label']),
                  'dims': dims[dat['level_label']]} for dat in data]
    print "dimtable = ", dimtable
    info['dimtable'] = dimtable
    return render_template("bmf-field_dim_table.html", info=info, title=t, properties=properties, bread=bread)


@bmf_page.route('/<field_label>/<level_label>')
def render_bmf_space_webpage(field_label, level_label):
    info = {}
    t = "Bianchi modular forms of level %s over %s" % (level_label, field_label)
    credit = bianchi_credit
    bread = [('Bianchi modular forms', url_for(".bianchi_modular_form_render_webpage")),
             (field_pretty(field_label), url_for(".render_bmf_field_dim_table", field_label=field_label)),
             (level_label, url_for(".render_bmf_space_webpage", field_label=field_label, level_label=level_label))]

    if not field_label_regex.match(field_label):
        info['err'] = "%s is not a valid label for an imaginary quadratic field" % field_label
    else:
        pretty_field_label = field_pretty(field_label)
        if not db_dims().find({'field_label': field_label}):
            info['err'] = "no information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi Modular Forms of level %s over %s" % (level_label, pretty_field_label)
            data = db_dims().find({'field_label': field_label, 'level_label': level_label})
            n = data.count()
            if n==0:
                info['err'] = "no information exists in the database for level %s and field %s" % (level_label, pretty_field_label)
            else:
                data = data.next()
                info['label'] = data['label']
                nf = WebNumberField(field_label)
                info['base_galois_group'] = nf.galois_string()
                info['field_label'] = field_label
                info['pretty_field_label'] = pretty_field_label
                info['level_label'] = level_label
                info['level_norm'] = data['level_norm']
                info['field_degree'] = nf.degree()
                info['field_classno'] = nf.class_number()
                info['field_disc'] = str(nf.disc())
                info['field_poly'] = teXify_pol(str(nf.poly()))
                w = 'i' if nf.disc()==-4 else 'a'
                L = nf.K().change_names(w)
                alpha = L.gen()
                info['field_gen'] = latex(alpha)
                N,c,d = [ZZ(x) for x in level_label.split('.')]
                I = L.ideal(N//d,c+d*alpha)
                info['level_gen'] = latex(I.gens_reduced()[0])
                info['level_fact'] = latex(I.factor())
                dim_data = data['gl2_dims']
                weights = dim_data.keys()
                weights.sort(key=lambda w: int(w))
                for w in weights:
                    dim_data[w]['dim']=dim_data[w]['cuspidal_dim']
                info['dim_data'] = dim_data
                info['weights'] = weights
                info['nweights'] = len(weights)
                # info['cuspidal_dim'] = dim_data['cuspidal_dim']
                # info['new_dim'] = dim_data['new_dim']
                # info['dimension'] = info['cuspidal_dim']

    return render_template("bmf-space.html", info=info, credit=credit, title=t, bread=bread)

@bmf_page.route('/<label>/')
def render_bmf_webpage(label):
    credit = "John Cremona"
    bread = []
    info = {}
    title = "Bianchi cusp forms"
    data = None
    properties2 = []
    friends = []
    bread = [('Bianchi modular forms', url_for(".bianchi_modular_form_render_webpage"))]
    try:
        data = WebBMF.by_label(label)
        title = "Bianchi cusp form {} over {}".format(data.short_label,field_pretty(data.field_label))
        bread = [('Bianchi modular forms', url_for(".bianchi_modular_form_render_webpage")),
                 (field_pretty(data.field_label), url_for(".render_bmf_field_dim_table", field_label=data.field_label)),
                 (data.short_label, url_for(".render_bmf_webpage", label=label))]
        properties2 = data.properties2
        friends = data.friends
    except ValueError:
        info['err'] = "No Bianchi modular form in the database has label {}".format(label)
    return render_template("bmf-newform.html", title=title, credit=credit, bread=bread, data=data, properties2=properties2, friends=friends, info=info)

def bianchi_modular_form_by_label(lab):
    if isinstance(lab, basestring):
        res = db_forms().find_one({'label': lab},{'label':True})
    else:
        res = lab
        lab = res['label']
    if res == None:
        flash(Markup("No Bianchi modular form in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
        return redirect(url_for(".bianchi_modular_form_render_webpage"))
    else:
        return redirect(url_for(".render_bmf_webpage", label=lab))

