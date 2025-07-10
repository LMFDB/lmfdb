import re
from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, display_knowl, StatsDisplay, proportioners, totaler, formatters
from sage.misc.lazy_attribute import lazy_attribute


def elist_formatter(elist):
    if not elist:
        return "1"
    edisp = ["^{%s}" % e if e != 1 else "" for e in elist]
    return f"${''.join(p + e for p, e in zip('pqrsl', edisp))}$"


pqr_re = re.compile(r"^(1)|(p(\^\{(\d+)\})?)(q(\^\{(\d+)\})?)?(r(\^\{(\d+)\})?)?(s(\^\{(\d+)\})?)?(l(\^\{(\d+)\})?)?$")


def elist_qformatter(elist):
    if isinstance(elist, list):
        return "exponents_of_order=" + str(elist).replace(" ", "")
    M = pqr_re.fullmatch(elist.replace("$",""))
    if M is None:
        raise ValueError(elist)
    L = []
    if M.group(1) is not None: # nontrivial group
        for i in range(2, len(M.groups()), 3):
            if M.group(i) is not None:
                L.append(1 if M.group(i+1) is None else int(M.group(i+2)))
    return elist_qformatter(L)

def nilp_formatter(nilp):
    if nilp == -1:
        return "not"
    return str(nilp)

def nilp_qformatter(nilp):
    if nilp == "not":
        return "nilpotent=no"
    return f"nilpotency_class={nilp}"

stype_lookup = {
    0: "cyclic",
    1: "abelian and metacyclic, not cyclic",
    2: "abelian, not metacyclic",
    3: "nilpotent and metacyclic, not abelian",
    4: "nilpotent and metabelian, not abelian or metacyclic",
    5: "nilpotent, not metabelian",
    6: "metacyclic, not nilpotent",
    7: "metabelian and supersolvable, not nilpotent or metacyclic",
    8: "metabelian and monomial, not supersolvable",
    9: "metabelian, not monomial",
    10: "supersolvable, not nilpotent or metabelian",
    11: "monomial, not supersolvable or metabelian",
    12: "solvable, not monomial or metabelian",
    13: "not solvable",
    16: "metabelian, not supersolvable, unknown if monomial",
    17: "solvable, not metabelian, unknown if monomial",
}

stype_qlookup = {
    0: "cyclic=yes",
    1: "abelian=yes&cyclic=no&metacyclic=yes",
    2: "abelian=yes&metacyclic=no",
    3: "abelian=no&nilpotent=yes&metacyclic=yes",
    4: "abelian=no&nilpotent=yes&metacyclic=no&metabelian=yes",
    5: "nilpotent=yes&metabelian=no",
    6: "nilpotent=no&metacyclic=yes",
    7: "nilpotent=no&metacyclic=no&metabelian=yes&supersolvable=yes",
    8: "metabelian=yes&supersolvable=no&monomial=yes",
    9: "metabelian=yes&monomial=no",
    10: "nilpotent=no&metabelian=no&supersolvable=yes",
    11: "metabelian=no&supersolvable=no&monomial=yes",
    12: "metabelian=no&monomial=no&solvable=yes",
    13: "solvable=no",
    16: "metabelian=yes&supersolvable=no&monomial=unknown",
    17: "solvable=yes&metabelian=no&monomial=unknown",
}

ftype_lookup = {
    0: "$1$",
    1: "$p$",
    2: "$p^2$",
    3: "$p^{3-6}$",
    7: "$p^{7+}$",
    11: r"$pq,pqr,\ldots$", # squarefree, not trivial or prime order
    22: "$p^2q,p^2q^2$",
    31: "$p^3q,p^4q$",
    32: "$p^{3+}q^2$",
    33: "$p^{3+}q^{3+}$",
    51: "$p^{5+}q$",
    222: r"$p^{1,2}q^{1,2}r^{1,2}\cdots$", # at least three distinct prime divisors each with valuation at most 2, not squarefree
    311: r"$p^{3+}qr\cdots$", # at least three distinct prime divisors, exactly one of which has valuation at least 3
    321: "other", # at least three distinct prime divisors, not one of the previous two patterns
}

group_knowls = {
    "exponents_of_order": "group.order",
    "cyclic": "group.cyclic",
    "abelian": "group.abelian",
    "nonabelian": "group.abelian",
    "nilpotent": "group.nilpotent",
    "metacyclic": "group.metacyclic",
    "metabelian": "group.metabelian",
    "supersolvable": "group.supersolvable",
    "monomial": "group.monomial",
    "solvable": "group.solvable",
    "nilpotency_class": "group.nilpotency_class",
    "Zgroup": "group.Zgroup",
    "Agroup": "group.Agroup",
    "rank": "group.rank",
}


def stype_insert_knowls(s):
    L = re.split("(,? ?(?:(?:and)|(?:or)|(?:not))? )", s)
    for i in range(len(L)):
        if i % 2 == 0 and L[i] in group_knowls:
            L[i] = display_knowl(group_knowls[L[i]], L[i])
    return "".join(L)
