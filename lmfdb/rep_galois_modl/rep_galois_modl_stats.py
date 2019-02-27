# -*- coding: utf-8 -*-
from lmfdb.db_backend import db
from lmfdb.base import app
from lmfdb.utils import make_logger, comma
from sage.misc.cachefunc import cached_method

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
    @cached_method
    def counts(self):
        logger.debug("Computing rep_galois_modl counts...")
        counts = {}
        nrep_galois_modl = db.modlgal_reps.count()
        counts['nrep_galois_modl']  = nrep_galois_modl
        counts['nrep_galois_modl_c']  = comma(nrep_galois_modl)
        logger.debug("... finished computing rep_galois_modl counts.")
        return counts

    @cached_method
    def stats(self):
        raise NotImplementedError
