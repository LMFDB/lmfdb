# -*- coding: utf-8 -*-
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from flask import render_template, url_for, request, send_file
from lmfdb.search_parsing import parse_range
# import siegel_core
import input_parser
import dimensions
import pickle
import urllib
from sage.all_cmdline import *
import os
import sample
import lmfdb.base
from lmfdb.base import app
from lmfdb.siegel_modular_forms import smf_page
from lmfdb.siegel_modular_forms import smf_logger
import json
import StringIO

from flask import flash, redirect


DATA = 'http://data.countnumber.de/Siegel-Modular-Forms/'
COLNS = None
DB = None


def rescan_collection():
    """
    Create and cache the instances of Collection.
    """
    from collection import Collection
    colns = dict()
    root = os.path.dirname( os.path.abspath(__file__))
    static = os.path.join( root, 'static')
    for a,b,files in os.walk( static):
        for f in files:
            try:
                if f.endswith('.json'):
                    c = f[:-5]
#                    print c
                colns[c] = Collection( c, location = static)
            except Exception as e:
                print str(e)
                pass
    global COLNS
    COLNS = colns

@app.route('/ModularForm/GSp/Q/Sp4Z_j/<j>/<k>')
@app.route('/ModularForm/GSp/Q/Sp4Z_j/<j>/<k>/')
def ModularForm_GSp4_Q_Sp4Z_j_space(j=4, k=4):
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('ModularForm_GSp4_Q_top_level')),
             ('$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z})$', '/ModularForm/GSp/Q/Sp4Z_j'),
             ('$M_{%s, %s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k,j), '/ModularForm/GSp/Q/Sp4Z_j/%s/%s'%(k,j))]
    # How to handle space decomposition: dict with keys and entries.
    #Then special case code here.
    j=int(j)
    k=int(k)
    samples =[]
    #TODO: cleanup
    if j==0:
        t= dimensions._dimension_Sp4Z([k])
        samples = find_samples('Sp4Z', k)
    elif j==2:
        t= dimensions._dimension_Sp4Z([k])
        samples = find_samples('Sp4Z_2', k)
    else:
        t = dimensions._dimension_Gamma_2([k], j, group="Sp4(Z)")
        #Right now no samples
    subdecomp=t[1][k]
    headers=t[0]
    #Same for samples. Really should have a big structure driving template: TODO
    return render_template('ModularForm_GSp4_Q_full_level_space.html',
                           title = '$M_{%s, %s}(\mathrm{Sp}(4, \mathbb{Z}))$'%(k, j),
                           k=k,
                           j=j,
                           subspace=subdecomp,
                           headers=headers,
                           samples = samples,
                           bread=bread);

def find_samples(coll, weight):
    conn = lmfdb.base.getDBConnection()
    db = conn.siegel_modular_forms.samples
    slist = db.find({'collection':coll,
                         'weight':str(weight)})
    ret = []
    for res in slist:
        name = res['name']
        path = "%s.%s"%(coll,res['name'])
        url = '/ModularForm/GSp/Q/%s'%(path)
        ret.append({'url':url, 'name':name})
    return ret

@app.route('/ModularForm/GSp/Q/Sp4Z_j')
@app.route('/ModularForm/GSp/Q/Sp4Z_j/')
def ModularForm_GSp4_Q_Sp4Z_j():
    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('ModularForm_GSp4_Q_top_level')),
             ('$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$', '/ModularForm/GSp/Q/Sp4Z_j')]
    error = False
    jrange = xrange(0, 21)
    krange = xrange(10, 21)
    if request.args.get('j'):
        try:
            jr = parse_range(request.args.get('j'))
            if type(jr) is int:
                jrange = xrange(jr, jr+20+1);
            else:
                jrange = xrange(jr['$gte'], jr['$lte'])
        except:
            error="Error parsing input for j.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." 
            flash(error, "error")
            return redirect(url_for(".ModularForm_GSp4_Q_Sp4Z_j"))

    if request.args.get('k'):
        try:
            kr = parse_range(request.args.get('k'))
            if type(kr) is int:
                if kr<4:
                    kr=4
                krange = xrange(kr, kr+10+1);
            else:
                if kr['$gte']<4:
                    kr['$gte']=4
                krange = xrange(kr['$gte'], kr['$lte'])
        except:
            error="Error parsing input for k.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." 
            flash(error, "error")
            return redirect(url_for(".ModularForm_GSp4_Q_Sp4Z_j"))
    jrange = [x for x in jrange if x%2==0]
    try:
        dimtable = dimensions.dimension_table_Sp4Z_j(krange, jrange)
    except:
        error='Not all dimensions are implemented at the moment. Try again with a different range'
        dimtable=False
    return render_template('ModularForm_GSp4_Q_Sp4Zj.html',
                           title='$M_{k,j}(\mathrm{Sp}(4, \mathbb{Z}))$',
                           bread = bread,
                           dimtable = dimtable,
                           jrange=jrange,
                           krange=krange,
                           error=error)
                    

