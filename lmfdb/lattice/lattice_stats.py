# -*- coding: utf-8 -*-
from lmfdb.base import app, getDBConnection
from lmfdb.utils import make_logger, comma
from lmfdb.knowledge.main import render_knowl_in_template

logger = make_logger("lattice")

def db_latstats():
    return getDBConnection().Lattices.lat.stats

def lattice_summary():
    latstats = db_latstats()

    integral = '<a knowl="lattice.definition">integral lattices</a>'
    positivedef = '<a knowl="lattice.postive_definite">positive definite</a>'
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

    #Is this a summary or a completeness statement.
    #The later should be a knowl!
    text = ''.join([
        r'<p>The database currently contains {} '.format(comma(number)),
        positivedef,
        ' ',
        integral,
        '. It includes data from the ',
        catalogue,
        '.</p><p>The largest ',
        cn ,
        ' is {}, '.format(comma(max_cn)),
        ' the largest ',
        dim,
        ' is {}, '.format(comma(max_dim)),
        'and the largest ',
        det,
        ' is {}.</p> '.format(comma(max_det)),
        '<p>In the case of ',
        pri,
        ' ',
        integral,
        ' of ',
        cn,
        ' one the database is complete, by a calculation of Kirschmer and Lorch (\cite{arxiv:1208.5638}, \cite{doi:10.1112/S1461157013000107}, \cite{MR3091733}). </p>']);
    return render_knowl_in_template(text);

def lattice_summary_data():
    latstats = db_latstats()
    cn_data = latstats.find_one('class_number')
    max_cn = cn_data['max']
    dim_data = latstats.find_one('dim')
    max_dim = dim_data['max']
    det_data = latstats.find_one('det')
    max_det = det_data['max']
    return [max_cn, max_dim, max_det]

@app.context_processor
def ctx_lattice_summary():
    return {'lattice_summary': lattice_summary}
