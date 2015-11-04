# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
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
        counts['max_det'] = max_det
	max_class_number = lattice.find().sort('class_number', DESCENDING).limit(1)[0]['class_number']
        counts['max_class_number'] = max_class_number
        self._counts  = counts
        logger.debug("... finished computing Lattice counts.")
        #logger.debug("%s" % self._counts)
