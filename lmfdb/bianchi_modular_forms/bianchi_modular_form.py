# -*- coding: utf-8 -*-

import re

from pymongo import ASCENDING
from flask import render_template, url_for, request, redirect, flash
from markupsafe import Markup

from sage.all import latex

from lmfdb.base import getDBConnection
from lmfdb.utils import to_dict, random_object_from_collection
from lmfdb.search_parsing import parse_range, nf_string_to_label, parse_nf_string
from lmfdb.hilbert_modular_forms.hilbert_modular_form import teXify_pol
from lmfdb.bianchi_modular_forms import bmf_page
from lmfdb.bianchi_modular_forms.web_BMF import WebBMF, db_dims, db_forms
from lmfdb.WebNumberField import field_pretty, WebNumberField, nf_display_knowl
from lmfdb.nfutils.psort import ideal_from_label


bianchi_credit = 'John Cremona, Aurel Page, Alexander Rahm, Haluk Sengun'

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')

@bmf_page.route("/")
def index():
    """Function to deal with the base URL
    /ModularForm/GL2/ImaginaryQuadratic.  If there are no request.args
    we display the browse and serch page, otherwise (as happens when
    submitting a jump or search button from that page) we hand over to
    the function bianchi_modular_form_search().
    """
    args = request.args
    if len(args) == 0:
        info = {}
        fields = ["2.0.{}.1".format(d) for d in [4,8,3,7,11]]
        names = ["\(\Q(\sqrt{-%s})\)" % d for d in [1,2,3,7,11]]
        info['field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table", field_label=f), 'name':n} for f,n in zip(fields,names)]
        info['field_forms'] = [{'url':url_for("bmf.index", field_label=f), 'name':n} for f,n in zip(fields,names)]
        credit = bianchi_credit
        t = 'Bianchi modular forms'
        bread = [('Bianchi modular forms', url_for(".index"))]
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return bianchi_modular_form_search(**args)

@bmf_page.route("/random")
def random_bmf():    # Random Hilbert modular form
    return bianchi_modular_form_by_label( random_object_from_collection( db_forms() ) )

def bianchi_modular_form_search(**args):
    """Function to handle requests from the top page, either jump to one
    newform or do a search.
    """
    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        # The Label button has been pressed.
        return bianchi_modular_form_by_label(info['label'])

    query = {}
    for field in ['field_label', 'weight', 'level_norm', 'dimension']:
        if info.get(field):
            if field == 'weight':
                query['weight'] = info[field]
            elif field == 'field_label':
                parse_nf_string(info,query,field,'base number field',field)
            elif field == 'label':
                query[field] = info[field]
            elif field == 'dimension':
                query['dimension'] = int(info[field])
            elif field == 'level_norm':
                query[field] = parse_range(info[field])
            else:
                query[field] = info[field]

    start = 0
    if 'start' in request.args:
        start = int(request.args['start'])
    count = 50
    if 'count' in request.args:
        count = int(request.args['count'])

    info['query'] = dict(query)
    res = db_forms().find(query).sort([('level_norm', ASCENDING), ('label', ASCENDING)]).skip(start).limit(count)
    nres = res.count()

    if nres > 0:
        info['field_pretty_name'] = field_pretty(res[0]['field_label'])
    else:
        info['field_pretty_name'] = ''
    info['number'] = nres

    if nres == 1:
        info['report'] = 'unique match'
    elif nres == 2:
        info['report'] = 'displaying both matches'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying items %s-%s of %s matches' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    res_clean = []
    for v in res:
        v_clean = {}
        v_clean['field_label'] = v['field_label']
        v_clean['short_label'] = v['short_label']
        v_clean['level_label'] = v['level_label']
        v_clean['label_suffix'] = v['label_suffix']
        v_clean['label'] = v['label']
        v_clean['level_ideal'] = teXify_pol(v['level_ideal'])
        v_clean['dimension'] = v['dimension']
        v_clean['url'] = url_for('.render_bmf_webpage',field_label=v['field_label'], level_label=v['level_label'], label_suffix=v['label_suffix'])
        res_clean.append(v_clean)

    info['forms'] = res_clean
    info['count'] = count
    info['start'] = start
    info['more'] = int(start + count < nres)

    t = 'Bianchi modular form search results'

    bread = [('Bianchi Modular Forms', url_for(".index")), (
        'Search results', ' ')]
    properties = []
    return render_template("bmf-search_results.html", info=info, title=t, properties=properties, bread=bread)

@bmf_page.route('/<field_label>')
def bmf_search_field(field_label):
    return bianchi_modular_form_search(field_label=field_label)

@bmf_page.route('/gl2dims/<field_label>')
def render_bmf_field_dim_table(**args):
    argsdict = to_dict(args)
    argsdict.update(to_dict(request.args))

    field_label=argsdict['field_label']
    field_label = nf_string_to_label(field_label)

    start = 0
    if 'start' in argsdict:
        start = int(argsdict['start'])
    count = 50
    if 'count' in argsdict:
        count = int(argsdict['count'])

    info={}
    nontrivial_only = argsdict.get('nontrivial_only', 'true') == 'true'
    info['nontrivial_only'] = nontrivial_only
    pretty_field_label = field_pretty(field_label)
    bread = [('Bianchi Modular Forms', url_for(".index")), (
        pretty_field_label, ' ')]
    properties = []
    t = ' '.join(['Dimensions of spaces of Bianchi modular forms over', pretty_field_label])
    query = {}
    query['field_label'] = field_label
    query['gl2_dims'] = {'$exists': True}
    data = db_dims().find(query)
    data = data.sort([('level_norm', ASCENDING)])
    info['number'] = data.count()
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
    info['next_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(start+count), count=str(count), level_norm=argsdict.get('level_norm',''), nontrivial_only=argsdict.get('nontrivial_only','true'))
    info['prev_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(max(0,start-count)), count=str(count), nontrivial_only=argsdict.get('nontrivial_only','true'))

    dims = {}
    nlevels = 0
    for dat in data:
        dims[dat['level_label']] = d = {}
        d['total_new'] = 0
        for w in weights:
            sw = str(w)
            if sw in dat['gl2_dims']:
                d[w] = {'d': dat['gl2_dims'][sw]['cuspidal_dim'],
                        'n': dat['gl2_dims'][sw]['new_dim']}
                d['total_new'] += d[w]['n']
            else:
                d[w] = {'d': '?', 'n': '?'}
        if d['total_new'] > 0:
            nlevels += 1
    info['nlevels'] = nlevels if nontrivial_only else len(data)
    dimtable = [{'level_label': dat['level_label'],
                 'level_norm': dat['level_norm'],
                 'level_space': url_for(".render_bmf_space_webpage", field_label=field_label, level_label=dat['level_label']),
                  'dims': dims[dat['level_label']]} for dat in data]
    info['dimtable'] = dimtable
    return render_template("bmf-field_dim_table.html", info=info, title=t, properties=properties, bread=bread)


@bmf_page.route('/<field_label>/<level_label>')
def render_bmf_space_webpage(field_label, level_label):
    info = {}
    t = "Bianchi modular forms of level %s over %s" % (level_label, field_label)
    credit = bianchi_credit
    bread = [('Bianchi modular forms', url_for(".index")),
             (field_pretty(field_label), url_for(".render_bmf_field_dim_table", field_label=field_label)),
             (level_label, '')]
    friends = []
    properties2 = []

    if not field_label_regex.match(field_label):
        info['err'] = "%s is not a valid label for an imaginary quadratic field" % field_label
    else:
        pretty_field_label = field_pretty(field_label)
        if not db_dims().find({'field_label': field_label}):
            info['err'] = "no dimension information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi Modular Forms of level %s over %s" % (level_label, pretty_field_label)
            data = db_dims().find({'field_label': field_label, 'level_label': level_label})
            n = data.count()
            if n==0:
                info['err'] = "no dimension information exists in the database for level %s and field %s" % (level_label, pretty_field_label)
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
                info['field_knowl'] = nf_display_knowl(field_label, getDBConnection(), pretty_field_label)
                w = 'i' if nf.disc()==-4 else 'a'
                L = nf.K().change_names(w)
                alpha = L.gen()
                info['field_gen'] = latex(alpha)
                I = ideal_from_label(L,level_label)
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

                newdim = data['gl2_dims']['2']['new_dim']
                newforms = db_forms().find({'field_label':field_label, 'level_label':level_label}).sort('label_suffix', ASCENDING)
                info['newforms'] = [[f['short_label'],
                                     url_for(".render_bmf_webpage",field_label=f['field_label'], level_label=f['level_label'], label_suffix=f['label_suffix'])] for f in newforms]
                info['nnewforms'] = len(info['newforms'])
                properties2 = [('Base field', pretty_field_label), ('Level',info['level_label']), ('Norm',str(info['level_norm'])), ('New dimension',str(newdim))]
                friends = [('Newform {}'.format(f[0]), f[1]) for f in info['newforms'] ]

    return render_template("bmf-space.html", info=info, credit=credit, title=t, bread=bread, properties2=properties2, friends=friends)

@bmf_page.route('/<field_label>/<level_label>/<label_suffix>/')
def render_bmf_webpage(field_label, level_label, label_suffix):
    label = "-".join([field_label, level_label, label_suffix])
    credit = "John Cremona"
    bread = []
    info = {}
    title = "Bianchi cusp forms"
    data = None
    properties2 = []
    friends = []
    bread = [('Bianchi modular forms', url_for(".index"))]
    try:
        data = WebBMF.by_label(label)
        title = "Bianchi cusp form {} over {}".format(data.short_label,field_pretty(data.field_label))
        bread = [('Bianchi modular forms', url_for(".index")),
                 (field_pretty(data.field_label), url_for(".render_bmf_field_dim_table", field_label=data.field_label)),
                 (data.level_label, url_for('.render_bmf_space_webpage', field_label=data.field_label, level_label=data.level_label)),
                 (data.short_label, '')]
        properties2 = data.properties2
        friends = data.friends
    except ValueError:
        info['err'] = "No Bianchi modular form in the database has label {}".format(label)
    return render_template("bmf-newform.html", title=title, credit=credit, bread=bread, data=data, properties2=properties2, friends=friends, info=info)

def bianchi_modular_form_by_label(lab):
    if lab == '':
        # do nothing: display the top page
        return redirect(url_for(".index"))
    if isinstance(lab, basestring):
        res = db_forms().find_one({'label': lab},{'label':True})
    else:
        res = lab
        lab = res['label']

    if res == None:
        flash(Markup("No Bianchi modular form in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".render_bmf_webpage", field_label = res['field_label'], level_label = res['level_label'], label_suffix = res['label_suffix']))
