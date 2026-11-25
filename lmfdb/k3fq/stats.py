from flask import url_for
from lmfdb.utils import comma, display_knowl, StatsDisplay, proportioners, totaler
from lmfdb.utils.display_stats import NO_SEARCH_QUERY
from sage.misc.lazy_attribute import lazy_attribute
from sage.misc.cachefunc import cached_method

from .web_k3fq import isog_table


def yn(t):
    if t is None:
        return "n/a"
    return "yes" if (t and t != "no") else "no"


def ynu(t):
    if t is None:
        return "not computed"
    if t in [0, "0", "unknown"]:
        return "unknown"
    elif t in [1, "1", "yes"]:
        return "yes"
    elif t in [-1, "-1", "no"]:
        return "no"
    return str(t)


def height_format(h):
    return r"\(\infty\)" if h is None else str(h)


def height_query(h):
    return "height=%s" % ("inf" if h is None else h)


def sign_format(s):
    return "+1" if s == 1 else "-1"


BOOL_COLS = ["ej_condition", "has_nonnegative_counts", "has_count_growth", "is_pointless",
             "is_primitive", "is_ordinary", "is_supersingular", "transcendental_irreducible",
             "has_k3_newton_polygon"]

REALIZABLE_COLS = ["realizable_k3", "realizable_nck3", "realizable_cubic", "realizable_nccubic",
                   "realizable_gm", "realizable_ncgm", "realizable_verra", "realizable_ncverra",
                   "realizable_kummer"]


def _bool_query(col):
    def nullable(f):
        return lambda t: NO_SEARCH_QUERY if t is None else f(t)
    if col == "is_ordinary":
        return nullable(lambda t: "newton=%s" % ("ordinary" if t else "not_ordinary"))
    if col == "is_supersingular":
        return nullable(lambda t: "newton=%s" % ("supersingular" if t else "not_supersingular"))
    return nullable(lambda t: "%s=%s" % (col, yn(t)))


def _realizable_query(col):
    return lambda t: NO_SEARCH_QUERY if t is None else "%s=%s" % (col, ynu(t))


