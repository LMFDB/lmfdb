# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.utils import comma, format_percentage
from lmfdb.logger import make_logger
from lmfdb import db
from sage.all import Integer

logger = make_logger("ec")

the_ECstats = None

def get_stats():
    global the_ECstats
    if the_ECstats is None:
        the_ECstats = ECstats()
    return the_ECstats

def elliptic_curve_summary():
    counts = get_stats().counts()
    return r'The database currently contains the complete Cremona database.  This contains all %s <a title="Elliptic curves [ec]" knowl="ec" kwargs="">elliptic curves</a> defined over $\Q$ with <a title="Conductor of an elliptic curve over $\Q$ [ec.q.conductor]" knowl="ec.q.conductor" kwargs="">conductor</a> at most %s.' % (str(counts['ncurves_c']), str(counts['max_N_c']))


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
        ecdb = db.ec_curves
        counts = {}
        ncurves = ecdb.count()
        nclasses = ecdb.count({'number':1})
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)

        max_N = ecdb.max('conductor')

        # round up to nearest multiple of 1000
        max_N = 1000*int((max_N/1000)+1)
        # NB while we only have the Cremona database, the upper bound
        # will always be a multiple of 1000, but it looks funny to
        # show the maximum condictor as something like 399998; there
        # are no elliptic curves whose conductor is a multiple of
        # 1000.

        counts['max_N'] = max_N
        counts['max_N_c'] = comma(max_N)
        counts['max_rank'] = ecdb.max('rank')
        self._counts  = counts
        logger.debug("... finished computing elliptic curve counts.")

    def init_ecdb_stats(self):
        if self._stats:
            return
        logger.debug("Computing elliptic curve stats...")
        ecdb = db.ec_curves
        counts = self._counts
        stats = {}

        # rank distribution
        
        rank_counts = []
        ranks = range(counts['max_rank']+1)
        for r in ranks:
            ncu = ecdb.count({'rank':r})
            ncl = ecdb.count({'rank':r, 'number':1})
            prop = format_percentage(ncl,counts['nclasses'])
            rank_counts.append({'r': r, 'ncurves': ncu, 'nclasses': ncl, 'prop': prop})
        stats['rank_counts'] = rank_counts

        # torsion distribution
        
        tor_counts = []
        tor_counts2 = []
        ncurves = counts['ncurves']
        for t in  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16]:
            ncu = ecdb.count({'torsion':t})
            if t in [4,8,12]: # two possible structures
                ncyc = ecdb.count({'torsion_structure':[t]})
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

        # Sha distribution
        
        max_sha = ecdb.max('sha')
        stats['max_sha'] = max_sha
        max_sqrt_sha = Integer(max_sha).sqrt() # exact since all sha values are squares!
        sha_counts = [{'s':s,'ncurves':ecdb.count({'sha':s**2})} for s in range(1,1+max_sqrt_sha)]
        # remove values with a count of 0
        sha_counts = [sc for sc in sha_counts if sc['ncurves']]
        stats['sha_counts'] = sha_counts
        self._stats = stats
        logger.debug("... finished computing elliptic curve stats.")

