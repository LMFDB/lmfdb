# -*- coding: utf-8 -*-
from lmfdb.base import app, getDBConnection
from lmfdb.utils import make_logger, comma

logger = make_logger("lattice")

def db_latstats():
    return getDBConnection().Lattices.lat.stats

def lattice_summary():
    latstats = db_latstats()

    integral = '<a knowl="lattice.definition">integral lattices</a>'
    positivedef = '<a knowl="lattice.postive_definite">postive definite</a>'
    catalogue = '<a knowl="lattice.catalogue_of_lattices">Catalogue of Lattices</a>'
    cn = '<a knowl="lattice.class_number">class number</a>'
    dim = '<a knowl="lattice.dimension">dimension</a>'
    det = '<a knowl="lattice.determinant">determinant</a>'
    pri = '<a knowl="lattice.primitive">primitive</a>'
    cn_data = latstats.find_one('class_number')
    number = cn_data['total']
    max_cn = cn_data['max']
    dim_data = latstats.find_one('dim')
    max_dim = dim_data['max']
    det_data = latstats.find_one('det')
    max_det = det_data['max']

    return ''.join([r'<p>The database currently contains {} '.format(comma(number)), positivedef,' ', integral,'. It includes data from the ', catalogue,
                    '.</p><p>The largest ', cn , ' is {}, '.format(comma(max_cn)), ' the largest ', dim, ' is {}, '.format(comma(max_dim)),
                    'and the largest ', det, ' is {}.</p> '.format(comma(max_det)),'<p>In the case of ', pri ,' ', integral, ' of ', cn, ' one the database is complete.</p>'])

@app.context_processor
def ctx_lattice_summary():
    return {'lattice_summary': lattice_summary}
