# -*- coding: utf-8 -*-
from collections import defaultdict
from lmfdb import db
from lmfdb.utils import comma, StatsDisplay
from lmfdb.logger import make_logger
from sage.misc.lazy_attribute import lazy_attribute

logger = make_logger("abvarfq")

class AbvarFqStats(StatsDisplay):
    @lazy_attribute
    def _counts(self):
        return db.av_fqisog.stats.column_counts(['g', 'q'])

    @lazy_attribute
    def qs(self):
        return sorted(set(q for g,q in self._counts))

    @lazy_attribute
    def gs(self):
        return sorted(set(g for g,q in self._counts))

    @lazy_attribute
    def counts(self):
        counts = {}
        counts['nclasses'] = ncurves = sum(sum(L) for L in self._counts.itervalues())
        counts['nclasses_c'] = comma(ncurves)
        counts['gs'] = self.gs
        counts['qs'] = self.qs
        counts['qg_count'] = defaultdict(lambda: defaultdict(int))
        for (g,q), cnt in self._counts.items():
            counts['qg_count'][q][g] = cnt
        return counts

    @lazy_attribute
    def maxq(self):
        return {g: max(q for gg,q in self._counts if g==gg) for g in self.gs}

    @lazy_attribute
    def maxg(self):
        maxg = {q: max(g for g,qq in self._counts if q==qq) for q in self.qs}
        # maxg[None] used in decomposition search
        maxg[None] = max(self.gs)
        return maxg
