import re
import pymongo

from base import app, getDBConnection
from flask import Flask, session, g, render_template, url_for, request, redirect

import sage.all
from sage.all import ZZ, QQ, PolynomialRing, NumberField, latex, AbelianGroup, polygen

from utilities import ajax_more, image_src, web_latex, to_dict, parse_range, coeff_to_poly, pol_to_html


def field_pretty(field_str):
    d,r,D,i = field_str.split('.')
    if d == '1':  # Q
        return '\( {\mathbb Q} \)'
    if d == '2':  # quadratic field
        return '\( {\mathbb Q}(\sqrt{' + D + '}) \)'
    return field_str
#    TODO:  pretty-printing of fields of higher degree

@app.route("/ModularForm/GL2/")
def hilbert_modular_form_render_webpage():
    args = request.args
    if len(args) == 0:      
        info = {    }
        credit = 'L. Dembele, S. Donnelly and J. Voight'	
        t = 'Hilbert Modular Forms'
        bread = [('Hilbert Modular Forms', url_for("hilbert_modular_form_render_webpage"))]
        info['learnmore'] = []

        return render_template("hilbert_modular_form/hilbert_modular_form_all.html", info = info, credit=credit, title=t, bread=bread)
    else:
        return hilbert_modular_form_search(**args)

def hilbert_modular_form_search(**args):
    C = getDBConnection()
    info = to_dict(args) # what has been entered in the search boxes
    if 'natural' in info:
        return render_hmf_webpage({'label' : info['natural']})
    query = {}
    for field in ['field_label', 'weight', 'level_norm', 'dimension']:
        if info.get(field):
            if field == 'weight':
                query[field] = eval(info[field])
            else:
                query[field] = info[field]

    if info.get('count'):        
        try:
            count = int(info['count'])
        except:
            count = 10
    else:
        info['count'] = 10
        count = 10

    info['query'] = dict(query)

    res = C.hmfs.forms.find(query).sort([('label',pymongo.ASCENDING)]).limit(10)
    nres = res.count()
        
    info['forms'] = res
    info['number'] = nres
    if nres==1:
        info['report'] = 'unique match'
    else:
        if nres>count:
            info['report'] = 'displaying first %s of %s matches'%(count,nres)
        else:
            info['report'] = 'displaying all %s matches'%nres

#    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    t = 'Hilbert Modular Form search results'

    bread = [('Hilbert Modular Forms', url_for("hilbert_modular_form_render_webpage")),('Search results',' ')]
    properties = []
    return render_template("hilbert_modular_form/hilbert_modular_form_search.html", info = info, title=t, properties=properties, bread=bread)

@app.route('/ModularForm/GL2/<field_label>/holomorphic/<label>')
def render_hmf_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        label = str(args['label'])
        data = C.hmfs.forms.find_one({'label': label})
    if data is None:
        return "No such field"    
    info = {}
    try:
        info['count'] = args['count']
    except KeyError:
        info['count'] = 10

    hmf_field  = C.hmfs.fields.find_one({'label': data['field_label']})
    field_info = C.numberfields.fields.find_one({'label': data['field_label']})
    field_info['galois_group'] = str(field_info['galois_group'][3])
    info['field_info'] = field_info
    info['field_poly'] = pol_to_html(str(coeff_to_poly(field_info['coefficients'])))

    data['field_label'] = field_pretty(data['field_label'])
    info.update(data)
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet (not yet)', '/')]
    info['friends'] = [('L-function (not yet)', '/')]
#    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    bread = [('Hilbert Modular Forms', url_for("hilbert_modular_form_render_webpage")),('%s'%data['label'],' ')]

    t = "Hilbert Cusp Form %s" % info['label']
    credit = 'L. Dembele, S. Donnelly and J. Voight'	

    eigs = eval(data['hecke_eigenvalues'])
    primes = hmf_field['primes']
    w = polygen(QQ,'w')
    n = min(len(eigs),len(primes))
    info['eigs'] = [{'eigenvalue': eigs[i],
                     'prime_ideal': primes[i], 
                     'prime_norm': eval(primes[i])[0]} for i in range(n)]
        
    properties = []
#     properties = ['<br>']
#     properties.extend('<table>')
#     properties.extend('<tr><td align=left>Degree:<td align=left> %s</td>'%data['degree'])
#     properties.extend('<tr><td align=left>Signature:<td align=left>%s</td>'%data['signature'])
#     properties.extend('<tr><td align=left>Discriminant:<td align=left>%s</td>'%data['discriminant'])
#     if npr==1:
#         properties.extend('<tr><td align=left>Ramified prime:<td align=left>%s</td>'%ram_primes)
#     else:
#         properties.extend('<tr><td align=left>Ramified primes:<td align=left>%s</td>'%ram_primes)
#     properties.extend('<tr><td align=left>Class number:<td align=left>%s</td>'%data['class_number'])
#     properties.extend('<tr><td align=left>Galois group:<td align=left>%s</td>'%data['galois_group'])
#     properties.extend('</table>')

    return render_template("hilbert_modular_form/hilbert_modular_form.html", info = info, properties=properties, credit=credit, title = t, bread=bread)

