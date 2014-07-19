# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.utils import comma, make_logger

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("ec")

the_ECstats = None

def get_stats():
    global the_ECstats
    if the_ECstats is None:
        the_ECstats = ECstats()
    return the_ECstats

class ECstats(object):
    """
    Class for creating and displaying statistics for elliptic curves over Q
    """

    def __init__(self):
        logger.info("Constructing an instance of ECstats")
        self.ecdb = lmfdb.base.getDBConnection().elliptic_curves.curves
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_ecdb_count()
        return self._counts

    def stats(self):
        self.init_ecdb_count()
        self.init_ecdb_stats()
        return self._stats

    def init_ecdb_count(self):
        if self._counts:
            return
        logger.info("Computing elliptic curve counts...")
        ecdb = self.ecdb
        counts = {}
        ncurves = ecdb.count()
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = ecdb.find({'number': 1}).count()
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        max_N = ecdb.find().sort('conductor', DESCENDING).limit(1)[0]['conductor']
        counts['max_N'] = max_N
        counts['max_N_c'] = comma(max_N)
        counts['max_rank'] = ecdb.find().sort('rank', DESCENDING).limit(1)[0]['rank']
        self._counts  = counts
        logger.info("... finished computing elliptic curve counts.")
        #logger.info("%s" % self._counts)

    def init_ecdb_stats(self):
        if self._stats:
            return
        logger.info("Computing elliptic curve stats...")
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
        stats['max_sha'] = ecdb.find().sort('sha_an', DESCENDING).limit(1)[0]['sha_an']
        sha_counts = []
        from math import sqrt
        for s in range(1,int(sqrt(stats['max_sha']))+1):
            s2 = s*s
            nc = ecdb.find({'sha_an': { '$gt': s2-0.1, '$lt': s2+0.1}}).count()
            if nc:
                sha_counts.append({'s': s, 'ncurves': nc})
        stats['sha_counts'] = sha_counts
        self._stats = stats
        logger.info("... finished computing elliptic curve stats.")
        #logger.info("%s" % self._stats)

