# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from flask import url_for

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

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
        self.init_ecdb_count()
        self.init_ecdb_stats()
        return self._stats

    def init_ecnfdb_count(self):
        if self._counts:
            return
        logger.debug("Computing elliptic curve (nf) counts...")
        ecdb = self.ecdb
        counts = {}
        fields = ecdb.distinct('field_label')
        counts['nfields'] = len(fields)
        degrees = ecdb.distinct('degree')
        counts['maxdeg'] = max(degrees)
        counts['ncurves_by_degree'] = dict([(d,ecdb.find({'degree':d}).count()) for d in degrees])
        ncurves = ecdb.count()
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = ecdb.find({'number': 1}).count()
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        self._counts  = counts
        logger.debug("... finished computing elliptic curve (nf) counts.")

    def init_ecdb_stats(self):
        if self._stats:
            return
        logger.debug("Computing elliptic curve stats...")
        ecdb = self.ecdb
        counts = self._counts
        stats = {}
        rank_counts = []
        for r in range(counts['max_rank']+1):
            ncu = ecdb.find({'rank': r}).count()
            ncl = ecdb.find({'rank': r, 'number': 1}).count()
            prop = format_percentage(ncl,counts['nclasses'])
            rank_counts.append({'r': r, 'ncurves': ncu, 'nclasses': ncl, 'prop': prop})
        stats['rank_counts'] = rank_counts
        tor_counts = []
        tor_counts2 = []
        ncurves = counts['ncurves']
        for t in  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16]:
            ncu = ecdb.find({'torsion': t}).count()
            if t in [4,8,12]: # two possible structures
                ncyc = ecdb.find({'torsion_structure': [str(t)]}).count()
                gp = "\(C_{%s}\)"%t
                prop = format_percentage(ncyc,ncurves)
                tor_counts.append({'t': t, 'gp': gp, 'ncurves': ncyc, 'prop': prop})
                nncyc = ncu-ncyc
                gp = "\(C_{2}\\times C_{%s}\)"%(t//2)
                prop = format_percentage(nncyc,ncurves)
                tor_counts2.append({'t': t, 'gp': gp, 'ncurves': nncyc, 'prop': prop})
            elif t==16: # all C_2 x C_8
                gp = "\(C_{2}\\times C_{8}\)"
                prop = format_percentage(ncu,ncurves)
                tor_counts2.append({'t': t, 'gp': gp, 'ncurves': ncu, 'prop': prop})
            else: # all cyclic
                gp = "\(C_{%s}\)"%t
                prop = format_percentage(ncu,ncurves)
                tor_counts.append({'t': t, 'gp': gp, 'ncurves': ncu, 'prop': prop})
        stats['tor_counts'] = tor_counts+tor_counts2
        stats['max_sha'] = ecdb.find().sort('sha', DESCENDING).limit(1)[0]['sha']
        sha_counts = []
        from sage.misc.functional import isqrt
        for s in range(1,1+isqrt(stats['max_sha'])):
            s2 = s*s
            nc = ecdb.find({'sha': s2}).count()
            if nc:
                sha_counts.append({'s': s, 'ncurves': nc})
        stats['sha_counts'] = sha_counts
        self._stats = stats
        logger.debug("... finished computing elliptic curve stats.")
        #logger.debug("%s" % self._stats)

