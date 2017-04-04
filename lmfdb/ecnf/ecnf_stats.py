# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.ecnf.WebEllipticCurve import db_ecnf

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

def get_field_stats(field):
    global the_ECNFstats
    if the_ECNFstats is None:
        the_ECNFstats = ECNFstats()
    return the_ECNFstats.stats(field)

def get_degree_stats(d):
    global the_ECNFstats
    if the_ECNFstats is None:
        the_ECNFstats = ECNFstats()
    return the_ECNFstats.dstats()[d]

def get_signature_stats(s):
    global the_ECNFstats
    if the_ECNFstats is None:
        the_ECNFstats = ECNFstats()
    return the_ECNFstats.sigstats()[s]

def ecnf_summary():
    counts = get_stats().counts()
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    deg_knowl = '<a knowl="nf.degree">degree</a>'
    return ''.join([r'The database currently contains %s ' % counts['ncurves_c'],
                    ec_knowl,
                    r' in %s ' % counts['nclasses_c'],
                    iso_knowl,
                    r', over %s ' % counts['nfields'],
                    nf_knowl, ' (not including $\mathbb{Q}$) of ',
                    deg_knowl,
                    r' up to %s.' % counts['maxdeg']])

def ecnf_field_summary(field):
    stats = get_field_stats(field)
    s = '' if stats['ncurves']==1 else 's'
    ec_knowl = '<a knowl="ec">elliptic curve%s</a>' % s
    s = '' if stats['nclasses']==1 else 'es'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny class%s</a>' % s
    nf_knowl = '<a knowl="nf">number field</a>'
    s = '' if stats['maxnorm']==1 else 's'
    cond_knowl = '<a knowl="ec.conductor">conductor%s</a>' % s
    s = '' if stats['maxnorm']==1 else 'up to '
    return ''.join([r'The database currently contains %s ' % stats['ncurves'],
                    ec_knowl,
                    r' defined over the ',
                    nf_knowl,
                    r' %s, in %s ' % (field_pretty(field), stats['nclasses']),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm %s %s.' % (s,stats['maxnorm'])])

def ecnf_signature_summary(s):
    stats = get_signature_stats(s)
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    r1, r2 = [int(r) for r in s[1:-1].split(",")]
    d = r1+2*r2
    return ''.join([r'The database currently contains %s ' % stats['ncurves'],
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of signature %s (degree %s), in %s ' % (s, d, stats['nclasses']),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to %s.' % stats['maxnorm']])

def ecnf_degree_summary(d):
    stats = get_degree_stats(d)
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    return ''.join([r'The database currently contains %s ' % stats['ncurves'],
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of degree %s, in %s ' % (d, stats['nclasses']),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to %s.' % stats['maxnorm']])

@app.context_processor
def ctx_ecnf_summary():
    return {'ecnf_summary': ecnf_summary}

class ECNFstats(object):
    """
    Class for creating and displaying statistics for elliptic curves over number fields other than Q
    """

    def __init__(self):
        logger.debug("Constructing an instance of ECstats")
        self.ecdb = db_ecnf()
        self._counts = {}
        self._stats = {}
        self._dstats = {}
        self._sigstats = {}

    def counts(self):
        self.init_ecnfdb_count()
        return self._counts

    def stats(self, field=None):
        self.init_ecnfdb_count()
        self.init_ecnfdb_stats()
        stats = self._stats
        if field == None:
            return stats
        d, r, D, i = [int(c) for c in field.split(".")]
        sig = "(%s,%s)" % (r,(int(d)-r)/2)
        return stats[d][sig][field]

    def dstats(self):
        self.init_ecnfdb_count()
        self.init_ecnfdb_stats()
        return self._dstats

    def sigstats(self):
        self.init_ecnfdb_count()
        self.init_ecnfdb_stats()
        return self._sigstats

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
        ecdb = self.ecdb
        counts = self._counts
        stats = {}
        dstats = {}
        sigstats = {}
        for d in counts['degrees']:
            dstats[d] =  {'ncurves' : ecdb.find({'degree':d}).count(),
                          'nclasses': ecdb.find({'degree':d, 'number':1}).count(),
                          'maxnorm': max(ecdb.find({'degree':d}).distinct('conductor_norm'))
                      }
            fsd = stats[d] = {}
            for r in range(d%2,d+1,2):
                sig_code = "%s.%s" % (d,r)
                xsig_code = "^%s\.%s\.*" % (d,r)
                sig = "(%s,%s)" % (r,(d-r)/2)
                fsd[sig] = fsds = {}
                sigstats[sig] = {'ncurves' : ecdb.find({'field_label':{'$regex': xsig_code}}).count(),
                                 'nclasses': ecdb.find({'field_label':{'$regex': xsig_code}, 'number':1}).count(),
                                 'maxnorm': max([0]+ecdb.find({'field_label':{'$regex': xsig_code}}).distinct('conductor_norm'))
                }
                for F in counts['fields_by_degree'][d]:
                    if F[:3]==sig_code:
                        fsds[F] = {'ncurves' : ecdb.find({'field_label':F}).count(),
                                        'nclasses': ecdb.find({'field_label':F, 'number':1}).count(),
                                        'maxnorm': max(ecdb.find({'field_label':F}).distinct('conductor_norm'))
                                    }
        self._stats = stats
        self._dstats = dstats
        self._sigstats = sigstats