@app.route('/ModularForm/GSp/Q')
@app.route('/ModularForm/GSp/Q/')
@app.route('/ModularForm/GSp/Q/<page>')
@app.route('/ModularForm/GSp/Q/<page>/')
def ModularForm_GSp4_Q_top_level( page = None):

    if request.args.get('empty_cache') or not COLNS:
        # we trigger a (re)scan for available collections
        rescan_collection()

    bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
             ('Siegel modular forms', url_for('ModularForm_GSp4_Q_top_level'))]

    # info = dict(args); info['args'] =  request.args
    #info['learnmore'] = []
    
    # parse the request
    if not page:
        name = request.args.get( 'download')
        if name:
            a,b = name.split('.')
            f = StringIO.StringIO( sample.export( a, b))
#            print f.getvalue()
            f.seek(0)
            return send_file( f,
                              attachment_filename = name + '.json',
                              as_attachment = True)
        
        else:
            return prepare_main_page( bread)
    if page in COLNS:
        return prepare_collection_page( COLNS[page], request.args, bread)
    if 'dimensions' == page:
        return prepare_dimension_page( request.args, bread)
    if 'search_results' == page:
        return prepare_search_results_page( request.args, bread)
    # check whether there is a sample called page
    try:
        a,b=page.split('.')
    except:
        a=b=None
    sam = sample.Samples( { 'collection': a, 'name': b})
    if len( sam) > 0:
        return prepare_sample_page( sam[0], request.args, bread)

    # return an error: better emit a 500    
    info = { 'error': 'Requested page does not exist' }
    return render_template("None.html", **info)



##########################################################
## HOME PAGE OF SIEGEL MODULAR FORMS
##########################################################
def prepare_main_page( bread):
    info = { 'number_of_collections': len(COLNS),
             'number_of_samples': len(sample.Samples( {})),
             'cols': COLNS.values(),
             'cols_with_forms': [COLNS[c] for c in COLNS if len(COLNS[c].members()) > 0],
             'cols_comp_dims': [COLNS[c] for c in COLNS if COLNS[c].computes_dimensions()]
             }
    return render_template( 'ModularForm_GSp4_Q_index.html',
                            title='Siegel Modular Forms',
                            bread=bread,
                            **info)



##########################################################
## SPECIFIC COLLECTION REQUEST
##########################################################
def prepare_collection_page( col, args, bread):
    #info['learnmore'] += [ ('The spaces $'+col.latex_name()+'$', col.name()+'/basic')]

    mbs = col.members()
    info = { 'col': col,
             'forms': [ (k,
                         [(f.name(), f.field().degree())
                          for f in mbs if k == f.weight()])
                        for k in Set( f.weight() for f in mbs)],
             }
    dim_args = args.get( 'dim_args')
    if not dim_args:
        dim_args = col.dim_args_default
#    print dim_args
    if dim_args:
        try:
            dim_args = eval( dim_args)
            header, table = col.dimension( *dim_args)
            info.update({ 'col': col,
                          'dimensions': table,
                          'table_headers': header,
                          'dim_args': dim_args
                          })
        except Exception as e:
            info.update( {'error': str(e)})            
    bread.append( ('$'+col.latex_name()+'$', col.name()))
    return render_template("ModularForm_GSp4_Q_collection.html",
                           title='Siegel modular forms $'+col.latex_name()+'$',
                           bread=bread, **info)



