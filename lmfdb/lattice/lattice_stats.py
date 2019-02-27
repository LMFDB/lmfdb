# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.db_backend import db
from lmfdb.utils import make_logger, comma

logger = make_logger("lattice")

def lattice_summary():
    latstats = db.lat_lattices.stats

    integral = '<a knowl="lattice.definition">integral lattices</a>'
    positivedef = '<a knowl="lattice.postive_definite">positive definite</a>'
    catalogue = '<a knowl="lattice.catalogue_of_lattices">Catalogue of Lattices</a>'
    cn = '<a knowl="lattice.class_number">class number</a>'
    dim = '<a knowl="lattice.dimension">dimension</a>'
    det = '<a knowl="lattice.determinant">determinant</a>'
    pri = '<a knowl="lattice.primitive">primitive</a>'
    cn_data = latstats.get_oldstat('class_number')
    number = cn_data['total']
    max_cn = cn_data['max']
    dim_data = latstats.get_oldstat('dim')
    max_dim = dim_data['max']
    det_data = latstats.get_oldstat('det')
    max_det = det_data['max']

    return ''.join([r'<p>The database currently contains {} '.format(comma(number)), positivedef,' ', integral,'. It includes data from the ', catalogue,
                    '.</p><p>The largest ', cn , ' is {}, '.format(comma(max_cn)), ' the largest ', dim, ' is {}, '.format(comma(max_dim)),
                    'and the largest ', det, ' is {}.</p> '.format(comma(max_det)),'<p>In the case of ', pri ,' ', integral, ' of ', cn, ' one the database is complete.</p>'])

def lattice_summary_data():
    latstats = db.lat_lattices.stats
    cn_data = latstats.get_oldstat('class_number')
    max_cn = cn_data['max']
    dim_data = latstats.get_oldstat('dim')
    max_dim = dim_data['max']
    det_data = latstats.get_oldstat('det')
    max_det = det_data['max']
    return [max_cn, max_dim, max_det]

@app.context_processor
def ctx_lattice_summary():
    return {'lattice_summary': lattice_summary}
