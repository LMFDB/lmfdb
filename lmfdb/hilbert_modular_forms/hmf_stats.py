# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import comma
from lmfdb.logger import make_logger
from lmfdb.number_fields.web_number_field import nf_display_knowl
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
                    nf_knowl, r' (not including $\mathbb{Q}$)',
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

        nforms = db.hmf_forms.count()
        counts['nforms']  = nforms
        counts['nforms_c']  = comma(nforms)

        fields = list(db.hmf_fields.search({}, ["degree", "discriminant", "label"]))
        degrees = sorted(set(F["degree"] for F in fields))
        by_deg = {d: [F for F in fields if F["degree"] == d] for d in degrees}
        counts["degrees"] = degrees
        counts["nfields"] = len(fields)
        counts["nfields_c"] = comma(len(fields))
        counts["maxdeg"] = max(degrees)
        counts["max_deg_c"] = comma(max(degrees))
        counts["fields_by_degree"] = {d : [F["label"] for F in by_deg[d]] for d in degrees}
        counts["nfields_by_degree"] = {d : len(by_deg[d]) for d in degrees}
        counts["max_disc_by_degree"] = {d : max(F["discriminant"] for F in by_deg[d]) for d in degrees}
        return counts

    @cached_method
    def stats(self, d=None):
        if d:
            return self.stats()[d]
        nstats = db.hmf_forms.stats.numstats("level_norm", "field_label")
        counts = db.hmf_forms.stats.column_counts("field_label")
        nstats_by_deg = db.hmf_forms.stats.numstats("level_norm", "deg")
        counts_by_deg = db.hmf_forms.stats.column_counts("deg")
        C = self.counts()
        stats = {d: {"fields": C["fields_by_degree"][d],
                     "nfields": C["nfields_by_degree"][d],
                     "nforms": counts_by_deg[d],
                     "max_norm": nstats_by_deg[d]["max"],
                     "counts": {F: {"nforms": counts[F],
                                    "maxnorm": nstats[F]["max"],
                                    "field_knowl": nf_display_knowl(F, F),
                                    "forms": url_for('hmf.hilbert_modular_form_render_webpage', field_label=F)}
                                for F in C["fields_by_degree"][d]}}
                 for d in C["degrees"]}
        return stats
