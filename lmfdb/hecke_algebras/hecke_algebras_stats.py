# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger, comma
from lmfdb.db_backend import db

logger = make_logger("hecke_algebras")

def hecke_algebras_summary():
    heckestats = db.hecke_algebras.stats
    hecke_knowl = '<a knowl="hecke_algebra.definition">Hecke algebras</a>'
    level_knowl = '<a knowl="mf.elliptic.level">level</a>'
    weight_knowl = '<a knowl="mf.elliptic.weight">weight</a>'
    gamma0_knowl = '<a knowl="group.sl2z.subgroup.gamma0n">$\Gamma_0$</a>'
    level_data = heckestats.get_oldstat('level')
    number = level_data['total']
    max_level = level_data['max']
    weight_data = heckestats.get_oldstat('weight')
    max_weight = weight_data['max']
    return ''.join([r'The database currently contains {} '.format(comma(number)),
                    hecke_knowl,'. The largest ', level_knowl, ' for ' , gamma0_knowl , ' is {}, '.format(comma(max_level)),
                    'the largest ', weight_knowl, ' is {}.'.format(comma(max_weight))])

@app.context_processor
def ctx_hecke_algebras_summary():
    return {'hecke_algebras_summary': hecke_algebras_summary}