##########################################################
## DIMENSIONS REQUEST
##########################################################
def prepare_dimension_page( args, bread):

    info = { 'cols_comp_dims': [COLNS[c] for c in COLNS if COLNS[c].computes_dimensions()]}
    col_name = args.get( 'col_name')
    try:
        col = COLNS[col_name]
        dim_args = eval( args.get( 'dim_args'))
        header, table = col.dimension( *dim_args)
        info.update({ 'col': col,
                      'dimensions': table,
                      'table_headers': header,
                      'dim_args': dim_args,
                      })
    except Exception as e:
        info.update( {'error': str(e)})

    bread.append( ('dimensions', 'dimensions'))
    return render_template( "ModularForm_GSp4_Q_dimensions.html",
                            title='Siegel modular forms dimensions',
                            bread=bread, **info)



##########################################################
## SEARCH RESULTS
##########################################################
def prepare_search_results_page( args, bread):

    info = {'all':args}
    query = args.get('query')
    try:
        query = json.loads( query)
        results = sample.Samples( query)
        info.update( {'results': results})
    except Exception as e:
        info.update( {'error': '%s %s' % (str(e),query)})

    bread.append( ('search results', 'search_results'))
    return render_template( "ModularForm_GSp4_Q_search_results.html",
                            title='Siegel modular forms search results',
                            bread=bread, **info)



##########################################################
## SPECIFIC FORM REQUEST
##########################################################
def prepare_sample_page( sam, args, bread):
    info = {'sam': sam, 'latex': latex}

    
    info['evs_to_show'] = args.get( 'indices', [])
    if info['evs_to_show'] != []:
        try:
            info['evs_to_show'] = [ Integer(l) for l in info['evs_to_show'].split()]
        except Exception as e:
            info['error'] = 'list of l: %s' % str(e)
            info['evs_to_show'] = []
    if info['evs_to_show']==[]:
        info['evs_to_show']=[2,3,4,5,7,9,11,13,17,19]

    info['fcs_to_show'] = args.get( 'dets', [])
    if info['fcs_to_show'] != []:
        try:
            info['fcs_to_show'] = [Integer(d) for d in info['fcs_to_show'].split()]
        except Exception as e:
            info['error'] = 'list of det(F): %s' % str(e)
            info['fcs_to_show'] = []
    if info['fcs_to_show']==[]:
        info['fcs_to_show']=sam.available_Fourier_coefficients()[:5]
    null_ideal = sam.field().ring_of_integers().ideal(0)
    info['ideal_l'] = args.get( 'modulus', null_ideal)
    if info['ideal_l'] != 0:
        try:
            O = sam.field().ring_of_integers()
            id_gens = [O(str(b)) for b in info['ideal_l'].split()]
            info['ideal_l'] = O.ideal(id_gens)
        except Exception as e:
            info['error'] = 'list of generators: %s' % str(e)
            info['ideal_l'] = null_ideal

    # Hack to reduce polynomials and to handle non integral stuff
    if sam.representation() == '2':
        fun = info['ideal_l'].reduce
        def apple(x):
            try:
                return fun(x)
            except:
                try:
                    return x.parent()(dict( (i, fun( x[i])) for i in x.dict()))
                except:
                    return 'Reduction undefined'
        info['ideal_l'].reduce = apple
    info['properties2']=[('Type', "%s"%sam.type()),
                         ('Weight', "%s"%sam.weight()),
                         ('Hecke Eigenform', "%s"%sam.is_eigenform()),
                         ('Degree of Field', "%s"%sam.field().degree())]
    
    bread.append( (sam.collection()[0] + '.' + sam.name(), '/' + sam.collection()[0] + '.' + sam.name()))
    return render_template( "ModularForm_GSp4_Q_sample.html",
                            title='Siegel modular forms sample ' + sam.collection()[0] + '.'+ sam.name(),
                            bread=bread, **info)

