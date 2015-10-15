# -*- coding: utf-8 -*-
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from flask import render_template, url_for, request, send_file
# import siegel_core
import input_parser
import dimensions
import pickle
import urllib
from sage.all_cmdline import *
import os
import sample
from lmfdb.base import app
from lmfdb.siegel_modular_forms import smf_page
from lmfdb.siegel_modular_forms import smf_logger
import json
import StringIO

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
                    print c
                colns[c] = Collection( c, location = static)
            except Exception as e:
                print str(e)
                pass
    global COLNS
    COLNS = colns


@app.route('/ModularForm/GSp/Q')
@app.route('/ModularForm/GSp/Q/')
@app.route('/ModularForm/GSp/Q/<page>')
@app.route('/ModularForm/GSp/Q/<page>/')
def ModularForm_GSp4_Q_top_level( page = None):

    if request.args.get('empty_cache') or not COLNS:
        # we trigger a (re)scan for available collections
        rescan_collection()

    bread = [('Siegel modular forms', url_for('ModularForm_GSp4_Q_top_level'))]        

    # info = dict(args); info['args'] =  request.args
    #info['learnmore'] = []
    
    # parse the request
    if not page:
        name = request.args.get( 'download')
        if name:
            a,b = name.split('.')
            f = StringIO.StringIO( sample.export( a, b))
            print f.getvalue()
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
    print dim_args
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

    info['fcs_to_show'] = args.get( 'dets', [])
    if info['fcs_to_show'] != []:
        try:
            info['fcs_to_show'] = [Integer(d) for d in info['fcs_to_show'].split()]
        except Exception as e:
            info['error'] = 'list of det(F): %s' % str(e)
            info['fcs_to_show'] = []

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
        
    bread.append( (sam.collection()[0] + '.' + sam.name(), '/' + sam.collection()[0] + '.' + sam.name()))
    return render_template( "ModularForm_GSp4_Q_sample.html",
                            title='Siegel modular forms sample ' + sam.collection()[0] + '.'+ sam.name(),
                            bread=bread, **info)

