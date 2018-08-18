# -*- coding: utf-8 -*-

import re

from lmfdb.db_backend import db
from flask import render_template, url_for, request
from lmfdb.half_integral_weight_forms import hiwf_page

from sage.all import QQ, PolynomialRing, PowerSeriesRing

from lmfdb.utils import flash_error
from lmfdb.search_parsing import parse_ints
from lmfdb.search_wrapper import search_wrap

from lmfdb.WebNumberField import nf_display_knowl


@hiwf_page.route("/")
def half_integral_weight_form_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = 'Samuele Anni, Soma Purkait'
        t = 'Half Integral Weight Cusp Forms'
        bread = [('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage"))]
        info['learnmore'] = []
        return render_template("half_integral_weight_form_all.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return half_integral_weight_form_search(args)

@search_wrap(template="half_integral_weight_form_search.html",
             table=db.halfmf_forms,
             title='Half Integral Weight Cusp Forms Search Results',
             err_title='Half Integral Weight Cusp Forms Search Input Error',
             per_page=100,
             shortcuts={'label':lambda info:render_hiwf_webpage(label=info['label'])},
             projection=['level','label','weight','character','dim'],
             cleaners={'char': lambda v:"\chi_{"+v['character'].split(".")[0]+"}("+v['character'].split(".")[1]+",\cdot)",
                       'ch_lab': lambda v: v.pop('character').replace('.','/'),
                       'dimension': lambda v: v.pop('dim')},
             bread=lambda:[('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage")),('Search Results', ' ')],
             properties=lambda: [])
def half_integral_weight_form_search(info, query):
    parse_ints(info, query, 'weight')
    parse_ints(info, query, 'level')
    if info.get('character','').strip():
        if re.match('^\d+.\d+$', info['character'].strip()):
            query['character'] = info['character'].strip()
        else:
            flash_error("%s is not a valid Dirichlet character label, it should be of the form q.n", info['character'])
            raise ValueError

def print_q_expansion(list):
     list=[str(c) for c in list]
     Qa=PolynomialRing(QQ,'a')
     Qq=PowerSeriesRing(Qa,'q')
     return str(Qq([c for c in list]).add_bigoh(len(list)+1))



def my_latex_from_qexp(s):
    ss = ""
    ss += re.sub('x\d', 'x', s)
    ss = re.sub("\^(\d+)", "^{\\1}", ss)
    ss = re.sub('\*', '', ss)
    ss = re.sub('zeta(\d+)', 'zeta_{\\1}', ss)
    ss = re.sub('zeta', '\zeta', ss)
    ss += ""
    return ss



@hiwf_page.route('/<label>')
def render_hiwf_webpage(**args):
    data = None
    if 'label' in args:
        label = str(args['label'])
        data = db.halfmf_forms.lookup(label)
    if data is None:
        return "No such field"
    info = {}
    info.update(data)

    info['friends'] = []

    bread = [('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage")), ('%s' % data['label'], ' ')]
    t = "Half Integral Weight Cusp Forms %s" % info['label']
    credit = 'Samuele Anni and Soma Purkait'

    dim = data['dim']
    dimtheta = data['dimtheta']
    dimnew=dim-dimtheta
    info['dimension'] = dim
    info['dimtheta']= dimtheta
    info['dimnew'] = dimnew
    chi = data['character']
    info['ch_lab']= chi.replace('.','/')
    chi1=chi.split(".")
    chi2="\chi_{"+chi1[0]+"}("+chi1[1]+",\cdot)"
    info['char']= chi2
    info['newpart']=data['newpart']
    new=[]
    for n in data['newpart']:
        v={}
        v['dim'] = n['dim_image']
        s=[]
        for h in n['half_forms']:
            s.append(my_latex_from_qexp(print_q_expansion(h)))
        v['hiwf'] = s
        v['mf'] = n['mf_label']
        v['nf'] = n['nf_label']
        v['field_knowl'] = nf_display_knowl(n['nf_label'], n['nf_label'])
        new.append(v)
    info['new']= new
    if dimtheta !=0:
        theta=[]
        for m in data['thetas']:
            for n in m:
                n_lab= n.replace('.','/')
                n_l=n.split(".")
                n_lat="\chi_{"+n_l[0]+"}("+n_l[1]+",\cdot)"
                v=[n_lab, n_lat]
                theta.append(v)
        info['theta']= theta
    else:
        info['theta']= data['thetas']
    return render_template("half_integral_weight_form.html", info=info, credit=credit, title=t, bread=bread)




