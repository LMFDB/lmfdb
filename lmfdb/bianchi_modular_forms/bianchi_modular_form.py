# -*- coding: utf-8 -*-

import re

from flask import render_template, url_for, request, redirect, flash
from markupsafe import Markup

from sage.all import latex

from lmfdb.db_backend import db
from lmfdb.utils import to_dict, web_latex_ideal_fact
from lmfdb.search_parsing import parse_range, nf_string_to_label, parse_nf_string, parse_start, parse_count
from lmfdb.search_wrapper import search_wrap
from lmfdb.hilbert_modular_forms.hilbert_modular_form import teXify_pol
from lmfdb.bianchi_modular_forms import bmf_page
from lmfdb.bianchi_modular_forms.web_BMF import WebBMF
from lmfdb.WebNumberField import field_pretty, WebNumberField, nf_display_knowl
from lmfdb.nfutils.psort import ideal_from_label


bianchi_credit = 'John Cremona, Aurel Page, Alexander Rahm, Haluk Sengun'

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Bianchi newform labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def bc_info(bc):
    return 'yes' if bc>0 else 'yes (twist)' if bc<0 else 'no'

def cm_info(cm):
    try:
        return 'no' if cm==0 else str(cm) if cm%4==1 else str(4*cm)
    except TypeError:
        return str(cm)

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
        gl2_fields = ["2.0.{}.1".format(d) for d in [4,8,3,7,11]]
        sl2_fields = gl2_fields + ["2.0.{}.1".format(d) for d in [19,43,67,163,20]]
        gl2_names = ["\(\Q(\sqrt{-%s})\)" % d for d in [1,2,3,7,11]]
        sl2_names = gl2_names + ["\(\Q(\sqrt{-%s})\)" % d for d in [19,43,67,163,5]]
        info['gl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_gl2", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]
        info['sl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_sl2", field_label=f), 'name':n} for f,n in zip(sl2_fields,sl2_names)]
        info['field_forms'] = [{'url':url_for("bmf.index", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]
        bc_examples = []
        bc_examples.append(('base-change of a newform with rational coefficients',
                         '2.0.4.1-100.2-a',
                         url_for('.render_bmf_webpage',field_label='2.0.4.1', level_label='100.2', label_suffix='a'),' (with an associated elliptic curve which is a base-change)'))
        bc_examples.append(('base-change of a newform with coefficients in \(\mathbb{Q}(\sqrt{2})\)',
                         '2.0.4.1-16384.1-d',
                         url_for('.render_bmf_webpage',field_label='2.0.4.1', level_label='16384.1', label_suffix='d'),' (with an associated elliptic curve which is not a base-change)'))
        bc_examples.append(('base-change of a newform with coefficients in \(\mathbb{Q}(\sqrt{6})\)',
                         '2.0.3.1-6561.1-b',
                         url_for('.render_bmf_webpage',field_label='2.0.3.1', level_label='6561.1', label_suffix='b'),' (with no associated elliptic curve)'))
        bc_examples.append(('base-change of a newform with coefficients in \(\mathbb{Q}(\sqrt{5})\), with CM by \(\mathbb{Q}(\sqrt{-35})\)',
                         '2.0.7.1-10000.1-b',
                         url_for('.render_bmf_webpage',field_label='2.0.7.1', level_label='10000.1', label_suffix='b'),' (with no associated elliptic curve)'))

        credit = bianchi_credit
        t = 'Bianchi Modular Forms'
        bread = [('Modular Forms', url_for('mf.modular_form_main_page')), ('Bianchi Modular Forms', url_for(".index"))]
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, credit=credit, title=t, bread=bread, bc_examples=bc_examples, learnmore=learnmore_list())
    else:
        return bianchi_modular_form_search(args)

@bmf_page.route("/random")
def random_bmf():    # Random Bianchi modular form
    label = db.bmf_forms.random()
    return bianchi_modular_form_by_label(label)

def bianchi_modular_form_jump(info):
    label = info['label']
    dat = label.split("-")
    if len(dat)==2: # assume field & level, display space
        return render_bmf_space_webpage(dat[0], dat[1])
    else: # assume single newform label; will display an error if invalid
        return bianchi_modular_form_by_label(label)

def bianchi_modular_form_postprocess(res, info, query):
    if info['number'] > 0:
        info['field_pretty_name'] = field_pretty(res[0]['field_label'])
    else:
        info['field_pretty_name'] = ''
    res.sort(key=lambda x: [x['level_norm'], int(x['level_number']), x['label_suffix']])
    return res

@search_wrap(template="bmf-search_results.html",
             table=db.bmf_forms,
             title='Bianchi Modular Form Search Results',
             err_title='Bianchi Modular Forms Search Input Error',
             shortcuts={'label': bianchi_modular_form_jump},
             projection=['label','field_label','short_label','level_label','level_norm','label_suffix','level_ideal','dimension','sfe','bc','CM'],
             cleaners={"level_number": lambda v: v['level_label'].split(".")[1],
                       "level_ideal": lambda v: teXify_pol(v['level_ideal']),
                       "sfe": lambda v: "+1" if v.get('sfe',None)==1 else ("-1" if v.get('sfe',None)==-1 else "?"),
                       "url": lambda v: url_for('.render_bmf_webpage',field_label=v['field_label'], level_label=v['level_label'], label_suffix=v['label_suffix']),
                       "bc": lambda v: bc_info(v['bc']),
                       "cm": lambda v: cm_info(v.pop('CM', '?'))},
             bread=lambda:[('Bianchi Modular Forms', url_for(".index")),
                           ('Search Results', '.')],
             learnmore=learnmore_list,
             properties=lambda: [])
def bianchi_modular_form_search(info, query):
    """Function to handle requests from the top page, either jump to one
    newform or do a search.
    """
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
    if not 'sfe' in info:
        info['sfe'] = "any"
    elif info['sfe'] != "any":
        query['sfe'] = int(info['sfe'])
    if 'include_cm' in info:
        if info['include_cm'] == 'exclude':
            query['CM'] = 0 # will exclude NULL values
        elif info['include_cm'] == 'only':
            query['CM'] = {'$ne': 0} # will exclude NULL values
    if 'include_base_change' in info and info['include_base_change'] == 'off':
        query['bc'] = 0
    else:
        info['include_base_change'] = "on"

@bmf_page.route('/<field_label>')
def bmf_search_field(field_label):
    return bianchi_modular_form_search(field_label=field_label)

@bmf_page.route('/gl2dims/<field_label>')
def render_bmf_field_dim_table_gl2(**args):
    return bmf_field_dim_table(gl_or_sl='gl2_dims', **args)

@bmf_page.route('/sl2dims/<field_label>')
def render_bmf_field_dim_table_sl2(**args):
    return bmf_field_dim_table(gl_or_sl='sl2_dims', **args)

def bmf_field_dim_table(**args):
    argsdict = to_dict(args)
    argsdict.update(to_dict(request.args))
    gl_or_sl = argsdict['gl_or_sl']

    field_label=argsdict['field_label']
    field_label = nf_string_to_label(field_label)

    start = parse_start(argsdict)

    info={}
    info['gl_or_sl'] = gl_or_sl
    # level_flag controls whether to list all levels ('all'), only
    # those with positive cuspidal dimension ('cusp'), or only those
    # with positive new dimension ('new').  Default is 'cusp'.
    level_flag = argsdict.get('level_flag', 'cusp')
    info['level_flag'] = level_flag
    count = parse_count(argsdict, 50)

    pretty_field_label = field_pretty(field_label)
    bread = [('Bianchi Modular Forms', url_for(".index")), (
        pretty_field_label, ' ')]
    properties = []
    if gl_or_sl=='gl2_dims':
        info['group'] = 'GL(2)'
        info['bgroup'] = '\GL(2,\mathcal{O}_K)'
    else:
        info['group'] = 'SL(2)'
        info['bgroup'] = '\SL(2,\mathcal{O}_K)'
    t = ' '.join(['Dimensions of Spaces of {} Bianchi Modular Forms over'.format(info['group']), pretty_field_label])
    query = {}
    query['field_label'] = field_label
    query[gl_or_sl] = {'$exists': True}
    data = db.bmf_dims.search(query, limit=count, offset=start, info=info)
    nres = info['number']
    if nres > count or start != 0:
        info['report'] = 'Displaying items %s-%s of %s levels,' % (start + 1, min(nres, start + count), nres)
    else:
        info['report'] = 'Displaying all %s levels,' % nres

    # convert data to a list and eliminate levels where all
    # new/cuspidal dimensions are 0.  (This could be done at the
    # search stage, but that requires adding new fields to each
    # record.)
    def filter(dat, flag):
        dat1 = dat[gl_or_sl]
        return any([int(dat1[w][flag])>0 for w in dat1])
    flag = 'cuspidal_dim' if level_flag=='cusp' else 'new_dim'
    data = [dat for dat in data if level_flag == 'all' or filter(dat, flag)]

    info['field'] = field_label
    info['field_pretty'] = pretty_field_label
    nf = WebNumberField(field_label)
    info['base_galois_group'] = nf.galois_string()
    info['field_degree'] = nf.degree()
    info['field_disc'] = str(nf.disc())
    info['field_poly'] = teXify_pol(str(nf.poly()))
    weights = set()
    for dat in data:
        weights = weights.union(set(dat[gl_or_sl].keys()))
    weights = list([int(w) for w in weights])
    weights.sort()
    info['weights'] = weights
    info['nweights'] = len(weights)

    data.sort(key = lambda x: [int(y) for y in x['level_label'].split(".")])
    dims = {}
    for dat in data:
        dims[dat['level_label']] = d = {}
        for w in weights:
            sw = str(w)
            if sw in dat[gl_or_sl]:
                d[w] = {'d': dat[gl_or_sl][sw]['cuspidal_dim'],
                        'n': dat[gl_or_sl][sw]['new_dim']}
            else:
                d[w] = {'d': '?', 'n': '?'}
    info['nlevels'] = len(data)
    dimtable = [{'level_label': dat['level_label'],
                 'level_norm': dat['level_norm'],
                 'level_space': url_for(".render_bmf_space_webpage", field_label=field_label, level_label=dat['level_label']) if gl_or_sl=='gl2_dims' else "",
                  'dims': dims[dat['level_label']]} for dat in data]
    info['dimtable'] = dimtable
    return render_template("bmf-field_dim_table.html", info=info, title=t, properties=properties, bread=bread)

@bmf_page.route('/<field_label>/<level_label>')
def render_bmf_space_webpage(field_label, level_label):
    info = {}
    t = "Bianchi Modular Forms of Level %s over %s" % (level_label, field_label)
    credit = bianchi_credit
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Bianchi Modular Forms', url_for(".index")),
             (field_pretty(field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=field_label)),
             (level_label, '')]
    friends = []
    properties2 = []

    if not field_label_regex.match(field_label):
        info['err'] = "%s is not a valid label for an imaginary quadratic field" % field_label
    else:
        pretty_field_label = field_pretty(field_label)
        if not db.bmf_dims.exists({'field_label': field_label}):
            info['err'] = "no dimension information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi Modular Forms of level %s over %s" % (level_label, pretty_field_label)
            data = db.bmf_dims.lucky({'field_label': field_label, 'level_label': level_label})
            if not data:
                info['err'] = "no dimension information exists in the database for level %s and field %s" % (level_label, pretty_field_label)
            else:
                info['label'] = data['label']
                info['nf'] = nf = WebNumberField(field_label)
                info['field_label'] = field_label
                info['pretty_field_label'] = pretty_field_label
                info['level_label'] = level_label
                info['level_norm'] = data['level_norm']
                info['field_poly'] = teXify_pol(str(nf.poly()))
                info['field_knowl'] = nf_display_knowl(field_label, pretty_field_label)
                w = 'i' if nf.disc()==-4 else 'a'
                L = nf.K().change_names(w)
                alpha = L.gen()
                info['field_gen'] = latex(alpha)
                I = ideal_from_label(L,level_label)
                info['level_gen'] = latex(I.gens_reduced()[0])
                info['level_fact'] = web_latex_ideal_fact(I.factor(), enclose=False)
                dim_data = data['gl2_dims']
                weights = dim_data.keys()
                weights.sort(key=lambda w: int(w))
                for w in weights:
                    dim_data[w]['dim']=dim_data[w]['cuspidal_dim']
                info['dim_data'] = dim_data
                info['weights'] = weights
                info['nweights'] = len(weights)

                newdim = data['gl2_dims']['2']['new_dim']
                newforms = db.bmf_forms.search({'field_label':field_label, 'level_label':level_label})
                info['nfdata'] = [{
                    'label': f['short_label'],
                    'url': url_for(".render_bmf_webpage",field_label=f['field_label'], level_label=f['level_label'], label_suffix=f['label_suffix']),
                    'wt': f['weight'],
                    'dim': f['dimension'],
                    'sfe': "+1" if f.get('sfe',None)==1 else "-1" if f.get('sfe',None)==-1 else "?",
                    'bc': bc_info(f['bc']),
                    'cm': cm_info(f.get('CM','?')),
                    } for f in newforms]
                info['nnewforms'] = len(info['nfdata'])
                properties2 = [('Base field', pretty_field_label), ('Level',info['level_label']), ('Norm',str(info['level_norm'])), ('New dimension',str(newdim))]
                friends = [('Newform {}'.format(f['label']), f['url']) for f in info['nfdata'] ]

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
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')), ('Bianchi Modular Forms', url_for(".index"))]
    try:
        data = WebBMF.by_label(label)
        title = "Bianchi cusp form {} over {}".format(data.short_label,field_pretty(data.field_label))
        bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
                 ('Bianchi Modular Forms', url_for(".index")),
                 (field_pretty(data.field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=data.field_label)),
                 (data.level_label, url_for('.render_bmf_space_webpage', field_label=data.field_label, level_label=data.level_label)),
                 (data.short_label, '')]
        properties2 = data.properties2
        friends = data.friends
    except ValueError:
        raise
        info['err'] = "No Bianchi modular form in the database has label {}".format(label)
    return render_template("bmf-newform.html", title=title, credit=credit, bread=bread, data=data, properties2=properties2, friends=friends, info=info)

def bianchi_modular_form_by_label(lab):
    if lab == '':
        # do nothing: display the top page
        return redirect(url_for(".index"))
    if isinstance(lab, basestring):
        res = db.bmf_forms.lookup(lab)
    else:
        res = lab
        lab = res['label']

    if res is None:
        flash(Markup("No Bianchi modular form in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".render_bmf_webpage", field_label = res['field_label'], level_label = res['level_label'], label_suffix = res['label_suffix']))

@bmf_page.route("/Source")
def how_computed_page():
    t = 'Source of the Bianchi Modular Forms'
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Bianchi Modular Forms', url_for(".index")),
             ('Source', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.mf.bianchi.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@bmf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Bianchi Modular Form Data'
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Bianchi Modular Forms', url_for(".index")),
             ('Completeness', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.mf.bianchi.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@bmf_page.route("/Labels")
def labels_page():
    t = 'Labels for Bianchi Newforms'
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Bianchi Modular Forms', url_for(".index")),
             ('Labels', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='mf.bianchi.labels',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

