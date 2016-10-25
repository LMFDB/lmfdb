# -*- coding: utf-8 -*-
from pymongo import DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import make_logger, comma

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("Lattices")

the_Latticestats = None

def get_stats():
    global the_Latticestats
    if the_Latticestats is None:
       the_Latticestats = Latticestats()
    return the_Latticestats


def lattice_summary():
    counts = get_stats().counts()
    return r"<p>The database currently contains %s <a title='integral lattices [lattice.definition]' knowl='lattice.definition' kwargs=''>integral lattices</a>. It includes data from the <a title='Catalogue of Lattices [lattice.catalogue_of_lattices]' knowl='lattice.catalogue_of_lattices' kwargs=''>Catalogue of Lattices</a>.<br>The largest  <a title='Class number [lattice.class_number]' knowl='lattice.class_number' kwargs=''>class number</a> is %s, the largest <a title='dimension [lattice.dimension]' knowl='lattice.dimension' kwargs=''>dimension</a> is %s and the largest <a title='determinant [lattice.determinant]' knowl='lattice.determinant' kwargs=''>determinant</a> is %s.</br>In the case of <a title='primitive [lattice.primitive]' knowl='lattice.primitive' kwargs=''>primitive</a> <a title='integral lattices [lattice.definition]' knowl='lattice.definition' kwargs=''>integral lattices</a> of <a title='class number[lattice.class_number]' knowl='lattice.class_number' kwargs=''>class number</a> one the database is complete.</p>" % (str(counts['nlattice_c']), str(counts['max_class_number_c']), str(counts['max_dim_c']), str(counts['max_det']))


@app.context_processor
def ctx_lattice_summary():
    return {'lattice_summary': lattice_summary}

class Latticestats(object):
    """
    Class for creating and displaying statistics for integral Lattices
    """

    def __init__(self):
        logger.debug("Constructing an instance of Latticestats")
        self.lattice = lmfdb.base.getDBConnection().Lattices.lat
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_lattice_count()
        return self._counts

    def stats(self):
        self.init_lattice_count()
        self.init_lattice_stats()
        return self._stats

    def init_lattice_count(self):
        if self._counts:
            return
        logger.debug("Computing Lattice counts...")
        lattice = self.lattice
        counts = {}
        nlattice = lattice.count()
        counts['nlattice']  = nlattice
        counts['nlattice_c']  = comma(nlattice)
        max_dim = lattice.find().sort('dim', DESCENDING).limit(1)[0]['dim']
        counts['max_dim'] = max_dim
        counts['max_dim_c'] = comma(max_dim)
        max_det = lattice.find().sort('det', DESCENDING).limit(1)[0]['det']
        counts['max_det'] = comma(max_det)
        max_class_number = lattice.find().sort('class_number', DESCENDING).limit(1)[0]['class_number']
        counts['max_class_number'] = max_class_number
        counts['max_class_number_c'] = comma(max_class_number)
        self._counts  = counts
        logger.debug("... finished computing Lattice counts.")
