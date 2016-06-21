# -*- coding: utf-8 -*-
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from flask import render_template, url_for, request, send_file, flash, redirect
from lmfdb.search_parsing import parse_range
from markupsafe import Markup
import urllib, os, json, StringIO
import dimensions, sample, collection
from sage.all import latex, ZZ, Set
from lmfdb.number_fields.number_field import poly_to_field_label, field_pretty
from lmfdb.siegel_modular_forms import smf_page
from lmfdb.siegel_modular_forms import smf_logger
from lmfdb.search_parsing import parse_ints, parse_ints_to_list_flash
from lmfdb.utils import to_dict

###############################################################################
# Utitlity functions
###############################################################################

def scan_collections():
    """
    scan filesystem for static instances of Collection.
    """
    colns = dict()
    root = os.path.dirname(os.path.abspath(__file__))
    static = os.path.join(root, 'static')
    for a,b,files in os.walk(static):
        for f in files:
            if f.endswith('.json'):
                c = f[:-5]
            colns[c] = collection.Collection(c, location = static)
    # Note that there is no point in caching this data
    # Each worker thread will need to recreate it anyway (and its fast in any case)
    return colns

def find_collection(coll):
    root = os.path.dirname(os.path.abspath(__file__))
    static = os.path.join(root, 'static')
    try:
        return collection.Collection(coll, location = static)
    except (ValueError,IOError):
        return None

def find_samples(coll, weight):
    slist = sample.smf_db_samples().find({'collection':coll, 'weight':str(weight)})
    ret = []
    for res in slist:
        name = res['name']
        url = url_for(".by_label", label=coll+"."+res['name'])
        ret.append({'url':url, 'name':name})
    return ret

def download_sample(name):
    a,b = name.split('.')
    f = StringIO.StringIO(sample.export(a, b))
    f.seek(0)
    return send_file(f, attachment_filename = name + '.json', as_attachment = True)


###############################################################################
# Page routing functions
###############################################################################

@smf_page.route('/')
def index():
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('.index'))]
    if len(request.args) > 0:
        if 'download' in request.args:
            return download_sample(request.args.get('download'))
        else:
            return render_search_results_page(request.args, bread)
    return render_main_page(bread)
    
@smf_page.route("/random")
def random_sample():
    return redirect(url_for('.by_label', label='.'.join(sample.random_sample_name())), 301)

@smf_page.route('/<label>')
@smf_page.route('/<label>/')
def by_label(label):
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('.index'))]
    slabel = label.split('.')
    col = find_collection (slabel[0])
    if col:
        if len(slabel) == 1:
            return render_collection_page(col, request.args, bread)
        if len(slabel) == 2:
            sam = sample.Samples({ 'collection': slabel[0], 'name': slabel[1]})
            if len(sam) > 0:
                bread.append(('$'+col.latex_name()+'$', url_for('.by_label',label=slabel[0])))
                return render_sample_page(col, sam[0], request.args, bread)
    flash(Markup("No siegel modular form data for <span style='color:black'>%s</span> was found in  the database"%label),"error")
    return redirect(url_for(".index"))

@smf_page.route('/Sp4Z_j/<int:k>/<int:j>')
@smf_page.route('/Sp4Z_j/<int:k>/<int:j>/')
def Sp4Z_j_space(j=4, k=4):
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('.index')),
             ('$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z})$', url_for('.Sp4Z_j')),
             ('$M_{%s,%s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k,j), '')]
    if j%2:
        # redirect to general page for Sp4Z_j which will display an error message
        return redirect(url_for(".Sp4Z_j",k=str(k),j=str(j)))
    info = { 'args':{'k':str(k),'j':str(j)} }
    try:
        if j in [0,2]:
            headers, table = dimensions._dimension_Sp4Z([k])
            info['samples'] = find_samples('Sp4Z' if j==0 else 'Sp4Z_2', k)
        else:
            headers, table = dimensions._dimension_Gamma_2([k], j, group='Sp4(Z)')
        info['headers'] = headers
        info['subspace'] = table[k]
    except NotImplementedError:
        # redirect to general page for Sp4Z_j which will display an error message
        return redirect(url_for(".Sp4Z_j",k=str(k),j=str(j)))
    return render_template('ModularForm_GSp4_Q_full_level_space.html',
                           title = '$M_{%s, %s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k, j),
                           bread=bread,
                           info=info);

@smf_page.route('/Sp4Z_j')
@smf_page.route('/Sp4Z_j/')
def Sp4Z_j():
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('.index')),
             ('$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$', '')]
    info={'args':request.args}
    try:
        dim_args = dimensions.parse_dim_args(request.args, {'k':'10-20','j':'0-30'})
    except ValueError:
        info['error'] = True
    if not info.get('error'):
        info['dim_args'] = dim_args
        try:
            info['table'] = dimensions.dimension_table_Sp4Z_j(dim_args['k_range'], dim_args['j_range'])
        except NotImplementedError as errmsg:
            flash(Markup(errmsg), "error")
            info['error'] = True
    return render_template('ModularForm_GSp4_Q_Sp4Zj.html',
                           title='$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$',
                           bread = bread,
                           info = info
                           )

