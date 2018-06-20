# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import comma, make_logger, format_percentage
from lmfdb.db_backend import db
from flask import url_for

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
        ecdbstats = db.ec_curves.stats
        counts = {}
        rankstats = ecdbstats.get_oldstat('rank')
        ncurves = rankstats['total']
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = ecdbstats.get_oldstat('class/rank')['total']
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        max_N = ecdbstats.get_oldstat('conductor')['max']
        # round up to nearest multiple of 1000
        max_N = 1000*((max_N/1000)+1)
        # NB while we only have the Cremona database, the upper bound
        # will always be a multiple of 1000, but it looks funny to
        # show the maximum condictor as something like 399998; there
        # are no elliptic curves whose conductor is a multiple of
        # 1000.

        counts['max_N'] = max_N
        counts['max_N_c'] = comma(max_N)
        counts['max_rank'] = int(rankstats['max'])
        self._counts  = counts
        logger.debug("... finished computing elliptic curve counts.")

    def init_ecdb_stats(self):
        if self._stats:
            return
        logger.debug("Computing elliptic curve stats...")
        ecdbstats = db.ec_curves.stats
        counts = self._counts
        stats = {}
        rank_counts = []
        rdict = dict(ecdbstats.get_oldstat('rank')['counts'])
        crdict = dict(ecdbstats.get_oldstat('class/rank')['counts'])
        for r in range(counts['max_rank']+1):
            try:
                ncu = rdict[str(r)]
                ncl = crdict[str(r)]
            except KeyError:
                ncu = rdict[r]
                ncl = crdict[r]
            prop = format_percentage(ncl,counts['nclasses'])
            rank_counts.append({'r': r, 'ncurves': ncu, 'nclasses': ncl, 'prop': prop})
        stats['rank_counts'] = rank_counts
        tor_counts = []
        tor_counts2 = []
        ncurves = counts['ncurves']
        tdict = dict(ecdbstats.get_oldstat('torsion')['counts'])
        tsdict = dict(ecdbstats.get_oldstat('torsion_structure')['counts'])
        for t in  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16]:
            try:
                ncu = tdict[t]
            except KeyError:
                ncu = tdict[str(t)]
            if t in [4,8,12]: # two possible structures
                ncyc = tsdict[str(t)]
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

        shadict = dict(ecdbstats.get_oldstat('sha')['counts'])
        stats['max_sha'] = max([int(s) for s in shadict])
        sha_counts = []
        from sage.misc.functional import isqrt
        sha_is_int = True
        try:
            nc = shadict[1]
        except KeyError:
            sha_is_int = False
        for s in range(1,1+isqrt(stats['max_sha'])):
            s2 = s*s
            if sha_is_int:
                nc = shadict.get(s2,0)
            else:
                nc = shadict.get(str(s2),0)
            if nc:
                sha_counts.append({'s': s, 'ncurves': nc})
        stats['sha_counts'] = sha_counts
        self._stats = stats
        logger.debug("... finished computing elliptic curve stats.")

