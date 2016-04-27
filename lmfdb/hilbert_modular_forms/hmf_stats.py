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

def get_stats():
    global the_HMFstats
    if the_HMFstats is None:
        the_HMFstats = HMFstats()
    return the_HMFstats

def get_degree_stats(d):
    global the_HMFstats
    if the_HMFstats is None:
        the_HMFstats = HMFstats()
    return the_HMFstats.dstats()[d]

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
def ctx_hmff_summary():
    return {'hmf_summary': hmf_summary}

def hmf_degree_summary(d):
    stats = get_degree_stats(d)
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
    stats = get_dstats()
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
        self._dstats = {}

    def counts(self):
        self.init_hmf_count()
        return self._counts

    def dstats(self):
        self.init_hmf_count()
        return self._dstats

    def init_hmf_count(self):
        if self._counts:
            return
        logger.debug("Computing HMF counts...")
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

        dstats = {}
        # the hint() her tells mongo to use that index (these have
        # been created for this)
        for d in degrees:
            dstats[d] = {}
            dstats[d]['fields'] = [F['label'] for F in fields.find({'degree':d},['label']).hint('degree_1')]
            dstats[d]['nfields'] = len(dstats[d]['fields'])
            dstats[d]['nforms'] = forms.find({'deg':d}).hint('deg_1').count()
            dstats[d]['maxnorm'] = max(forms.find({'deg':d}).hint('deg_1_level_norm_1').distinct('level_norm')+[0])
            dstats[d]['counts'] = {}
            for F in dstats[d]['fields']:
                ff = forms.find({'field_label':F}, ['label', 'level_norm']).hint('field_label_1')
                fln = [f['level_norm'] for f in ff]
                dstats[d]['counts'][F] = {}
                dstats[d]['counts'][F]['nforms'] = len(fln)
                dstats[d]['counts'][F]['maxnorm'] = max(fln)
                dstats[d]['counts'][F]['field_knowl'] = nf_display_knowl(F, lmfdb.base.getDBConnection(), field_pretty(F))
                dstats[d]['counts'][F]['forms'] = url_for('hmf.hilbert_modular_form_render_webpage', field_label=F)

        self._counts  = counts
        self._dstats = dstats
        logger.debug("... finished computing HMF counts.")
        #logger.debug("%s" % self._counts)
