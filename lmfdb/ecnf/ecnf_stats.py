# -*- coding: utf-8 -*-
from lmfdb.app import app
from lmfdb.utils import comma, StatsDisplay
from lmfdb.logger import make_logger
from lmfdb.number_fields.number_field import field_pretty
from lmfdb import db
from sage.misc.lazy_attribute import lazy_attribute
from sage.misc.cachefunc import cached_method
from collections import defaultdict

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

class ECNF_stats(StatsDisplay):
    ec_knowls = '<a knowl="ec">elliptic curves</a>'
    ec_knowl = '<a knowl="ec">elliptic curve</a>'
    iso_knowls = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny class</a>'
    nf_knowls = '<a knowl="nf">number fields</a>'
    nf_knowl = '<a knowl="nf">number field</a>'
    deg_knowl = '<a knowl="nf.degree">degree</a>'
    cond_knowls = '<a knowl="ec.conductor">conductors</a>'
    cond_knowl = '<a knowl="ec.conductor">conductor</a>'
    @lazy_attribute
    def ncurves(self):
        return db.ec_nfcurves.count()
    @lazy_attribute
    def nclasses(self):
        return db.ec_nfcurves.count({'number':1})
    @lazy_attribute
    def field_counts(self):
        return db.ec_nfcurves.stats.column_counts('field_label')
    @lazy_attribute
    def field_classes(self):
        return db.ec_nfcurves.stats.column_counts('field_label', {'number':1})
    @lazy_attribute
    def sig_counts(self):
        return db.ec_nfcurves.stats.column_counts('signature')
    @lazy_attribute
    def sig_classes(self):
        return db.ec_nfcurves.stats.column_counts('signature', {'number':1})
    @lazy_attribute
    def deg_counts(self):
        return db.ec_nfcurves.stats.column_counts('degree')
    @lazy_attribute
    def deg_classes(self):
        return db.ec_nfcurves.stats.column_counts('degree', {'number':1})
    @lazy_attribute
    def torsion_counts(self):
        return db.ec_nfcurves.stats.column_counts('torsion_structure')
    @lazy_attribute
    def field_normstats(self):
        return db.ec_nfcurves.stats.numstats('conductor_norm', ['field_label'])
    @lazy_attribute
    def sig_normstats(self):
        return db.ec_nfcurves.stats.numstats('conductor_norm', ['signature'])
    @lazy_attribute
    def deg_normstats(self):
        return db.ec_nfcurves.stats.numstats('conductor_norm', ['degree'])
    @lazy_attribute
    def maxdeg(self):
        return db.ec_nfcurves.max('degree')
    @staticmethod
    def _get_sig(nflabel):
        d,r = map(int,nflabel.split('.',2)[:2])
        return '%s,%s'%(r,(d-r)//2)
    @staticmethod
    def _get_deg(nflabel):
        return int(nflabel.split('.',1)[0])
    def _fields_by(self, func):
        D = defaultdict(list)
        for label in self.field_counts:
            D[func(label)].append(label)
        for fields in D.values():
            fields.sort(key=sort_field)
        return D
    @lazy_attribute
    def fields_by_sig(self):
        return self._fields_by(self._get_sig)
    @lazy_attribute
    def fields_by_deg(self):
        return self._fields_by(self._get_deg)
    @lazy_attribute
    def sigs_by_deg(self):
        def _get_deg_s(sig):
            r, s = map(int, sig.split(','))
            return r + 2*s
        D = defaultdict(list)
        for sig in self.sig_counts:
            D[_get_deg_s(sig)].append(sig)
        for sigs in D.values():
            sigs.sort()
        return D

    def summary(self):
        return ''.join([r'The database currently contains {} '.format(comma(self.ncurves)),
                        self.ec_knowls,
                        r' in {} '.format(comma(self.nclasses)),
                        self.iso_knowls,
                        r', over {} '.format(len(self.field_counts)),
                        self.nf_knowls, ' (not including $\mathbb{Q}$) of ',
                        self.deg_knowl,
                        r' up to {}.'.format(self.maxdeg)])

    @cached_method
    def field_summary(self, field):
        ncurves = self.field_counts[field]
        nclasses = self.field_classes[field]
        max_norm = self.field_normstats[field]['max']
        ec_knowl = self.ec_knowl if ncurves==1 else self.ec_knowls
        iso_knowl = self.iso_knowl if ncurves==1 else self.iso_knowls
        nf_knowl = self.nf_knowl if ncurves==1 else self.nf_knowls
        cond_knowl = self.cond_knowl if ncurves==1 else self.cond_knowls
        s = '' if max_norm==1 else 'up to '
        norm_phrase = ' of norm {}{}.'.format(s, max_norm)
        return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over the ',
                    nf_knowl,
                    r' {}, in {} '.format(field_pretty(field), nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm {} {}.'.format(s,data['max_norm'])])

    @cached_method
    def signature_summary(self, sig):
        r, s = sig
        d = r+2*s
        ncurves = self.sig_counts[r,s]
        nclasses = self.sig_classes[r,s]
        max_norm = self.sig_normstats[r,s]['max']
        return ''.join([r'The database currently contains {} '.format(ncurves),
                        self.ec_knowls,
                        r' defined over ',
                        self.nf_knowls,
                        r' of signature ({},{}) (degree {}), in {} '.format(r, s, d, nclasses),
                        self.iso_knowls,
                        r', with ',
                        self.cond_knowls,
                        r' of norm up to {}.'.format(max_norm)])

    @cached_method
    def degree_summary(self, d):
        ncurves = self.deg_counts[d]
        nclasses = self.deg_classes[d]
        max_norm = self.deg_normstats[d]['max']
        return ''.join([r'The database currently contains {} '.format(ncurves),
                        self.ec_knowls,
                        r' defined over ',
                        self.nf_knowls,
                        r' of degree {}, in {} '.format(d, nclasses),
                        self.iso_knowls,
                        r', with ',
                        self.cond_knowls,
                        r' of norm up to {}.'.format(max_norm)])

@app.context_processor
def ctx_ecnf_summary():
    return {'ecnf_summary': ECNF_stats().summary}
