# -*- coding: utf-8 -*-
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import make_logger, comma

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("rep_galois_modls")

the_rep_galois_modlstats = None

def get_stats():
    global the_rep_galois_modlstats
    if the_rep_galois_modlstats is None:
       the_rep_galois_modlstats = rep_galois_modlstats()
    return the_rep_galois_modlstats


def rep_galois_modl_summary():
    counts = get_stats().counts()
    return r"<p>The database currently contains %s <a title='mod &#x2113; Galois representation'[rep_galois_modl.definition]' knowl='rep_galois_modl.definition' kwargs=''>mod &#x2113; Galois representations</a>.</p>" % (str(counts['nrep_galois_modl_c']))


@app.context_processor
def ctx_rep_galois_modl_summary():
    return {'rep_galois_modl_summary': rep_galois_modl_summary}

class rep_galois_modlstats(object):
    """
    Class for creating and displaying statistics for integral rep_galois_modls
    """

    def __init__(self):
        logger.debug("Constructing an instance of rep_galois_modlstats")
        self.rep_galois_modl = lmfdb.base.getDBConnection().mod_l_galois.reps
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_rep_galois_modl_count()
        return self._counts

    def stats(self):
        self.init_rep_galois_modl_count()
        self.init_rep_galois_modl_stats()
        return self._stats

    def init_rep_galois_modl_count(self):
        if self._counts:
            return
        logger.debug("Computing rep_galois_modl counts...")
        rep_galois_modl = self.rep_galois_modl
        counts = {}
        nrep_galois_modl = rep_galois_modl.count()
        counts['nrep_galois_modl']  = nrep_galois_modl
        counts['nrep_galois_modl_c']  = comma(nrep_galois_modl)
        self._counts  = counts
        logger.debug("... finished computing rep_galois_modl counts.")