##########################################################
# Page rendering functions
##########################################################

def render_main_page(bread):
    cols = scan_collections()
    col_list = [cols[c] for c in cols if cols[c].computes_dimensions()]
    col_list.sort(key=lambda x: x.order)
    info = { 'col_list': col_list, 'args': {}, 'number_of_samples': sample.count_samples()}
    return render_template('ModularForm_GSp4_Q_index.html',
                            title='Siegel Modular Forms',
                            bread=bread,
                            info=info)

def build_dimension_table(info, col, args):
    try:
        dim_args = dimensions.parse_dim_args(args, col.dim_args_default)
    except ValueError:
        info['error'] = True
    if not info.get('error'):
        info['dim_args'] = dim_args
        kwargs={}
        try:
            for arg in col.dimension_desc()['args']:
                if (arg == 'wt_range' or arg == 'k_range') and 'k_range' in dim_args:
                    kwargs[arg] = dim_args['k_range']
                elif (arg == 'wt' or arg == 'k') and 'k_range' in dim_args:
                    if len(dim_args['k_range']) != 1:
                        raise NotImpelmentedError("Please specify a single value of <span style='color:black'>$k$</span> rather than a range of values.")
                    kwargs[arg] = dim_args['k_range'][0]
                elif arg == 'j_range' and 'j_range' in dim_args:
                    kwargs[arg] = dim_args['j_range']
                elif arg == 'j' and 'j_range' in dim_args:
                    if len(dim_args['j_range']) != 1:
                        raise NotImplementedError("Please specify a single value of <span style='color:black'>$j$</span> rather than a range of values.")
                    kwargs[arg] = dim_args['j_range'][0]
        except NotImplementedError as errmsg:
            flash(Markup(errmsg), "error")
            info['error'] = True
        if not info.get('error'):
            info['kwargs'] = kwargs
            try:
                headers, table = col.dimension(**kwargs)
                info['headers'] = headers
                info['table'] = table
            except (ValueError,NotImplementedError) as errmsg:
                flash(Markup(errmsg), "error")
                info['error'] = True
    return

def render_collection_page(col, args, bread):
    mbs = col.members()
    forms = [ (k, [(f.name(), f.degree_of_field()) for f in mbs if k == f.weight()]) for k in Set(f.weight() for f in mbs)]
    info = { 'col': col, 'forms': forms, 'args': to_dict(args) }
    #info['learnmore'] += [ ('The spaces $'+col.latex_name()+'$', col.name()+'/basic')]
    if col.computes_dimensions():
        build_dimension_table (info, col, args)
    bread.append(('$'+col.latex_name()+'$', ''))
    return render_template("ModularForm_GSp4_Q_collection.html",
                           title='Siegel modular forms $'+col.latex_name()+'$',
                           bread=bread,
                           info=info)

def render_search_results_page(args, bread):
    if args.get("table"):
        return render_dimension_table_page(args, bread)
    if args.get("lookup"):
        return redirect(url_for('.by_label',label=args['label']))
    info = { 'args': to_dict(args) }
    query = {}
    try:
        parse_ints (info['args'], query, 'deg', 'degree')
        parse_ints (info['args'], query, 'wt', '$k$')
        parse_ints (info['args'], query, 'fdeg', 'field degree')
    except ValueError:
        info['error'] = True
    if not info.get('error'):
        print query
        info['results'] = sample.Samples(query)
    bread.append( ('search results', ''))
    return render_template( "ModularForm_GSp4_Q_search_results.html",
                           title='Siegel modular forms search results',
                           bread=bread,
                           info=info)

def render_dimension_table_page(args, bread):
    cols = scan_collections()
    col_list = [cols[c] for c in cols if cols[c].computes_dimensions()]
    col_list.sort(key=lambda x: x.order)
    info = { 'col_list': col_list, 'args': to_dict(args) }
    col = cols.get(args.get('col'))
    if col and col.computes_dimensions():
        info['col'] = col
        build_dimension_table (info, col, args)
    bread.append(('dimensions', 'dimensions'))
    return render_template("ModularForm_GSp4_Q_dimensions.html",
                            title='Siegel modular forms dimension tables',
                            bread=bread,
                            info=info)

