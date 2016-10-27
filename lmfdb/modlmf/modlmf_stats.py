# -*- coding: utf-8 -*-
from pymongo import DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import make_logger, comma

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("modlmfs")

the_modlmf_stats = None

def get_stats():
    global the_modlmf_stats
    if the_modlmf_stats is None:
       the_modlmf_stats = modlmf_stats()
    return the_modlmf_stats


def modlmf_summary():
    counts = get_stats().counts()
    return r"<p>The database currently contains %s <a title='mod &#x2113; modular forms [modlmf.definition]' knowl='modlmf.definition' kwargs=''>mod &#x2113; modular forms</a>. <br>The largest <a title='level [modlmf.level]' knowl='modlmf.level' kwargs=''>level</a> is %s, the largest <a title='weight [modlmf.weight]' knowl='modlmf.weight' kwargs=''>weight</a> is %s.</p>" % (str(counts['nmodlmf_c']), str(counts['max_level_c']), str(counts['max_weight_c']))


@app.context_processor
def ctx_modlmf_summary():
    return {'modlmf_summary': modlmf_summary}

class modlmf_stats(object):
    """
    Class for creating and displaying statistics for integral modlmfs
    """

    def __init__(self):
        logger.debug("Constructing an instance of modlmf_stats")
        self.modlmf = lmfdb.base.getDBConnection().mod_l_eigenvalues.modlmf
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_modlmf_count()
        return self._counts

    def stats(self):
        self.init_modlmf_count()
        self.init_modlmf_stats()
        return self._stats

    def init_modlmf_count(self):
        if self._counts:
            return
        logger.debug("Computing modlmf counts...")
        modlmf = self.modlmf
        counts = {}
        nmodlmf = modlmf.count()
        counts['nmodlmf']  = nmodlmf
        counts['nmodlmf_c']  = comma(nmodlmf)
        max_level = modlmf.find().sort('level', DESCENDING).limit(1)[0]['level']
        counts['max_level'] = max_level
        counts['max_level_c'] = comma(max_level)
        max_weight = modlmf.find().sort('min_weight', DESCENDING).limit(1)[0]['min_weight']
        counts['max_weight'] = max_weight
        counts['max_weight_c'] = comma(max_weight)
        self._counts  = counts
        logger.debug("... finished computing modlmf counts.")
