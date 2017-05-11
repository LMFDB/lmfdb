# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.ecnf.WebEllipticCurve import db_ecnfstats

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
    return the_ECNFstats.sigstats().get(s,None)

def ecnf_summary():
    ecnfstats = db_ecnfstats()
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    deg_knowl = '<a knowl="nf.degree">degree</a>'
    data = ecnfstats.find_one({'_id':'conductor_norm'})
    ncurves = comma(data['ncurves'])
    nclasses = comma(data['nclasses'])
    data = ecnfstats.find_one({'_id':'field_label'})
    nfields = len(data['counts'])
    data = ecnfstats.find_one({'_id':'signatures_by_degree'})
    maxdeg = max(int(d) for d in data if d!='_id')
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' in {} '.format(nclasses),
                    iso_knowl,
                    r', over {} '.format(nfields),
                    nf_knowl, ' (not including $\mathbb{Q}$) of ',
                    deg_knowl,
                    r' up to {}.'.format(maxdeg)])

def ecnf_field_summary(field):
    data = db_ecnfstats().find_one({'_id':'conductor_norm_by_field'})[field]
    ncurves = data['ncurves']
    s = '' if ncurves==1 else 's'
    ec_knowl = '<a knowl="ec">elliptic curve{}</a>'.format(s)
    nclasses = data['nclasses']
    s = '' if nclasses==1 else 'es'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny class{}</a>'.format(s)
    nf_knowl = '<a knowl="nf">number field</a>'
    max_norm = data['max_norm']
    s = '' if max_norm==1 else 's'
    cond_knowl = '<a knowl="ec.conductor">conductor{}</a>'.format(s)
    s = '' if max_norm==1 else 'up to '
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over the ',
                    nf_knowl,
                    r' {}, in {} '.format(field_pretty(field), nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm {} {}.'.format(s,data['max_norm'])])

def ecnf_signature_summary(sig):
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    r, s = [int(x) for x in sig.split(",")]
    d = r+2*s
    data = db_ecnfstats().find_one({'_id':'conductor_norm_by_signature'})[sig]
    ncurves = data['ncurves']
    nclasses = data['nclasses']
    max_norm = data['max_norm']
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of signature ({}) (degree {}), in {} '.format(sig, d, nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to {}.'.format(max_norm)])

def ecnf_degree_summary(d):
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    data = db_ecnfstats().find_one({'_id':'conductor_norm_by_degree'})[str(d)]
    ncurves = data['ncurves']
    nclasses = data['nclasses']
    max_norm = data['max_norm']
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of degree {}, in {} '.format(d, nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to {}.'.format(max_norm)])

@app.context_processor
def ctx_ecnf_summary():
    return {'ecnf_summary': ecnf_summary}

class ECNFstats(object):
    """
    Class for creating and displaying statistics for elliptic curves over number fields other than Q
    """

    def __init__(self):
        logger.debug("Constructing an instance of ECstats")
        self.ecdbstats = db_ecnfstats()
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
        ecdbstats = self.ecdbstats
        counts = {}
        fields_dict = dict(ecdbstats.find_one({'_id':'field_label'})['counts'])
        fields = sorted(fields_dict.keys(), key=sort_field)
        counts['fields'] = fields
        counts['nfields'] = len(fields)
        degrees_dict = dict(ecdbstats.find_one({'_id':'degree'})['counts'])
        degrees = sorted(degrees_dict.keys())
        counts['degrees'] = degrees
        counts['maxdeg'] = max(degrees)
        counts['ncurves_by_degree'] = degrees_dict
        counts['fields_by_degree'] = dict([(d,sorted([f for f,n in ecdbstats.find_one({'_id':'bydegree/{}/field_label'.format(d)})['counts']],key=sort_field)) for d in degrees])
        counts['nfields_by_degree'] = dict([(d,len(counts['fields_by_degree'][d])) for d in degrees])
        data = ecdbstats.find_one({'_id':'conductor_norm'})
        ncurves = data['ncurves']
        nclasses = data['nclasses']
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        self._counts  = counts
        logger.debug("... finished computing elliptic curve (nf) counts.")

    def init_ecnfdb_stats(self):
        if self._stats:
            return
        ecdbstats = self.ecdbstats
        counts = self._counts
        stats = {}
        dstats = {}
        sigstats = {}
        data_deg = ecdbstats.find_one({'_id':'conductor_norm_by_degree'})
        data_sig = ecdbstats.find_one({'_id':'conductor_norm_by_signature'})
        print("Signatures: {}".format(data_sig.keys()))
        data_field = ecdbstats.find_one({'_id':'conductor_norm_by_field'})
        for d in counts['degrees']:
            dstats[d] = data_deg[str(d)]
            fsd = stats[d] = {}
            for r in range(d%2,d+1,2):
                s = (d-r)//2
                sig_code = "%s,%s" % (r,s)
                if sig_code in data_sig:
                    sig = "(%s,%s)" % (r,s)
                    fsd[sig] = fsds = {}
                    sigstats[sig] = data_sig[sig_code]
                    sigstats[sig]['r'] = str(r)
                    print("sig = {}".format(sig))
                    print("sigstats[sig] = {}".format(sigstats[sig]))
                    data_f = ecdbstats.find_one({'_id':'bysignature/{}/field_label'.format(sig_code)})
                    for F,n in data_f['counts']:
                        fsds[F] = data_field[F.replace(".",":")]
        self._stats = stats
        self._dstats = dstats
        self._sigstats = sigstats