def render_sample_page(col, sam, args, bread):
    info = { 'args': to_dict(args), 'sam': sam, 'latex': latex, 'type':sam.type(), 'name':sam.name(), 'full_name': sam.full_name(), 'weight':sam.weight(), 'fdeg':sam.degree_of_field(), 'is_eigenform':sam.is_eigenform(), 'field_poly': sam.field_poly()}
    if sam.is_integral() != None:
        info['is_integral'] = sam.is_integral()
    if 'Sp4Z' in sam.collection():
        info['space_url'] = url_for('.Sp4Z_j_space', k=info['weight'], j=0)
    if 'Sp4Z_2' in sam.collection():
        info['space_url'] = url_for('.Sp4Z_j_space', k=info['weight'], j=2)
    info['space'] = '$'+col.latex_name().replace('k', '{' + str(sam.weight()) + '}')+'$'
    if 'space_url' in info:
        bread.append((info['space'], info['space_url']))
    info['space_href'] = '<a href="%s">%s</d>'%(info['space_url'],info['space']) if 'space_url' in info else info['space']
    if info['field_poly'].disc() < 10**10:
        label = poly_to_field_label(info['field_poly'])
        if label:
            info['field_label'] = label
            info['field_url'] = url_for('number_fields.by_label', label=label)
            info['field_href'] = '<a href="%s">%s</a>'%(info['field_url'], field_pretty(label))
    
    bread.append((info['name'], ''))
    title='Siegel modular forms sample ' + info['full_name']
    properties = [('Space', info['space_href']),
                  ('Name', info['name']),
                  ('Type', '<br>'.join(info['type'].split(','))),
                  ('Weight', str(info['weight'])),
                  ('Hecke eigenform', str(info['is_eigenform'])),
                  ('Field degree', str(info['fdeg']))]
    try:
        evs_to_show = parse_ints_to_list_flash(args.get('ev_index'), 'list of $l$')
        fcs_to_show = parse_ints_to_list_flash(args.get('fc_det'), 'list of $\\det(F)$')
    except ValueError:
        evs_to_show = []
        fcs_to_show = []
    info['evs_to_show'] = sorted([n for n in (evs_to_show if len(evs_to_show) else sam.available_eigenvalues()[:10])])
    info['fcs_to_show'] = sorted([n for n in (fcs_to_show if len(fcs_to_show) else sam.available_Fourier_coefficients()[1:6])])
    info['evs_avail'] = [n for n in sam.available_eigenvalues()]
    info['fcs_avail'] = [n for n in sam.available_Fourier_coefficients()]

    # Do not attempt to constuct a modulus ideal unless the field has a reasonably small discriminant
    # otherwise sage may not even be able to factor the discriminant
    info['field'] = sam.field()
    if info['field_poly'].disc() < 10**80:
        null_ideal = sam.field().ring_of_integers().ideal(0)
        info['modulus'] = null_ideal
        modulus = args.get('modulus','').replace(' ','')
        m = 0
        if modulus:
            try:
                O = sam.field().ring_of_integers()
                m = O.ideal([O(str(b)) for b in modulus.split(',')])
            except Exception as e:
                info['error'] = True
                flash(Markup("Error: unable to construct modulus ideal from specified generators <span style='color:black'>%s</span>." % modulus), "error")
            if m == 1:
                info['error'] = True
                flash(Markup("Error: the ideal <span style='color:black'>(%s)</span> is the unit ideal, please specify a different modulus." % modulus), "error")
                m = 0
        info['modulus'] = m
        # Hack to reduce polynomials and to handle non integral stuff
        def redc(c):
            return m.reduce(c*c.denominator())/m.reduce(c.denominator())
        def redp(f):
            c = f.dict()
            return f.parent()(dict((e,redc(c[e])) for e in c))
        def safe_reduce(f):
            if not m:
                return latex(f)
            try:
                if f in sam.field():
                    return latex(redc(f))
                else:
                    return latex(redp(f))
            except ZeroDivisionError:
                return '\\textrm{Unable to reduce} \\bmod\\mathfrak{m}'
        info['reduce'] = safe_reduce
    else:
        info['reduce'] = latex
        
    # check that explicit formula is not ridiculously big
    if sam.explicit_formula():
        info['explicit_formula_bytes'] = len(sam.explicit_formula())
        if len(sam.explicit_formula()) < 100000:
            info['explicit_formula'] = sam.explicit_formula()
        
    return render_template("ModularForm_GSp4_Q_sample.html",
                            title=title,
                            bread=bread,
                            properties2=properties,
                            info=info)

