# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.elliptic_curves.web_ec import db_ec
from flask import url_for

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("ec")

the_ECstats = None

def get_stats():
    global the_ECstats
    if the_ECstats is None:
        the_ECstats = ECstats()
    return the_ECstats

def elliptic_curve_summary():
    counts = get_stats().counts()
    ecstaturl = url_for('ec.statistics')
    return r'The database currently contains the Cremona database of all %s <a title="Elliptic curves [ec]" knowl="ec" kwargs="">elliptic curves</a> defined over $\Q$ with <a title="Conductor of an elliptic curve over $\Q$ [ec.q.conductor]" knowl="ec.q.conductor" kwargs="">conductor</a> at most %s, all of which have <a title="Rank of an elliptic curve over $\mathbb{Q}$ [ec.q.rank]" knowl="ec.q.rank" kwargs="">rank</a> $\leq %s$.   Here are some <a href="%s">further statistics</a>.' % (str(counts['ncurves_c']), str(counts['max_N_c']), str(counts['max_rank']), ecstaturl)


@app.context_processor
def ctx_elliptic_curve_summary():
    return {'elliptic_curve_summary': elliptic_curve_summary}

class ECstats(object):
    """
    Class for creating and displaying statistics for elliptic curves over Q
    """

    def __init__(self):
        logger.debug("Constructing an instance of ECstats")
        self.ecdb = db_ec()
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
        logger.debug("Computing elliptic curve counts...")
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
        logger.debug("... finished computing elliptic curve counts.")
        #logger.debug("%s" % self._counts)

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