stype_klookup = {stype: stype_insert_knowls(desc) for stype, desc in stype_lookup.items()}


def stype_formatter(stype):
    return stype_klookup[stype]

def stype_qformatter(stype):
    if isinstance(stype, str):
        for k, v in stype_klookup.items():
            if v == stype:
                return stype_qlookup[k]
    return stype_qlookup[stype]

def ftype_formatter(ftype):
    return ftype_lookup[ftype]
def ftype_qformatter(ftype):
    if isinstance(ftype, str) and not ftype.isdigit():
        for k, v in ftype_lookup.items():
            if v == ftype:
                ftype = k
                break
    return f"order_factorization_type={ftype}"

class GroupStats(StatsDisplay):
    extent_knowl = "rcs.cande.groups.abstract"
    table = db.gps_groups
    baseurl_func = ".index"
    buckets = {
        "aut_order": ["1-7", "8-32", "33-128", "129-512", "513-2048", "2049-8192", "8193-65536","65537-"],
        "outer_order": ["1", "2-7", "8-32", "33-128", "129-512", "513-2048", "2049-8192", "8193-65536","65537-"],
    }
    knowls = group_knowls
    short_display = {
        "exponents_of_order": "order factorization",
    }
    formatters = {
        "exponents_of_order": elist_formatter,
        "order_factorization_type": ftype_formatter,
        "abelian": formatters.yesno,
        "solvable": formatters.yesno,
        "supersolvable": formatters.yesno,
        "Zgroup": formatters.yesno,
        "cyclic": formatters.yesno,
        "nilpotency_class": nilp_formatter,
        "solvability_type": stype_formatter,
    }
    query_formatters = {
        "exponents_of_order": elist_qformatter,
        "order_factorization_type": ftype_qformatter,
        "nilpotency_class": nilp_qformatter,
        "solvability_type": stype_qformatter,
    }
    sort_keys = {
        "exponents_of_order": lambda elist: [sum(elist)] + [-e for e in elist],
    }
    stat_list = [
        {"cols": ["solvability_type", "order_factorization_type"],
         "top_title": f"Solvability as a function of {display_knowl('group.order', 'order')}",
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["nilpotency_class", "order_factorization_type"],
         "top_title": f"{display_knowl('group.nilpotent', 'nilpotency class')} as a function of {display_knowl('group.order', 'order')}",
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["rank", "order_factorization_type"],
         "top_title": f"{display_knowl('group.rank', 'rank')} as a function of {display_knowl('group.order', 'order')}",
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["derived_length", "order_factorization_type"],
         "top_title": f"{display_knowl('group.derived_series', 'derived length')} among {display_knowl('group.solvable', 'solvable')} groups as a function of {display_knowl('group.order', 'order')}",
         "constraint": {"solvable": True},
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["aut_order", "order_factorization_type"],
         "top_title": f"{display_knowl('group.automorphism', 'automorphism group order')} as a function of {display_knowl('group.order', 'order')} for {display_knowl('group.abelian', 'nonabelian')} groups",
         "constraint": {"abelian": False},
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["outer_order", "order_factorization_type"],
         "top_title": f"{display_knowl('group.outer_aut', 'outer aut. group order')} as a function of {display_knowl('group.order', 'order')} for {display_knowl('group.abelian', 'nonabelian')} groups",
         "constraint": {"abelian": False},
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
    ]

    @staticmethod
    def dynamic_parse(info, query):
        from .main import group_parse
        group_parse(info, query)

    dynamic_parent_page = "abstract-search.html"
    dynamic_cols = ["order", "order_factorization_type", "abelian"]

    @lazy_attribute
    def short_summary(self):
        return fr'The database currently contains {comma(db.gps_groups.count())} {display_knowl("group", "groups")} from {display_knowl("rcs.source.groups.abstract", "many different sources")}, the largest of which is $S_{{47}}$ of {display_knowl("group.order", "order")} $47!$.  In addition, it contains {comma(db.gps_subgroup_search.count())} of their {display_knowl("group.subgroup", "subgroups")} and {comma(db.gps_char.count())} of their {display_knowl("group.representation.character", "irreducible complex characters")}.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.'# or <a href="{url_for(".dynamic_statistics")}">create your own</a>.'

    @lazy_attribute
    def summary(self):
        return fr'The database currently contains {comma(db.gps_groups.count())} {display_knowl("group", "groups")} from {display_knowl("rcs.source.groups.abstract", "many different sources")}, the largest of which is $S_{{47}}$ of {display_knowl("group.order", "order")} $47!$.  In addition, it contains {comma(db.gps_subgroup_search.count())} of their {display_knowl("group.subgroup", "subgroups")} and {comma(db.gps_char.count())} of their {display_knowl("group.representation.character", "irreducible complex characters")}.' #  In addition to the statistics below, you can also <a href="{url_for(".dynamic_statistics")}">create your own</a>.'
