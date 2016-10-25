# -*- coding: utf-8 -*-
from pymongo import DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import make_logger, comma

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("hecke_algebrass")

the_hecke_algebras_stats = None

def get_stats():
    global the_hecke_algebras_stats
    if the_hecke_algebras_stats is None:
       the_hecke_algebras_stats = hecke_algebrasstats()
    return the_hecke_algebras_stats


def hecke_algebras_summary():
    counts = get_stats().counts()
    return r"<p>The database currently contains %s <a title='Hecke algebras [hecke_algebra.definition]' knowl='hecke_algebra.definition' kwargs=''>Hecke algebras</a>. <br>The largest  <a title='level [mf.elliptic.level]' knowl='mf.elliptic.level' kwargs=''>level</a> for <a title='level [group.sl2z.subgroup.gamma0n]' knowl='group.sl2z.subgroup.gamma0n' kwargs=''>$\Gamma_0$</a> is %s, the largest <a title='weight [mf.elliptic.weight]' knowl='mf.elliptic.weight' kwargs=''>weight</a> is %s." % (str(counts['nhecke_algebras_c']), str(counts['max_level_c']), str(counts['max_weight_c']))


@app.context_processor
def ctx_hecke_algebras_summary():
    return {'hecke_algebras_summary': hecke_algebras_summary}

class hecke_algebrasstats(object):
    """
    Class for creating and displaying statistics for hecke_algebras
    """

    def __init__(self):
        logger.debug("Constructing an instance of hecke_algebrasstats")
        self.hecke_algebras = lmfdb.base.getDBConnection().mod_l_eigenvalues.hecke_algebras
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_hecke_algebras_count()
        return self._counts

    def stats(self):
        self.init_hecke_algebras_count()
        self.init_hecke_algebras_stats()
        return self._stats

    def init_hecke_algebras_count(self):
        if self._counts:
            return
        logger.debug("Computing hecke_algebras counts...")
        hecke_algebras = self.hecke_algebras
        counts = {}
        nhecke_algebras = hecke_algebras.count()
        counts['nhecke_algebras']  = nhecke_algebras
        counts['nhecke_algebras_c']  = comma(nhecke_algebras)
        max_lev = hecke_algebras.find().sort('level', DESCENDING).limit(1)[0]['level']
        counts['max_level'] = max_lev
        counts['max_level_c'] = comma(max_lev)
        max_wt = hecke_algebras.find().sort('weight', DESCENDING).limit(1)[0]['weight']
        counts['max_weight'] = max_wt
        counts['max_weight_c'] = comma(max_wt)
        self._counts  = counts
        logger.debug("... finished computing hecke_algebras counts.")
