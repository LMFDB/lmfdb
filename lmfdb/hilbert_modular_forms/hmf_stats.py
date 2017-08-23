# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb.base import app, getDBConnection
from lmfdb.utils import comma, make_logger
from lmfdb.WebNumberField import nf_display_knowl

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

def field_sort_key(F):
    dsdn = F.split(".")
    return (int(dsdn[0]), int(dsdn[2]))  # by degree then discriminant

logger = make_logger("hmf")

def db_forms_stats():
    return getDBConnection().hmfs.forms.search.stats

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
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_hmf_count()
        return self._counts

    def stats(self, d=None):
        self.init_hmf_stats()
        if d:
            return self._stats[str(d)]
        return self._stats

    def init_hmf_count(self):
        if self._counts:
            return
        #print("initializing HMF counts")
        counts = {}

        formstats = db_forms_stats()

        nforms = formstats.find_one({'_id':'deg'})['total']
        counts['nforms']  = nforms
        counts['nforms_c']  = comma(nforms)

        degs = formstats.find_one({'_id':'fields_summary'})
        nfields = degs['total']
        degrees = [x[0] for x in degs['counts']]
        degrees.sort()
        max_deg = max(degrees)
        counts['degrees'] = degrees = [str(d) for d in degrees]
        counts['nfields'] = nfields
        counts['nfields_c']  = comma(nfields)
        counts['maxdeg'] = max_deg
        counts['max_deg_c'] = comma(max_deg)

        fields = formstats.find_one({'_id':'fields_by_degree'})
        counts['fields_by_degree'] = dict([(d,fields[d]['fields']) for d in degrees])
        counts['nfields_by_degree'] = dict([(d,fields[d]['nfields']) for d in degrees])
        counts['max_disc_by_degree'] = dict([(d,fields[d]['maxdisc']) for d in degrees])
        self._counts  = counts
        #print("-- finished initializing HMF counts")

    def init_hmf_stats(self):
        if self._stats:
            return
        if not self._counts:
            self.init_hmf_count()
        #print("initializing HMF stats")
        deg_data = db_forms_stats().find_one({'_id':'level_norm_by_degree'})
        field_data = db_forms_stats().find_one({'_id':'level_norm_by_field'})
        def field_stats(F):
            ff = F.replace(".",":")
            return {'nforms': field_data[ff]['nforms'],
                    'maxnorm': field_data[ff]['max_norm'],
                    'field_knowl': nf_display_knowl(F, getDBConnection(), F),
                    'forms': url_for('hmf.hilbert_modular_form_render_webpage', field_label=F)
            }
        for d in self._counts['degrees']:
            #print("initializing HMF stats for degree {}".format(d))
            d = str(d)
            # NB the only reason for keeping the list of fields here
            # is that we can sort them, while the keys of stats.counts
            # are the fields in a random order
            fields = self._counts['fields_by_degree'][d]
            fields.sort(key=field_sort_key)
            self._stats[d] = {'fields': fields,
                     'nfields': len(fields),
                     'nforms': deg_data[d]['nforms'],
                     'maxnorm': deg_data[d]['max_norm'],
                     'counts': dict([(F,field_stats(F)) for F in fields])
                     }
            #print("-- finished initializing HMF stats for degree {}".format(d))

        #print("-- finished initializing HMF stats")
