# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
from flask import url_for
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.ecnf.ecnf_stats import field_data, sort_field
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

logger = make_logger("hmf")

the_HMFstats = None

def get_counts():
    global the_HMFstats
    if the_HMFstats is None:
        the_HMFstats = HMFstats()
    return the_HMFstats.counts()

def get_stats(d=None):
    global the_HMFstats
    if the_HMFstats is None:
        the_HMFstats = HMFstats()
    return the_HMFstats.stats(d)

def hmf_summary():
    counts = get_stats().counts()
    hmf_knowl = '<a knowl="mf.hilbert">Hilbert modular forms</a>'
    nf_knowl = '<a knowl="nf.totally_real">totally real number fields</a>'
    return ''.join([r'The database currently contains %s ' % counts['nforms_c'],
                    hmf_knowl,
                    r', over %s ' % counts['nfields'],
                    nf_knowl, ' (not including $\mathbb{Q}$)',
                    ' of degree up to %s' % counts['maxdeg']
                ])

@app.context_processor
def ctx_hmf_summary():
    return {'hmf_summary': hmf_summary}

def hmf_degree_summary(d):
    stats = get_stats(d)
    hmf_knowl = '<a knowl="mf.hilbert">Hilbert modular forms</a>'
    nf_knowl = '<a knowl="nf.totally_real">totally real number fields</a>'
    level_knowl = '<a knowl="mf.hilbert.level_norm">level norm</a>'
    return ''.join([r'The database currently contains %s ' % stats['nforms'],
                    hmf_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of degree %s, with ' % d,
                    level_knowl,
                    r' up to %s.' % stats['maxnorm']])

def hmf_field_summary(F):
    stats = get_stats()
    hmf_knowl = '<a knowl="mf.hilbert">Hilbert modular forms</a>'
    nf_knowl = '<a knowl="nf.totally_real">totally real number field</a>'
    level_knowl = '<a knowl="mf.hilbert.level_norm">level norm</a>'
    d = F.split(".")[0]
    return ''.join([r'The database currently contains %s ' % stats[d][F]['nforms'],
                    hmf_knowl,
                    r' defined over the totally real ',
                    nf_knowl,
                    r', with ',
                    level_knowl,
                    r' up to %s.' % stats[d][F]['maxnorm']])

class HMFstats(object):
    """
    Class for creating and displaying statistics for Hilbert modular forms
    """

    def __init__(self):
        logger.debug("Constructing an instance of HMFstats")
        self.fields = lmfdb.base.getDBConnection().hmfs.fields
        self.forms = lmfdb.base.getDBConnection().hmfs.forms
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_hmf_count()
        return self._counts

    def stats(self, d=None):
        if d:
            return self.stats_for_degree(d) # cached
        self.init_hmf_stats() # computes all
        return self._stats

    def init_hmf_count(self):
        if self._counts:
            return
        print("Computing HMF counts...")
        forms = self.forms
        fields = self.fields
        counts = {}

        nforms = forms.count()
        counts['nforms']  = nforms
        counts['nforms_c']  = comma(nforms)

        ff = fields.distinct('label')
        counts['fields'] = ff
        counts['nfields'] = nfields = len(ff)
        counts['nfields_c']  = comma(nfields)

        counts['degrees'] = degrees = fields.distinct('degree')
        counts['maxdeg'] = max_deg = max(degrees)
        counts['max_deg_c'] = comma(max_deg)

        counts['fields_by_degree'] = dict([(d,[F['label'] for F in fields.find({'degree':d},['label']).hint('degree_1')]) for d in degrees])
        counts['discs_by_degree'] = dict([(d,[F['discriminant'] for F in fields.find({'degree':d},['discriminant']).hint('degree_1')]) for d in degrees])
        counts['max_disc_by_degree'] = dict([(d,max(counts['discs_by_degree'][d])) for d in degrees])
        counts['nfields_by_degree'] = dict([(d,len(counts['fields_by_degree'][d])) for d in degrees])
        self._counts  = counts

    def init_hmf_stats(self):
        if self._stats:
            return
        if not self._counts:
            self.init_hmf_count()
        print("Computing HMF stats...")
        forms = self.forms
        fields = self.fields
        for d in self._counts['degrees']:
            self._stats[d] = self.stats_for_degree(d)

    def stats_for_degree(self, d):
        if not d in self._stats:
            forms = self.forms
            fields = self.fields
            stats = {}
            stats['fields'] = [F['label'] for F in fields.find({'degree':d},['label']).hint('degree_1')]
            field_sort_key = lambda F: int(F.split(".")[2]) # by discriminant
            stats['fields'].sort(key=field_sort_key)
            stats['nfields'] = len(stats['fields'])
            stats['nforms'] = forms.find({'deg':d}).hint('deg_1').count()
            stats['maxnorm'] = max(forms.find({'deg':d}).hint('deg_1_level_norm_1').distinct('level_norm')+[0])
            stats['counts'] = {}
            for F in stats['fields']:
                #print("Field %s" % F)
                stats['counts'][F] = self.stats_for_field(F)
            self._stats[d] = stats
        return self._stats[d]

    def stats_for_field(self, F):
        forms = self.forms
        fields = self.fields
        pipeline = [{"$match": {'field_label':F}},
                    {"$project" : { 'level_norm' : 1 }},
                    {"$group":{"_id":"level_norm", "nforms": {"$sum": 2}, "maxnorm" : {"$max": '$level_norm'}}}]
        res = forms.aggregate(pipeline).next()
        stats = {}
        stats['nforms'] = res['nforms']
        stats['maxnorm'] = res['maxnorm']
        stats['field_knowl'] = nf_display_knowl(F, lmfdb.base.getDBConnection(), field_pretty(F))
        stats['forms'] = url_for('hmf.hilbert_modular_form_render_webpage', field_label=F)
        return stats
