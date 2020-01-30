# -*- coding: utf-8 -*-
from __future__ import print_function
from collections import defaultdict
from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, display_knowl, StatsDisplay, proportioners, totaler, range_formatter
from lmfdb.logger import make_logger
from sage.misc.lazy_attribute import lazy_attribute

logger = make_logger("abvarfq")
def yn(t):
    return "yes" if (t and t != "no") else "no"
def ynu(t):
    if t in [0, "unknown"]:
        return "unknown"
    elif t in [1, "yes"]:
        return "yes"
    elif t in [-1, "no"]:
        return "no"
    else:
        print(t)
        raise RuntimeError

class AbvarFqStats(StatsDisplay):
    extent_knowl = "rcs.cande.av.fq"
    table = db.av_fq_isog
    baseurl_func = ".abelian_varieties"
    buckets = {
        "q": ["2", "3", "4", "5-8", "9-16", "17-32", "37-64", "67-128", "131-211", "223-1024"],
        "geometric_extension_degree": ["1", "2", "3-8", "9-24", "25-64", "65-168"],
        "jacobian_count": ["0", "1", "2", "3-8", "9-16", "17-256", "257-6375"],
        "hyp_count": ["0", "1", "2", "3-8", "9-16", "17-256", "257-6375"],
        "size": ["1", "2", "3-16", "17-256", "257-12240"],
        "twist_count": ["1", "2", "3-8", "9-24", "25-64", "65-390"],
    }
    knowls = {
        "q": "ag.base_field",
        "g": "ag.dimension",
        "p_rank": "av.fq.p_rank",
        "angle_rank": "av.fq.angle_rank",
        "galois_group": "nf.galois_group",
        "size": "av.fq.isogeny_class_size",
        "geometric_extension_degree": "av.endomorphism_field",
        "jacobian_count": "av.jacobian_count",
        "hyp_count": "av.hyperelliptic_count",
        "twist_count": "av.twist",
        "max_twist_degree": "av.twist",
        "is_simple": "av.simple",
        "is_geometrically_simple": "av.geometrically_simple",
        "is_primitive": "ag.primitive",
        "has_jacobian": "ag.jacobian",
        "has_principal_polarization": "av.princ_polarizable",
    }
    top_titles = {
        "q": "base field",
        "g": "dimension",
        "p_rank": "$p$-rank",
        "galois_group": "Galois group",
        "size": "isogeny class size",
        "geometric_extension_degree": "degree of Endomorphism field",
        "jacobian_count": "number of Jacobians",
        "hyp_count": "number of hyperelliptic curves",
        "twist_count": "number of twists",
        "max_twist_degree": "maximum twist degree",
        "is_geometrically_simple": "geometrically simple",
        "is_simple": "simple",
        "is_primitive": "primitive",
        "has_jacobian": "Jacobian",
        "has_principal_polarization": "principally polarizable",
    }
    short_display = {
        "q": "q",
        "g": "g",
        "size": "size",
        "geometric_extension_degree": "End. degree",
        "jacobian_count": "# Jacobians",
        "hyp_count": "# Hyp. curves",
        "twist_count": "# twists",
        "max_twist_degree": "max twist degree",
        "is_geometrically_simple": "geom. simple",
        "is_simple": "simple",
        "is_primitive": "primitive",
        "has_jacobian": "Jacobian",
        "has_principal_polarization": "princ. polarizable",
    }
    formatters = {"is_geometrically_simple": yn,
                  "is_simple": yn,
                  "is_primitive": yn,
                  "has_jacobian": ynu,
                  "has_principal_polarization": ynu,
    }
    query_formatters = {"is_geometrically_simple": (lambda t: "geom_simple=%s" % (yn(t))),
                        "is_simple": (lambda t: "simple=%s" % (yn(t))),
                        "is_primitive": (lambda t: "primitive=%s" % (yn(t))),
                        "has_jacobian": (lambda t: "jacobian=%s" % (ynu(t))),
                        "has_principal_polarization": (lambda t: "polarizable=%s" % (ynu(t))),
                        "jacobian_count": (lambda t: "jac_cnt=%s" % range_formatter(t)),
                        "hyp_count": (lambda t: "hyp_cnt=%s" % range_formatter(t)),
    }
    stat_list = [
        {"cols": ["g", "q"],
         "proportioner": proportioners.per_total,
         "totaler": totaler()},
        {"cols": ["g", "p_rank"],
         "proportioner": proportioners.per_row_total,
         "totaler": totaler()},
        {"cols": ["g", "twist_count"],
         "proportioner": proportioners.per_row_total,
         "totaler": totaler()},
        {"cols": ["g", "max_twist_degree"],
         "proportioner": proportioners.per_row_total,
         "totaler": totaler()},
        {"cols": ["g", "geometric_extension_degree"],
         "proportioner": proportioners.per_row_total,
         "totaler": totaler()},
        {"cols": ["g", "is_geometrically_simple"],
         "constraint": {"is_simple": True},
         "proportioner": proportioners.per_row_total,
         "totaler": totaler(),
         "top_title": display_knowl("av.geometrically_simple", "geometrically simple") + " isogeny classes among those that are " + display_knowl("av.simple", "simple")},
        {"cols": ["has_principal_polarization", "q"],
         "constraint": {"g": 2},
         "buckets": {"q":["2", "3", "4", "5", "7", "8", "9", "11", "13", "16", "17", "19", "23", "25"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("av.princ_polarizable", "principally polarizable") + " abelian surfaces"},
        {"cols": ["has_jacobian", "q"],
         "constraint": {"g": 2},
         "buckets": {"q":["2", "3", "4", "5", "7", "8", "9", "11", "13", "16", "17", "19", "23", "25"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("ag.jacobian", "Jacobians") + " among isogeny classes of abelian surfaces"},
        #{"cols": ["has_jacobian", "q"],
        # "constraint": {"g": 3},
        # "buckets": {"q":["2", "3", "4", "5", "7", "8", "9", "11", "13", "16", "17", "19", "23", "25"]},
        # "proportioner": proportioners.per_col_total,
        # "top_title": display_knowl("ag.jacobian", "Jacobians") + " among isogeny classes of abelian threefolds"},
        {"cols": ["jacobian_count", "q"],
         "constraint": {"g": 2},
         "buckets": {"q":["2", "3", "4", "5", "7", "8", "9", "11", "13", "16", "17", "19", "23", "25"],
                     "jacobian_count": ["0", "1", "2", "3-8", "9-16", "17-256"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("av.jacobian_count", "Jacobian counts") + " among isogeny classes of abelian surfaces"},
        {"cols": ["jacobian_count", "q"],
         "constraint": {"g": 3},
         "buckets": {"q":["2", "3", "5"],
                     "jacobian_count": ["0", "1", "2", "3-8", "9-16", "17-256", "257-6375"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("av.jacobian_count", "Jacobian counts") + " among isogeny classes of abelian threefolds"},
        {"cols": ["hyp_count", "q"],
         "constraint": {"g": 3},
         "buckets": {"q":["2", "3", "5", "7", "9", "11", "13"],
                     "hyp_count": ["0", "1", "2", "3-8", "9-16", "17-256", "257-6375"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("av.hyperelliptic_count", "hyperelliptic Jacobian counts") + " among isogeny classes of abelian threefolds"},
        {"cols": ["is_primitive", "q"],
         "constraint": {"g": 2},
         "buckets": {"q":["4", "8", "9", "16", "25", "27", "32", "49", "64", "81", "125", "128", "243", "256", "343", "512", "625", "729", "1024"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("ag.primitive", "primitive") + " abelian surfaces"},
        {"cols": ["is_primitive", "q"],
         "constraint": {"g":3},
         "buckets": {"q":["4", "8", "9", "16", "25"]},
         "proportioner": proportioners.per_col_total,
         "top_title": display_knowl("ag.primitive", "primitive") + " abelian threefolds"},
    ]

    @staticmethod
    def dynamic_parse(info, query):
        from lmfdb.abvar.fq.main import common_parse
        common_parse(info, query)

    dynamic_parent_page = "abvarfq-refine-search.html"
    dynamic_cols = ["q", "g", "p_rank", "angle_rank", "size", "geometric_extension_degree", "jacobian_count", "hyp_count", "twist_count", "max_twist_degree", "is_simple", "is_geometrically_simple", "is_primitive", "has_jacobian", "has_principal_polarization", "jacobian_count", "hyp_count"]

    @lazy_attribute
    def _counts(self):
        return db.av_fq_isog.stats.column_counts(["g", "q"])

    @lazy_attribute
    def qs(self):
        return sorted(set(q for g, q in self._counts))

    @lazy_attribute
    def gs(self):
        return sorted(set(g for g, q in self._counts))

    @lazy_attribute
    def isogeny_knowl(self):
        return display_knowl("av.isogeny_class", "isogeny classes")

    @lazy_attribute
    def abvar_knowl(self):
        return display_knowl("ag.abelian_variety", "abelian varieties")

    @lazy_attribute
    def short_summary(self):
        return r"The database currently contains %s %s of %s of dimension up to %s over finite fields." % (
            self.counts["nclasses_c"],
            self.isogeny_knowl,
            self.abvar_knowl,
            max(self.gs),
        )

    @lazy_attribute
    def summary(self):
        return r"The database currently contains %s %s of %s of dimension up to %s over finite fields.  In addition to the statistics below, you can also <a href='%s'>create your own</a>." % (
            self.counts["nclasses_c"],
            self.isogeny_knowl,
            self.abvar_knowl,
            max(self.gs),
            url_for("abvarfq.dynamic_statistics"),
        )

    @lazy_attribute
    def counts(self):
        counts = {}
        counts["nclasses"] = ncurves = sum(self._counts.values())
        counts["nclasses_c"] = comma(ncurves)
        counts["gs"] = self.gs
        counts["qs"] = self.qs
        counts["qg_count"] = defaultdict(lambda: defaultdict(int))
        for (g, q), cnt in self._counts.items():
            counts["qg_count"][q][g] = cnt
        return counts

    @lazy_attribute
    def maxq(self):
        return {g: max(q for gg, q in self._counts if g == gg) for g in self.gs}

    @lazy_attribute
    def maxg(self):
        maxg = {q: max(g for g, qq in self._counts if q == qq) for q in self.qs}
        # maxg[None] used in decomposition search
        maxg[None] = max(self.gs)
        return maxg
