# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb.db_backend import db
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.WebNumberField import nf_display_knowl
from sage.misc.cachefunc import cached_method

def field_sort_key(F):
    dsdn = F.split(".")
    return (int(dsdn[0]), int(dsdn[2]))  # by degree then discriminant

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
                    r' defined over %s ' % stats['nfields'],
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

    @cached_method
    def counts(self):
        counts = {}

        formstats = db.hmf_forms.stats

        nforms = formstats.get_oldstat('deg')['total']
        counts['nforms']  = nforms
        counts['nforms_c']  = comma(nforms)

        degs = formstats.get_oldstat('fields_summary')
        nfields = degs['total']
        degrees = [x[0] for x in degs['counts']]
        degrees.sort()
        max_deg = max(degrees)
        counts['degrees'] = degrees = [str(d) for d in degrees]
        counts['nfields'] = nfields
        counts['nfields_c']  = comma(nfields)
        counts['maxdeg'] = max_deg
        counts['max_deg_c'] = comma(max_deg)

        fields = formstats.get_oldstat('fields_by_degree')
        counts['fields_by_degree'] = dict([(d,fields[d]['fields']) for d in degrees])
        counts['nfields_by_degree'] = dict([(d,fields[d]['nfields']) for d in degrees])
        counts['max_disc_by_degree'] = dict([(d,fields[d]['maxdisc']) for d in degrees])
        return counts

    @cached_method
    def stats(self, d=None):
        if d:
            return self.stats()[str(d)]
        deg_data = db.hmf_forms.stats.get_oldstat('level_norm_by_degree')
        field_data = db.hmf_forms.stats.get_oldstat('level_norm_by_field')
        def field_stats(F):
            ff = F.replace(".",":")
            return {'nforms': field_data[ff]['nforms'],
                    'maxnorm': field_data[ff]['max_norm'],
                    'field_knowl': nf_display_knowl(F, F),
                    'forms': url_for('hmf.hilbert_modular_form_render_webpage', field_label=F)
            }
        stats = {}
        for d in self.counts()['degrees']:
            d = str(d)
            # NB the only reason for keeping the list of fields here
            # is that we can sort them, while the keys of stats.counts
            # are the fields in a random order
            fields = self.counts()['fields_by_degree'][d]
            fields.sort(key=field_sort_key)
            stats[d] = {'fields': fields,
                        'nfields': len(fields),
                        'nforms': deg_data[d]['nforms'],
                        'maxnorm': deg_data[d]['max_norm'],
                        'counts': dict([(F,field_stats(F)) for F in fields])}
        return stats
