# -*- coding: utf-8 -*-
from pymongo import ASCENDING, DESCENDING
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from flask import url_for
from lmfdb.elliptic_curves.ec_stats import format_percentage
from sage.structure.unique_representation import UniqueRepresentation
from sage.misc.lazy_attribute import lazy_attribute

logger = make_logger("abvarfq")



class AbvarFqStats(UniqueRepresentation):
    def __init__(self):
        logger.debug("Constructing AbvarFqStats")

    @lazy_attribute
    def qs(self):
        from main import db
        avdb = db()
        return sorted(avdb.distinct('q'))

    @lazy_attribute
    def gs(self):
        from main import db
        avdb = db()
        return sorted(avdb.distinct('g'))

    @lazy_attribute
    def counts(self):
        from main import db
        logger.debug("Computing abelian variety counts")
        avdb = db()
        counts = {}
        counts['nclasses'] = ncurves = avdb.count()
        counts['nclasses_c'] = comma(ncurves)
        counts['gs'] = gs = self.gs
        counts['qs'] = qs = self.qs
        counts['qg_count'] = {}
        for q in qs:
            counts['qg_count'][q] = {}
            for g in gs:
                counts['qg_count'][q][g] = avdb.find({'g': g, 'q': q}).count()
        return counts

    @lazy_attribute
    def maxq(self):
        from main import db
        avdb = db()
        maxq = {}
        for g in self.gs:
            maxq[g] = max(avdb.find({'g': g}).distinct('q'))
        return maxq

    @lazy_attribute
    def maxg(self):
        # We assume that if (g, q) is in the database,
        # so is (g', q') whenever 1 <= g' <= g, q' <= q, q' prime power
        maxg = {}
        maxq = self.maxq
        for q in self.qs:
            for g in self.gs[1:]:
                if maxq[g] < q:
                    maxg[q] = g - 1
                    break
        # maxg[None] used in decomposition search
        maxg[None] = max(self.gs)
        return maxg
