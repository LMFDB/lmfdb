# -*- coding: utf-8 -*-
from six import string_types
import re

from flask import render_template, url_for, request, redirect
from sage.all import latex

from lmfdb import db
from lmfdb.utils import (
    to_dict, web_latex_ideal_fact, flash_error,
    nf_string_to_label, parse_nf_string, parse_noop, parse_start, parse_count, parse_ints,
    SearchArray, TextBox, SelectBox, ExcludeOnlyBox, CountBox,
    teXify_pol, search_wrap)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.number_fields.web_number_field import WebNumberField, nf_display_knowl
from lmfdb.nfutils.psort import ideal_from_label
from lmfdb.bianchi_modular_forms import bmf_page
from lmfdb.bianchi_modular_forms.web_BMF import WebBMF


bianchi_credit = 'John Cremona, Aurel Page, Alexander Rahm, Haluk Sengun'

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')

def learnmore_list():
    return [('Source of the data', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Bianchi modular form labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def get_bread(tail=[]):
    base = [('Modular forms', url_for('modular_forms')),
            ('Bianchi', url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def bc_info(bc):
    return 'yes' if bc > 0 else 'yes (twist)' if bc < 0 else 'no'


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
    info = to_dict(request.args, search_array=BMFSearchArray())
    if not request.args:
        gl2_fields = ["2.0.{}.1".format(d) for d in [4,8,3,7,11]]
        sl2_fields = gl2_fields + ["2.0.{}.1".format(d) for d in [19,43,67,163,20]]
        gl2_names = [r"\(\Q(\sqrt{-%s})\)" % d for d in [1,2,3,7,11]]
        sl2_names = gl2_names + [r"\(\Q(\sqrt{-%s})\)" % d for d in [19,43,67,163,5]]
        info['gl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_gl2", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]
        info['sl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_sl2", field_label=f), 'name':n} for f,n in zip(sl2_fields,sl2_names)]
        info['field_forms'] = [{'url':url_for("bmf.index", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]

        credit = bianchi_credit
        t = 'Bianchi modular forms'
        bread = get_bread()
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())
    else:
        return bianchi_modular_form_search(info)

@bmf_page.route("/random")
def random_bmf():    # Random Bianchi modular form
    label = db.bmf_forms.random()
    return bianchi_modular_form_by_label(label)

@bmf_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "mf.bianchi",
        db.bmf_forms,
        url_for_label=url_for_label,
        title="Some interesting Bianchi modular forms",
        credit=bianchi_credit,
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

def bianchi_modular_form_jump(info):
    label = info['jump'].strip()
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

def url_for_label(label):
    return url_for(".render_bmf_webpage",
                   **dict(zip(
                       ['field_label', 'level_label', 'label_suffix'],
                       label.split('-')
                   )))

@search_wrap(template="bmf-search_results.html",
             table=db.bmf_forms,
             title='Bianchi modular form search results',
             err_title='Bianchi modular forms search input error',
             shortcuts={'jump': bianchi_modular_form_jump},
             projection=['label','field_label','short_label','level_label','level_norm','label_suffix','level_ideal','dimension','sfe','bc','CM'],
             cleaners={"level_number": lambda v: v['level_label'].split(".")[1],
                       "level_ideal": lambda v: teXify_pol(v['level_ideal']),
                       "sfe": lambda v: "+1" if v.get('sfe',None)==1 else ("-1" if v.get('sfe',None)==-1 else "?"),
                       "url": lambda v: url_for('.render_bmf_webpage',field_label=v['field_label'], level_label=v['level_label'], label_suffix=v['label_suffix']),
                       "bc": lambda v: bc_info(v['bc']),
                       "cm": lambda v: cm_info(v.pop('CM', '?')),
                       "field_knowl": lambda e: nf_display_knowl(e['field_label'], field_pretty(e['field_label']))},
             bread=lambda:get_bread("Search results"),
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             properties=lambda: [])

def bianchi_modular_form_search(info, query):
    """Function to handle requests from the top page, either jump to one
    newform or do a search.
    """
    parse_nf_string(info, query, 'field_label', name='base number field')
    parse_noop(info, query, 'label')
    parse_ints(info, query, 'dimension')
    parse_ints(info, query, 'level_norm')
    if not 'sfe' in info:
        info['sfe'] = "any"
    elif info['sfe'] != "any":
        query['sfe'] = int(info['sfe'])
    if 'include_cm' in info:
        if info['include_cm'] in ['exclude', 'off']:
            query['CM'] = 0 # will exclude NULL values
        elif info['include_cm'] == 'only':
            query['CM'] = {'$ne': 0} # will exclude NULL values
    if info.get('include_base_change') =='exclude':
        query['bc'] = 0
    elif info.get('include_base_change') == 'only':
        query['bc'] = {'$ne': 0}

@bmf_page.route('/<field_label>')
def bmf_search_field(field_label):
    return bianchi_modular_form_search({'field_label':field_label, 'search_array':BMFSearchArray()})

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
    bread = get_bread(pretty_field_label)
    properties = []
    query = {}
    query['field_label'] = field_label
    if gl_or_sl=='gl2_dims':
        info['group'] = 'GL(2)'
        info['bgroup'] = r'\GL(2,\mathcal{O}_K)'
    else:
        info['group'] = 'SL(2)'
        info['bgroup'] = r'\SL(2,\mathcal{O}_K)'
    if level_flag == 'all':
        query[gl_or_sl] = {'$exists': True}
    else:
        # Only get records where the cuspdial/new dimension is positive for some weight
        totaldim = gl_or_sl.replace('dims', level_flag) + '_totaldim'
        query[totaldim] = {'$gt': 0}
    t = ' '.join(['Dimensions of spaces of {} Bianchi modular forms over'.format(info['group']), pretty_field_label])
    data = list(db.bmf_dims.search(query, limit=count, offset=start, info=info))
    nres = info['number']
    if not info['exact_count']:
        info['number'] = nres = db.bmf_dims.count(query)
        info['exact_count'] = True
    if nres > count or start != 0:
        info['report'] = 'Displaying items %s-%s of %s levels,' % (start + 1, min(nres, start + count), nres)
    else:
        info['report'] = 'Displaying all %s levels,' % nres

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
    t = "Bianchi modular forms of level %s over %s" % (level_label, field_label)
    credit = bianchi_credit
    bread = get_bread([
        (field_pretty(field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=field_label)),
        (level_label, '')])
    friends = []
    properties = []

    if not field_label_regex.match(field_label):
        info['err'] = "%s is not a valid label for an imaginary quadratic field" % field_label
    else:
        pretty_field_label = field_pretty(field_label)
        if not db.bmf_dims.exists({'field_label': field_label}):
            info['err'] = "no dimension information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi modular forms of level %s over %s" % (level_label, pretty_field_label)
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
                weights = list(dim_data)
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
                # currently we have newforms of dimension 1 and 2 only (mostly dimension 1)
                info['nnf1'] = sum(1 for f in info['nfdata'] if f['dim']==1)
                info['nnf2'] = sum(1 for f in info['nfdata'] if f['dim']==2)
                info['nnf_missing'] = dim_data['2']['new_dim'] - info['nnf1'] - 2*info['nnf2']
                properties = [('Base field', pretty_field_label), ('Level',info['level_label']), ('Norm',str(info['level_norm'])), ('New dimension',str(newdim))]
                friends = [('Newform {}'.format(f['label']), f['url']) for f in info['nfdata'] ]

    return render_template("bmf-space.html", info=info, credit=credit, title=t, bread=bread, properties=properties, friends=friends, learnmore=learnmore_list())

@bmf_page.route('/<field_label>/<level_label>/<label_suffix>/download/<download_type>')
def render_bmf_webpage_download(**args):
    if args['download_type'] == 'sage':
        pass # TODO

def download_bmf_sage(**args):
    label = "-".join([args['field_label'],args['level_label'],args['label_suffix']])
    F = WebNumberField(args['field_label'])
    try:
        data = WebBMF.by_label(label)
    except ValueError:
        flash_error("No Bianchi modular form in the database has label %s", label)
        return "// No Bianchi modular form in the database has label %s"

@bmf_page.route('/<field_label>/<level_label>/<label_suffix>/')
def render_bmf_webpage(field_label, level_label, label_suffix):
    label = "-".join([field_label, level_label, label_suffix])
    credit = "John Cremona"
    info = {}
    title = "Bianchi cusp forms"
    data = None
    properties = []
    friends = []
    bread = get_bread()
    try:
        data = WebBMF.by_label(label)
        title = "Bianchi cusp form {} over {}".format(data.short_label,field_pretty(data.field_label))
        bread = get_bread([
            (field_pretty(data.field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=data.field_label)),
            (data.level_label, url_for('.render_bmf_space_webpage', field_label=data.field_label, level_label=data.level_label)),
            (data.short_label, '')])
        properties = data.properties
        friends = data.friends
    except ValueError:
        flash_error("No Bianchi modular form in the database has label %s", label)
        return redirect(url_for(".index"))
    return render_template(
        "bmf-newform.html",
        title=title,
        credit=credit,
        bread=bread,
        data=data,
        properties=properties,
        friends=friends,
        info=info,
        learnmore=learnmore_list(),
        KNOWL_ID="mf.bianchi.%s"%label,
    )

def bianchi_modular_form_by_label(lab):
    if lab == '':
        # do nothing: display the top page
        return redirect(url_for(".index"))
    if isinstance(lab, string_types):
        res = db.bmf_forms.lookup(lab)
    else:
        res = lab
        lab = res['label']

    if res is None:
        flash_error("No Bianchi modular form in the database has label or name %s", lab)
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".render_bmf_webpage",
                        field_label=res['field_label'],
                        level_label=res['level_label'],
                        label_suffix=res['label_suffix']))

@bmf_page.route("/Source")
def how_computed_page():
    t = 'Source of Bianchi modular form data'
    bread = get_bread("Source")
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.mf.bianchi.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@bmf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Bianchi modular form data'
    bread = get_bread("Completeness")
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.mf.bianchi.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@bmf_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of Bianchi modular form data'
    bread = get_bread("Reliability")
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.mf.bianchi.reliability',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@bmf_page.route("/Labels")
def labels_page():
    t = 'Labels for Bianchi newforms'
    bread = get_bread("Labels")
    credit = 'John Cremona'
    return render_template("single.html", kid='mf.bianchi.labels',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))


class BMFSearchArray(SearchArray):
    noun = "form"
    plural_noun = "forms"
    jump_example = "2.0.4.1-65.2-a"
    jump_egspan = "e.g. 2.0.4.1-65.2-a (single form) or 2.0.4.1-65.2 (space of forms at a level)"
    def __init__(self):
        field = TextBox(
            name='field_label',
            label='Base field',
            knowl='nf',
            example='2.0.4.1',
            example_span=r'either a field label, e.g. 2.0.4.1 for \(\mathbb{Q}(\sqrt{-1})\), or a nickname, e.g. Qsqrt-1',
            example_span_colspan=4)
        level = TextBox(
            name='level_norm',
            label='Level norm',
            knowl='mf.bianchi.level',
            example='1',
            example_span='e.g. 1 or 1-100')
        dimension = TextBox(
            name='dimension',
            label='Dimension',
            knowl='mf.bianchi.spaces',
            example='1',
            example_span='e.g. 1 or 2')

        sign = SelectBox(
            name='sfe',
            label='Sign',
            knowl='mf.bianchi.sign',
            options=[("", ""), ("+1", "+1"), ("-1", "-1")],
            example_col=True
        )
        base_change = ExcludeOnlyBox(
            name='include_base_change',
            label='Base change',
            knowl='mf.bianchi.base_change'
        )
        CM = ExcludeOnlyBox(
            name='include_cm',
            label='CM',
            knowl='mf.bianchi.cm'
        )
        count = CountBox()

        self.browse_array = [
            [field],
            [level, sign],
            [dimension, base_change],
            [count, CM]
        ]
        self.refine_array = [
            [field, level, dimension],
            [sign, base_change, CM]
        ]
