# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from flask import url_for

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

def field_data(s):
    r"""
    Returns full field data from field label.
    """
    deg, r1, abs_disc, n = [int(c) for c in s.split(".")]
    sig = [r1, (deg - r1) // 2]
    return [s, deg, sig, abs_disc]

def sort_field(F):
    r"""
    Returns data to sort by, from field label.
    """
    return [int(c) for c in F.split(".")]

logger = make_logger("ecnf")

the_ECNFstats = None

def get_stats():
    global the_ECNFstats
    if the_ECNFstats is None:
        the_ECNFstats = ECNFstats()
    return the_ECNFstats

def ecnf_summary():
    counts = get_stats().counts()
    #ecnfstaturl = url_for('ecnf.statistics')
    return r'The database currently contains %s elliptic curves in %s isogeny classes, over %s number fields (not including $\mathbb{Q}$) of degrees up to %s.' % (counts['ncurves_c'], counts['nclasses_c'], counts['nfields'], counts['maxdeg'])


@app.context_processor
def ctx_ecnf_summary():
    return {'ecnf_summary': ecnf_summary}

class ECNFstats(object):
    """
    Class for creating and displaying statistics for elliptic curves over number fields other than Q
    """

    def __init__(self):
        logger.debug("Constructing an instance of ECstats")
        self.ecdb = lmfdb.base.getDBConnection().elliptic_curves.nfcurves
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_ecnfdb_count()
        return self._counts

    def stats(self):
        self.init_ecnfdb_count()
        self.init_ecnfdb_stats()
        return self._stats

    def init_ecnfdb_count(self):
        if self._counts:
            return
        logger.debug("Computing elliptic curve (nf) counts...")
        ecdb = self.ecdb
        counts = {}
        fields = ecdb.distinct('field_label')
        counts['fields'] = fields
        counts['nfields'] = len(fields)
        degrees = ecdb.distinct('degree')
        counts['degrees'] = degrees
        counts['maxdeg'] = max(degrees)
        counts['ncurves_by_degree'] = dict([(d,ecdb.find({'degree':d}).count()) for d in degrees])
        counts['fields_by_degree'] = dict([(d,sorted(ecdb.find({'degree':d}).distinct('field_label'),key=sort_field)) for d in degrees])
        counts['nfields_by_degree'] = dict([(d,len(counts['fields_by_degree'][d])) for d in degrees])
        ncurves = ecdb.count()
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = ecdb.find({'number': 1}).count()
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        self._counts  = counts
        logger.debug("... finished computing elliptic curve (nf) counts.")

    def init_ecnfdb_stats(self):
        if self._stats:
            return
        logger.debug("Computing elliptic curve (nf) stats...")
        ecdb = self.ecdb
        counts = self._counts
        stats = {}
        # For each field find the max conductor norm
        stats['ncurves'] = {}
        stats['nclasses'] = {}
        stats['maxnorm'] = {}
        for d in counts['degrees']:
            stats['ncurves'][d] = {}
            stats['nclasses'][d] = {}
            stats['maxnorm'][d] = {}
            for F in counts['fields_by_degree'][d]:
                stats['ncurves'][d][F] = ecdb.find({'field_label':F}).count()
                stats['nclasses'][d][F] = ecdb.find({'field_label':F, 'number':1}).count()
                stats['maxnorm'][d][F] = max(ecdb.find({'field_label':F}).distinct('conductor_norm'))
        self._stats = stats
        logger.debug("... finished computing elliptic curve (nf) stats.")

