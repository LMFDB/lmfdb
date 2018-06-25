# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.db_backend import db
from lmfdb.utils import make_logger, comma
from sage.misc.cachefunc import cached_method

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
    @cached_method
    def counts(self):
        logger.debug("Computing modlmf counts...")
        counts = {}
        nmodlmf = db.modlmf_forms.count()
        counts['nmodlmf']  = nmodlmf
        counts['nmodlmf_c']  = comma(nmodlmf)
        max_level = db.modlmf_forms.max('level')
        counts['max_level'] = max_level
        counts['max_level_c'] = comma(max_level)
        max_weight = db.modlmf_forms.max('weight_grading')
        counts['max_weight'] = max_weight
        counts['max_weight_c'] = comma(max_weight)
        logger.debug("... finished computing modlmf counts.")
        return counts

    @cached_method
    def stats(self):
        raise NotImplementedError
