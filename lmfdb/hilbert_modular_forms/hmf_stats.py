# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb import db
from lmfdb.utils import comma
from lmfdb.utils.display_stats import StatsDisplay, proportioners, totaler
from lmfdb.logger import make_logger
from lmfdb.number_fields.web_number_field import nf_display_knowl
from sage.misc.cachefunc import cached_method

logger = make_logger("hmf")

class HMFstats(StatsDisplay):
    """
    Class for creating and displaying statistics for Hilbert modular forms
    """
    def __init__(self):
        self.nforms = db.hmf_forms.count()

    table = db.hmf_forms
    baseurl_func = ".hilbert_modular_form_render_webpage"

    stat_list = [
        {'cols': ['level_norm', 'deg'],
         'totaler': totaler(),
         'proportioner': proportioners.per_col_total},
        {'cols': ['level_norm', 'dimension'],
         'totaler': totaler(),
         'proportioner': proportioners.per_col_total},
    ]
    buckets = {'level_norm': ['1', '2-10', '11-100', '101-1000', '1001-10000'],
               'dimension': ['1', '2', '3', '4', '5-10', '11-20', '21-100', '101-1000']}
    knowls = {'level_norm': 'mf.hilbert.level_norm',
              'dimension': 'mf.hilbert.dimension',
              'deg': 'nf.degree'}
    short_display = {'deg': 'degree'}

    @property
    def short_summary(self):
        return self.summary + "  Here are some <a href='%s'>further statistics</a>." % (url_for(".statistics"),)

    @property
    def summary(self):
        hmf_knowl = '<a knowl="mf.hilbert">Hilbert modular forms</a>'
        nf_knowl = '<a knowl="nf.totally_real">totally real number fields</a>'
        deg_knowl = '<a knowl="nf.degree">degree</a>'
        return "The database currently contains %s %s over %s %s of %s 2 to %s." % (comma(self.nforms), hmf_knowl, self.counts()["nfields"], nf_knowl, deg_knowl, self.counts()["maxdeg"])

    def degree_summary(self, d):
        stats = self.statistics(d)
        hmf_knowl = '<a knowl="mf.hilbert">Hilbert modular forms</a>'
        nf_knowl = '<a knowl="nf.totally_real">totally real number fields</a>'
        deg_knowl = '<a knowl="nf.degree">degree</a>'
        level_knowl = '<a knowl="mf.hilbert.level_norm">level norm</a>'
        return ''.join([r'The database currently contains %s ' % stats['nforms'],
                        hmf_knowl,
                        r' defined over %s ' % stats['nfields'],
                        nf_knowl,
                        r' of %s %s, with ' % (deg_knowl, d),
                        level_knowl,
                        r' up to %s.' % stats['maxnorm']])

    @cached_method
    def counts(self):
        counts = {}


        counts['nforms']  = self.nforms
        counts['nforms_c']  = comma(self.nforms)

        attrs = ["degree", "discriminant", "label"]
        fields = list(db.hmf_fields.search({}, attrs, sort=attrs))
        degrees = sorted(set(F["degree"] for F in fields))
        by_deg = {d: [F for F in fields if F["degree"] == d] for d in degrees}
        counts["degrees"] = degrees
        counts["nfields"] = len(fields)
        counts["nfields_c"] = comma(len(fields))
        counts["maxdeg"] = max(degrees)
        counts["max_deg_c"] = comma(max(degrees))
        counts["fields_by_degree"] = {d: [F["label"] for F in by_deg[d]] for d in degrees}
        counts["nfields_by_degree"] = {d: len(by_deg[d]) for d in degrees}
        counts["max_disc_by_degree"] = {d: max(F["discriminant"] for F in by_deg[d]) for d in degrees}
        return counts

    @cached_method
    def statistics(self, d=None):
        if d is not None:
            return self.statistics()[int(d)]
        nstats = db.hmf_forms.stats.numstats("level_norm", "field_label")
        counts = db.hmf_forms.stats.column_counts("field_label")
        nstats_by_deg = db.hmf_forms.stats.numstats("level_norm", "deg")
        counts_by_deg = db.hmf_forms.stats.column_counts("deg")
        C = self.counts()
        stats = {d: {"fields": C["fields_by_degree"][d],
                     "nfields": C["nfields_by_degree"][d],
                     "nforms": counts_by_deg[d],
                     "maxnorm": nstats_by_deg[d]["max"],
                     "counts": {F: {"nforms": counts[F],
                                    "maxnorm": nstats[F]["max"],
                                    "field_knowl": nf_display_knowl(F, F),
                                    "forms": lambda label: url_for('hmf.hilbert_modular_form_render_webpage', field_label=label)}
                                for F in C["fields_by_degree"][d]}}
                 for d in C["degrees"]}
        return stats

    def setup(self, attributes=None, delete=False):
        if attributes is None:
            # Per-degree statistics aren't updated by the normal setup function
            # The assert is for pyflakes
            assert self.statistics()
        super().setup(attributes, delete)
