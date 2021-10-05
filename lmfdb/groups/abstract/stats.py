from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, display_knowl, StatsDisplay, proportioners, totaler, formatters
from sage.misc.lazy_attribute import lazy_attribute

def elist_formatter(elist):
    if elist == []: return "1"
    edisp = ["^{%s}" % e if e != 1 else "" for e in elist]
    return f"${''.join(p+e for (p,e) in zip('pqrsl', edisp))}$"

class GroupStats(StatsDisplay):
    extent_knowl = "rcs.cande.groups.abstract"
    table = db.gps_groups
    baseurl_func = ".index"

    knowls = {
        "exponents_of_order": "group.order",
        "abelian": "group.abelian",
    }
    short_display = {
        "exponents_of_order": "order factorization",
        "abelian": "abelian",
    }
    formatters = {
        "exponents_of_order": elist_formatter,
        "abelian": formatters.boolean,
    }
    sort_keys = {
        "exponents_of_order": lambda elist: [sum(elist)] + [-e for e in elist],
    }
    stat_list = [
        {"cols": ["abelian", "exponents_of_order"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()}
    ]

    @staticmethod
    def dynamic_parse(info, query):
        from .main import group_parse
        group_parse(info, query)

    dynamic_parent_page = "abstract-search.html"
    dynamic_cols = ["order", "exponents_of_order", "abelian"]

    @lazy_attribute
    def short_summary(self):
        return fr'The database currently contains {comma(db.gps_groups.count())} {display_knowl("group", "groups")} of {display_knowl("group.order", "order")} $n\leq {db.gps_groups.max("order")}$ together with {comma(db.gps_subgroups.count())} of their {display_knowl("group.subgroup", "subgroups")} and {comma(db.gps_char.count())} of their {display_knowl("group.representation.character", "irreducible complex characters")}.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.'# or <a href="{url_for(".dynamic_statistics")}">create your own</a>.'

    @lazy_attribute
    def summary(self):
        return fr'The database currently contains {comma(db.gps_groups.count())} {display_knowl("group", "groups")} of {display_knowl("group.order", "order")} $n\leq {db.gps_groups.max("order")}$ together with {comma(db.gps_subgroups.count())} of their {display_knowl("group.subgroup", "subgroups")} and {comma(db.gps_char.count())} of their {display_knowl("group.representation.character", "irreducible complex characters")}.' #  In addition to the statistics below, you can also <a href="{url_for(".dynamic_statistics")}">create your own</a>.'
