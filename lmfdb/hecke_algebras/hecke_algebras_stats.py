# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.utils import comma
from lmfdb.logger import make_logger
from lmfdb import db

logger = make_logger("hecke_algebras")

def hecke_algebras_summary():
    hecke_knowl = '<a knowl="hecke_algebra.definition">Hecke algebras</a>'
    level_knowl = '<a knowl="cmf.level">level</a>'
    weight_knowl = '<a knowl="cmf.weight">weight</a>'
    gamma0_knowl = r'<a knowl="group.sl2z.subgroup.gamma0n">$\Gamma_0$</a>'
    number = db.hecke_algebras.count()
    max_level = db.hecke_algebras.max('level')
    max_weight = db.hecke_algebras.max('weight')
    return ''.join([r'The database currently contains {} '.format(comma(number)),
                    hecke_knowl,'. The largest ', level_knowl, ' for ', gamma0_knowl, ' is {}, '.format(comma(max_level)),
                    'the largest ', weight_knowl, ' is {}.'.format(comma(max_weight))])

@app.context_processor
def ctx_hecke_algebras_summary():
    return {'hecke_algebras_summary': hecke_algebras_summary}
