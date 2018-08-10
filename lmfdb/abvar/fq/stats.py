# -*- coding: utf-8 -*-
from lmfdb.db_backend import db
from lmfdb.utils import comma, make_logger
from sage.structure.unique_representation import UniqueRepresentation
from sage.misc.lazy_attribute import lazy_attribute

logger = make_logger("abvarfq")

class AbvarFqStats(UniqueRepresentation):
    def __init__(self):
        logger.debug("Constructing AbvarFqStats")

    @lazy_attribute
    def _counts(self):
        logger.debug("Looking up abelian variety counts")
        D = {}
        for q, L in db.av_fqisog.stats.get_oldstat('counts').iteritems():
            D[int(q)] = L
        return D

    @lazy_attribute
    def qs(self):
        return sorted(self._counts.keys())

    @lazy_attribute
    def gs(self):
        maxg = max(len(L)-1 for L in self._counts.values())
        return range(1, maxg+1)

    @lazy_attribute
    def counts(self):
        counts = {}
        counts['nclasses'] = ncurves = sum(sum(L) for L in self._counts.itervalues())
        counts['nclasses_c'] = comma(ncurves)
        counts['gs'] = self.gs
        counts['qs'] = qs = self.qs
        counts['qg_count'] = {}
        for q in qs:
            counts['qg_count'][q] = {}
            L = self._counts[q]
            for g in xrange(1,self.maxg[None]+1):
                if g < len(L):
                    counts['qg_count'][q][g] = L[g]
                else:
                    counts['qg_count'][q][g] = 0
        return counts

    @lazy_attribute
    def maxq(self):
        return {g: max(q for q in self.qs if len(self._counts[q]) > g) for g in self.gs}

    @lazy_attribute
    def maxg(self):
        maxg = {q: len(self._counts[q]) - 1 for q in self.qs}
        # maxg[None] used in decomposition search
        maxg[None] = max(self.gs)
        return maxg
