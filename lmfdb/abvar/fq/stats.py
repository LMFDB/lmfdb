# -*- coding: utf-8 -*-
from pymongo import ASCENDING, DESCENDING
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from flask import url_for
from lmfdb.elliptic_curves.ec_stats import format_percentage
from lmfdb.main import db
from sage.structure.unique_representation import UniqueRepresentation
from sage.misc.lazy_attribute import lazy_attribute

logger = make_logger("abvarfq")



class AbvarFqStats(UniqueRepresentation):
    def __init__(self):
        logger.debug("Constructing AbvarFqStats")

    @lazy_attribute
    def counts(self):
        logger.debug("Computing abelian variety counts")
        avdb = db()
        counts = {}
        counts['nclasses'] = ncurves = avdb.count()
        counts['nclasses_c'] = comma(ncurves)
        counts['gs'] = gs = avdb.aggregate({}, {'g':'$g'})
        counts['qs'] = qs = avdb.aggregate({}, {'q':'$q'})
        counts['qg_count'] = {}
        for q in qs:
            counts['qg_count'][q] = {}
            for g in gs:
                counts['qg_count'][q][g] = avdb.find({'g': g, 'q': q}).count()
        return counts
