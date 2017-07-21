# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger, comma
from lmfdb.base import getDBConnection

logger = make_logger("hecke_algebras")

the_hecke_algebras_stats = None

def db_heckestats():
    global the_hecke_algebras_stats
    if the_hecke_algebras_stats is None:
        the_hecke_algebras_stats = getDBConnection().hecke_algebras.stats
    return the_hecke_algebras_stats
    
     
def hecke_algebras_summary():
    heckestats = db_heckestats()
    hecke_knowl = '<a knowl="hecke_algebra.definition">Hecke algebras</a>'
    level_knowl = '<a knowl="mf.elliptic.level">level</a>'
    weight_knowl = '<a knowl="mf.elliptic.weight">weight</a>'
    gamma0_knowl = '<a knowl="group.sl2z.subgroup.gamma0n">$\Gamma_0$</a>'
    data = heckestats.find_one()
    return ''.join([r'The database currently contains {} '.format(comma(data['num_hecke'])),
                    hecke_knowl,'. The largest ', level_knowl, ' for ' , gamma0_knowl , ' is {}, '.format(comma(data['max_lev_hecke'])),
                    'the largest ', weight_knowl, ' is {}.'.format(comma(data['max_weight_hecke']))])    
                    
@app.context_processor
def ctx_hecke_algebras_summary():
    return {'hecke_algebras_summary': hecke_algebras_summary}