class K3FqStats(StatsDisplay):
    extent_knowl = "rcs.cande.k3.fq"
    table = isog_table
    baseurl_func = ".index"
    buckets = {
        "twist_count": ["1", "2", "3-4", "5-8", "9-16", "17-50", "51-"],
        "max_twist_degree": ["1", "2", "3-4", "5-8", "9-24", "25-"],
        "geometric_extension_degree": ["1", "2", "3-6", "7-12", "13-24", "25-60", "61-"],
    }
    knowls = {
        "q": "ag.base_field",
        "p": "ag.base_field",
        "r": "ag.base_field",
        "sign": "k3.fq.sign",
        "picard_rank": "k3.picard_rank",
        "geometric_picard_rank": "k3.geometric_picard_rank",
        "height": "k3.height",
        "angle_rank": "k3.fq.angle_rank",
        "angle_corank": "k3.fq.angle_rank",
        "newton_elevation": "k3.fq.newton_elevation",
        "geometric_extension_degree": "k3.fq.geometric_extension_degree",
        "twist_count": "k3.fq.twist",
        "max_twist_degree": "k3.fq.twist",
        "ej_condition": "k3.fq.ej_condition",
        "has_nonnegative_counts": "k3.fq.count_conditions",
        "has_count_growth": "k3.fq.count_conditions",
        "is_pointless": "k3.fq.point_counts",
        "is_primitive": "k3.fq.primitive",
        "is_ordinary": "k3.fq.newton_polygon",
        "is_supersingular": "k3.fq.newton_polygon",
        "transcendental_irreducible": "k3.fq.transcendental_part",
        "has_k3_newton_polygon": "k3.fq.newton_polygon",
        "num_lattices": "k3.fq.lattices",
    }
    knowls.update({col: "k3.fq.realizability" for col in REALIZABLE_COLS})
    top_titles = {
        "q": "base field",
        "p": "characteristic",
        "r": "degree of base field",
        "sign": "sign",
        "picard_rank": "Picard rank",
        "geometric_picard_rank": "geometric Picard rank",
        "height": "height",
        "angle_rank": "angle rank",
        "angle_corank": "angle corank",
        "newton_elevation": "Newton elevation",
        "geometric_extension_degree": "geometric extension degree",
        "twist_count": "number of twists",
        "max_twist_degree": "maximum twist degree",
        "ej_condition": "Artin-Tate condition",
        "has_nonnegative_counts": "nonnegative point counts",
        "has_count_growth": "point count growth",
        "is_pointless": "pointless classes",
        "is_primitive": "primitive classes",
        "is_ordinary": "ordinary classes",
        "is_supersingular": "supersingular classes",
        "transcendental_irreducible": "irreducible transcendental part",
        "has_k3_newton_polygon": "K3 Newton polygon",
        "num_lattices": "number of lattices",
        "realizable_k3": "classes containing a K3 surface",
        "realizable_nck3": "classes containing a noncommutative K3 surface",
        "realizable_cubic": "classes containing a cubic fourfold",
        "realizable_nccubic": "classes containing a noncommutative cubic fourfold",
        "realizable_gm": "classes containing a Gushel-Mukai fourfold",
        "realizable_ncgm": "classes containing a noncommutative Gushel-Mukai fourfold",
        "realizable_verra": "classes containing a Verra fourfold",
        "realizable_ncverra": "classes containing a noncommutative Verra fourfold",
        "realizable_kummer": "classes containing a Kummer surface",
    }
    short_display = {
        "q": "q",
        "p": "p",
        "r": "r",
        "sign": "sign",
        "picard_rank": "Picard rank",
        "geometric_picard_rank": "geom. Picard rank",
        "height": "height",
        "angle_rank": "angle rank",
        "angle_corank": "angle corank",
        "newton_elevation": "Newton elevation",
        "geometric_extension_degree": "geom. ext. degree",
        "twist_count": "# twists",
        "max_twist_degree": "max twist degree",
        "ej_condition": "AT condition",
        "has_nonnegative_counts": "nonneg. counts",
        "has_count_growth": "count growth",
        "is_pointless": "pointless",
        "is_primitive": "primitive",
        "is_ordinary": "ordinary",
        "is_supersingular": "supersingular",
        "transcendental_irreducible": "irred. trans. part",
        "has_k3_newton_polygon": "K3 Newton polygon",
        "num_lattices": "# lattices",
        "realizable_k3": "K3",
        "realizable_nck3": "NC K3",
        "realizable_cubic": "cubic",
        "realizable_nccubic": "NC cubic",
        "realizable_gm": "GM",
        "realizable_ncgm": "NC GM",
        "realizable_verra": "Verra",
        "realizable_ncverra": "NC Verra",
        "realizable_kummer": "Kummer",
    }
    formatters = {
        "height": height_format,
        "sign": sign_format,
    }
    formatters.update({col: yn for col in BOOL_COLS})
    formatters.update({col: ynu for col in REALIZABLE_COLS})
    query_formatters = {
        "height": height_query,
    }
    url_params = {
        "is_ordinary": ["newton"],
        "is_supersingular": ["newton"],
    }
    query_formatters.update({col: _bool_query(col) for col in BOOL_COLS})
    query_formatters.update({col: _realizable_query(col) for col in REALIZABLE_COLS})
    stat_list = [
        {"cols": ["picard_rank", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["geometric_picard_rank", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["height", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["angle_rank", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["geometric_extension_degree", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["twist_count", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["ej_condition", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["has_count_growth", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["is_pointless", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["realizable_k3", "q"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
    ]

    @staticmethod
    def dynamic_parse(info, query):
        from .main import common_parse
        common_parse(info, query)

    dynamic_parent_page = "k3fq-refine-search.html"
    dynamic_cols = ["q", "p", "r", "sign", "picard_rank", "geometric_picard_rank", "height",
                    "angle_rank", "angle_corank", "newton_elevation", "geometric_extension_degree",
                    "twist_count", "max_twist_degree", "num_lattices"] + BOOL_COLS + REALIZABLE_COLS

    @cached_method
    def _counts(self):
        return self.table.stats.column_counts(["picard_rank", "q"])

    @lazy_attribute
    def qs(self):
        return sorted({q for rho, q in self._counts()})

    @lazy_attribute
    def picard_ranks(self):
        return sorted({rho for rho, q in self._counts() if rho is not None})

    @lazy_attribute
    def nclasses(self):
        return sum(self._counts().values())

    @lazy_attribute
    def class_knowl(self):
        return display_knowl("k3.fq.motive", "classes of motives of K3 type")

    def _field_list(self):
        qs = self.qs
        if not qs:
            return "no finite fields"
        fields = [r"$\F_{%s}$" % q for q in qs]
        if len(fields) == 1:
            return fields[0]
        return ", ".join(fields[:-1]) + " and " + fields[-1]

    @lazy_attribute
    def short_summary(self):
        return r'The database currently contains %s %s over %s.  You can <a href="%s">browse further statistics</a> or <a href="%s">create your own</a>.' % (
            comma(self.nclasses),
            self.class_knowl,
            self._field_list(),
            url_for(".statistics"),
            url_for(".dynamic_statistics"),
        )

    @lazy_attribute
    def summary(self):
        return r"The database currently contains %s %s over %s.  In addition to the statistics below, you can also <a href='%s'>create your own</a>." % (
            comma(self.nclasses),
            self.class_knowl,
            self._field_list(),
            url_for("k3fq.dynamic_statistics"),
        )
