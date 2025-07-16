import re

import time
from collections import defaultdict, Counter
from flask import (
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    abort,
)
from markupsafe import Markup
#from six import BytesIO
from string import digits
from io import BytesIO
from sage.all import ZZ, latex, factor, prod, is_prime
from sage.misc.cachefunc import cached_function
from sage.databases.cremona import class_to_int

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    flash_error,
    to_dict,
    display_knowl,
    SearchArray,
    TextBox,
    SneakyTextBox,
    SneakySelectBox,
    SelectBox,
    CountBox,
    YesNoBox,
    parse_ints,
    parse_bool,
    clean_input,
    parse_regex_restricted,
    parse_bracketed_posints,
    parse_noop,
    parse_group_label_or_order,
    dispZmat,
    dispcyclomat,
    search_wrap,
    web_latex,
    pluralize,
    Downloader,
    pos_int_and_factor,
    sparse_cyclotomic_to_mathml,
    integer_to_mathml,
)
from lmfdb.utils.search_parsing import (parse_multiset, search_parser)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, CheckCol, SpacerCol, ProcessedCol, MultiProcessedCol, ColGroup
from lmfdb.api import datapage
from . import abstract_page  # , abstract_logger
from .web_groups import (
    WebAbstractCharacter,
    WebAbstractConjClass,
    WebAbstractGroup,
    WebAbstractRationalCharacter,
    WebAbstractSubgroup,
    group_names_pretty,
    label_sortkey,
    primary_to_smith,
    abelian_gp_display,
    abstract_group_display_knowl,
    cc_data_to_gp_label,
    gp_label_to_cc_data,
    missing_subs,
)
from .stats import GroupStats


abstract_group_label_regex = re.compile(r"^(\d+)\.([a-z]+|\d+)$")
abstract_subgroup_label_regex = re.compile(
    r"^(\d+)\.([a-z]+|\d+)\.(\d+)\.([a-z]+\d+|[a-z]+\d+\.[a-z]+\d+|[A-Z]+|_\.[A-Z]+)$"
)

#abstract_subgroup_label_regex = re.compile(
#    r"^(\d+)\.([a-z0-9]+)\.(\d+)\.([a-z]+\d+)(?:\.([a-z]+\d+))?(?:\.(N|M|NC\d+))?$"
#)

#abstract_subgroup_partial_regex = re.compile(
#    r"^(\d+)\.([a-z0-9]+)\.(\d+)\.([a-z]+[A-Z]+)(?:\.([a-z]+[A-Z]+))?(?:\.(N|M|NC\d+|CF\d+))?$"
#)

#abstract_subgroup_CFlabel_regex = re.compile(
#    r"^(\d+)\.([a-z0-9]+)\.(\d+)\.(CF\d+)$"
#)

#abstract_noncanonical_subgroup_label_regex = re.compile(
#    r"^(\d+)\.([a-z0-9]+)\.(\d+)\.([A-Z]+)(?:\.(N|M|NC\d+))?$"
#)


gap_group_label_regex = re.compile(r"^(\d+)\.(\d+)$")
# order_stats_regex = re.compile(r'^(\d+)(\^(\d+))?(,(\d+)\^(\d+))*')

abstract_group_hash_regex = re.compile(r"^(\d+)#(\d+)$")

def yesno(val):
    return "yes" if val else "no"

def deTeX_name(s):
    s = re.sub(r"[{}\\$]", "", s)
    return s

@cached_function
def group_families(deTeX=False):
    L = [(el["family"], el["tex_name"], el["name"]) for el in db.gps_families.search(projection=["family", "tex_name", "name"], sort=["priority"])]
    L = [(fam, name if "fam" in tex else f"${tex}$") for (fam, tex, name) in L]
    if deTeX:
        # Used for constructing the dropdown
        return [(fam, deTeX_name(name)) for (fam, name) in L]

    def hidden(fam):
        return fam not in ["C", "S", "D", "A", "Q", "GL", "SL", "PSL", "Sp", "SO", "Sporadic"]
    L = [(fam, name, "fam_more" if hidden(fam) else "fam_always", hidden(fam)) for (fam, name) in L]
    return L

# For dynamic knowls
@app.context_processor
def ctx_abstract_groups():
    return {
        "cc_data": cc_data,
        "sub_data": sub_data,
        "rchar_data": rchar_data,
        "cchar_data": cchar_data,
        "dyn_gen": dyn_gen,
        "semidirect_data": semidirect_data,
        "nonsplit_data": nonsplit_data,
        "possibly_split_data": possibly_split_data,
        "aut_data": aut_data,
        "trans_expr_data": trans_expr_data,
    }


def learnmore_list():
    return [
        ("Source and acknowledgements", url_for(".how_computed_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Abstract  group labeling", url_for(".labels_page")),
    ]


def learnmore_list_add(learnmore_label, learnmore_url):
    return learnmore_list() + [(learnmore_label, learnmore_url)]


def learnmore_list_remove(matchstring):
    return filter(lambda t: t[0].find(matchstring) < 0, learnmore_list())


def subgroup_label_is_valid(lab):
    m = abstract_subgroup_label_regex.fullmatch(lab)
    if m:
        return m


def label_is_valid(lab):
    return abstract_group_label_regex.fullmatch(lab)


#parser for conjugacy class search
@search_parser(clean_info=True, prep_ranges=True)
def parse_group(inp, query, qfield):
    if label_is_valid(inp):
        gp_ord, gp_count = gp_label_to_cc_data(inp)
        query["group_order"] = gp_ord
        query["group_counter"] = gp_count
    elif re.fullmatch(r'\d+',inp):
        query["group_order"] = int(inp)
    else:
        raise ValueError("It must be a valid group label or order of the group. ")

@search_parser
def parse_family(inp, query, qfield):
    if inp not in ([el[0] for el in group_families(deTeX=True)] + ['any']):
        raise ValueError("Not a valid family label.")
    if inp == 'any':
        query[qfield] = {'$in':list(db.gps_special_names.search(projection='label'))}
    elif inp == 'C':
        query["cyclic"] = True
    else:
        query[qfield] = {'$in':list(db.gps_special_names.search({'family':inp}, projection='label'))}

@search_parser
def parse_hashes(inp, query, qfield, order_field):
    if inp.count("#") == 0:
        opts = [ZZ(opt) for opt in inp.split(",")]
        if len(opts) == 1:
            query[qfield] = opts[0]
        else:
            query[qfield] = {"$or": opts}
    elif inp.count("#") == 1:
        N, hsh = inp.split("#")
        N, hsh = ZZ(N), ZZ(hsh)
        if order_field not in query:
            query[order_field] = N
        elif query[order_field] != N:
            raise ValueError(f"You cannot specify order both in the {order_field} input and the {qfield} input")
        query[qfield] = hsh
    else:
        raise ValueError("To specify multiple hash values, all must have the same order; provide the order in the order input and then just give hashes separated by commas")

#input string of complex character label and return rational character label
def q_char(char):
    return char.rstrip(digits)


def get_bread(tail=[]):
    base = [("Groups", url_for(".index")), ("Abstract", url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def display_props(proplist, joiner="and"):
    if len(proplist) == 1:
        return proplist[0]
    elif len(proplist) == 2:
        return f" {joiner} ".join(proplist)
    else:
        return ", ".join(proplist[:-1]) + f", {joiner} {proplist[-1]}"

def find_props(
    gp,
    overall_order,
    impl_order,
    overall_display,
    implications,
    hence_str,
    show,
):
    props = []
    noted = set()
    for prop in overall_order:
        if not getattr(gp, prop, None) or prop in noted or prop not in show:
            continue
        noted.add(prop)
        impl = [B for B in implications.get(prop, []) if B not in noted]
        cur = 0
        while cur < len(impl):
            impl.extend(
                [
                    B
                    for B in implications.get(impl[cur], [])
                    if B not in impl and B not in noted
                ]
            )
            cur += 1
        noted.update(impl)
        impl = [
            overall_display.get(B)
            for B in impl_order
            if B in impl and B in show
        ]
        if impl:
            props.append(f"{overall_display[prop]} ({hence_str} {display_props(impl)})")
        else:
            props.append(overall_display[prop])
    return props


group_prop_implications = {
    "cyclic": ["abelian", "is_elementary", "Zgroup"],
    "abelian": ["nilpotent", "Agroup", "metabelian"],
    "pgroup": ["nilpotent", "is_elementary"],
    "is_elementary": ["nilpotent", "is_hyperelementary"],
    "nilpotent": ["supersolvable"],  # for finite groups
    "Zgroup": ["Agroup", "metacyclic"],  # metacyclic for finite groups
    "metacyclic": ["metabelian", "supersolvable"],
    "supersolvable": ["monomial"],  # for finite groups
    "is_hyperelementary": ["monomial"],
    "monomial": ["solvable"],
    "metabelian": ["solvable"],
    "nab_simple": ["quasisimple", "almost_simple"],
    "quasisimple": ["nab_perfect"],
    "nab_perfect": ["nonsolvable"],
}


def get_group_prop_display(gp, cyclic_known=True):
    # We want elementary and hyperelementary to display which primes, but only once
    elementaryp = ''
    hyperelementaryp = ''
    if hasattr(gp, 'elementary'):
        elementaryp = ",".join(str(p) for p, e in ZZ(gp.elementary).factor())
        hyperelementaryp = ",".join(
            str(p)
            for p, e in ZZ(gp.hyperelementary).factor()
            if not p.divides(gp.elementary)
        )
    if (
        gp.order == 1
    ):  # here it will be implied from cyclic, so both are in the implication list
        elementaryp = " (for every $p$)"
        hyperelementaryp = ""
    elif hasattr(gp, 'pgroup') and gp.pgroup:  # We don't display p since there's only one in play
        elementaryp = hyperelementaryp = ""
    elif gp.cyclic:  # both are in the implication list
        if not cyclic_known: # rare case where subgroup is cyclic but not in db
            elementarylist = str(gp.order.prime_factors()).replace("[",""). replace("]","")
            elementaryp = f" ($p = {elementarylist}$)"
            hyperelementaryp = ""
        elif gp.elementary == gp.hyperelementary:
            elementaryp = f" ($p = {elementaryp}$)"
            hyperelementaryp = ""
        else:
            elementaryp = f" ($p = {elementaryp}$)"
            hyperelementaryp = f" (also for $p = {hyperelementaryp}$)"
    elif hasattr(gp, 'is_elementary') and gp.is_elementary:  # Now elementary is a top level implication
        elementaryp = f" for $p = {elementaryp}$"
        if hasattr(gp, 'hyperelementary') and gp.elementary == gp.hyperelementary:
            hyperelementaryp = ""
        else:
            hyperelementaryp = f" (also for $p = {hyperelementaryp}$)"
    elif hasattr(gp, 'hyperelementary') and gp.hyperelementary:  # Now hyperelementary is a top level implication
        hyperelementaryp = f" for $p = {hyperelementaryp}$"
    overall_display = {
        "cyclic": display_knowl("group.cyclic", "cyclic"),
        "abelian": display_knowl("group.abelian", "abelian"),
        "nonabelian": display_knowl("group.abelian", "nonabelian"),
        "nilpotent": display_knowl('group.nilpotent', 'nilpotent'),
        "supersolvable": display_knowl("group.supersolvable", "supersolvable"),
        "monomial": display_knowl("group.monomial", "monomial"),
        "solvable": display_knowl("group.solvable", "solvable"),
        "nonsolvable": display_knowl("group.solvable", "nonsolvable"),
        "Zgroup": f"a {display_knowl('group.z_group', 'Z-group')}",
        "Agroup": f"an {display_knowl('group.a_group', 'A-group')}",
        "metacyclic": display_knowl("group.metacyclic", "metacyclic"),
        "metabelian": display_knowl("group.metabelian", "metabelian"),
        "quasisimple": display_knowl("group.quasisimple", "quasisimple"),
        "almost_simple": display_knowl("group.almost_simple", "almost simple"),
        "ab_simple": display_knowl("group.simple", "simple"),
        "nab_simple": display_knowl("group.simple", "simple"),
        "ab_perfect": display_knowl("group.perfect", "perfect"),
        "nab_perfect": display_knowl("group.perfect", "perfect"),
        "rational": display_knowl("group.rational_group", "rational"),
        "pgroup": f"a {display_knowl('group.pgroup', '$p$-group')}",
        "is_elementary": display_knowl("group.elementary", "elementary") + elementaryp,
        "is_hyperelementary": display_knowl("group.hyperelementary", "hyperelementary")
        + hyperelementaryp,
    }
    # We display a few things differently for trivial groups
    if gp.order == 1:
        overall_display["pgroup"] += " (for every $p$)"
    return overall_display

def create_boolean_subgroup_string(sgp, type="normal"):
    # We put direct and semidirect after normal since (hence normal) seems weird there, even if correct
    implications = {
        "thecenter": ["characteristic", "central"],
        "thecommutator": ["characteristic"],
        "thefrattini": ["characteristic"],
        "thefitting": ["characteristic", "nilpotent"],
        "theradical": ["characteristic", "solvable"],
        "thesocle": ["characteristic"],
        "characteristic": ["normal"],
        "cyclic": ["abelian"],
        "abelian": ["nilpotent"],
        "stem": ["central"],
        "central": ["abelian"],
        "is_sylow": ["is_hall", "nilpotent"],
        "nilpotent": ["solvable"],
    }

    if type == "normal":
        overall_order = [
            "thecenter",
            "thecommutator",
            "thefrattini",
            "thefitting",
            "theradical",
            "thesocle",
            "characteristic",
            "normal",
            "maximal",
            "direct",
            "semidirect",
            "cyclic",
            "stem",
            "central",
            "abelian",
            "nonabelian",
            "is_sylow",
            "is_hall",
            "pgroup",
            "is_elementary",
            "nilpotent",
            "Zgroup",
            "metacyclic",
            "supersolvable",
            "is_hyperelementary",
            "monomial",
            "metabelian",
            "solvable",
            "nab_simple",
            "ab_simple",
            "Agroup",
            "quasisimple",
            "nab_perfect",
            "ab_perfect",
            "almost_simple",
            "nonsolvable",
            "rational",
        ]
        impl_order = [
            "characteristic",
            "normal",
            "abelian",
            "central",
            "nilpotent",
            "solvable",
            "supersolvable",
            "is_hall",
            "monomial",
            "nonsolvable",
            "is_elementary",
            "is_hyperelementary",
            "metacyclic",
            "metabelian",
            "Zgroup",
            "Agroup",
            "nab_perfect",
            "quasisimple",
            "almost_simple",
        ]
        implications.update(group_prop_implications)
    else:
        overall_order = [
            "thecenter",
            "thecommutator",
            "thefrattini",
            "thefitting",
            "theradical",
            "thesocle",
            "characteristic",
            "normal",
            "maximal",
            "direct",
            "semidirect",
            "cyclic",
            "stem",
            "central",
            "abelian",
            "nonabelian",
            "is_sylow",
            "is_hall",
            "nilpotent",
            "solvable",
            "nab_perfect",
            "nonsolvable",
        ]
        impl_order = [
            "characteristic",
            "normal",
            "abelian",
            "central",
            "nilpotent",
            "solvable",
            "is_hall",
        ]

    if not getattr(sgp,'normal'):  #if gp isn't normal we don't store direct/semidirect
        overall_order.remove('direct')
        overall_order.remove('semidirect')

    for A, L in implications.items():
        for B in L:
            assert A in overall_order and B in overall_order
            assert overall_order.index(A) < overall_order.index(B)
            assert B in impl_order

    overall_display = {
        "thecenter": display_knowl("group.center", "the center"),
        "thecommutator": display_knowl(
            "group.commutator_subgroup", "the commutator subgroup"
        ),
        "thefrattini": display_knowl(
            "group.frattini_subgroup", "the Frattini subgroup"
        ),
        "thefitting": display_knowl("group.frattini_subgroup", "the Fitting subgroup"),
        "theradical": display_knowl("group.radical", "the radical"),
        "thesocle": display_knowl("group.socle", "the socle"),
        "characteristic": display_knowl(
            "group.characteristic_subgroup", "characteristic"
        ),
        "normal": display_knowl("group.subgroup.normal", "normal"),
        "maximal": display_knowl("group.maximal_subgroup", "maximal"),
        "cyclic": display_knowl("group.cyclic", "cyclic"),
        "stem": display_knowl("group.stem_extension", "stem"),
        "central": display_knowl("group.central", "central"),
        "abelian": display_knowl("group.abelian", "abelian"),
        "nonabelian": display_knowl("group.abelian", "nonabelian"),
        "is_sylow": f"a {display_knowl('group.sylow_subgroup', '$'+str(sgp.sylow)+'$-Sylow subgroup')}",
        "is_hall": f"a {display_knowl('group.subgroup.hall', 'Hall subgroup')}",
        "nilpotent": display_knowl("group.nilpotent", "nilpotent"),
        "solvable": display_knowl("group.solvable", "solvable"),
        "nab_perfect": display_knowl("group.perfect", "perfect"),
        "nonsolvable": display_knowl("group.solvable", "nonsolvable"),
    }
    if getattr(sgp,'normal'):  #if gp isn't normal we don't store direct/semidirect
        norm_attr = {"direct": f"a {display_knowl('group.direct_product', 'direct factor')}","semidirect": f"a {display_knowl('group.semidirect_product', 'semidirect factor')}"}
        overall_display.update(norm_attr)

    if type == "normal":
        if sgp.cyclic and sgp.subgroup is None:  # deals with rare case where subgroup is cyclic but not in db
            overall_display.update(get_group_prop_display(sgp.sub, cyclic_known=False))
        else:
            overall_display.update(get_group_prop_display(sgp.sub))

    assert set(overall_display) == set(overall_order)
    hence_str = display_knowl(
        "group.subgroup_properties_interdependencies", "hence"
    )  # This needs to contain both kind of implications....
    props = find_props(
        sgp,
        overall_order,
        impl_order,
        overall_display,
        implications,
        hence_str,
        show=overall_display,
    )
    if type == "normal":
        main = f"The subgroup is {display_props(props)}."
#        unknown = [prop for prop in overall_order if getattr(sgp, prop, None) is None]
    else:
        main = f"This subgroup is {display_props(props)}."
    unknown = [prop for prop in overall_order if getattr(sgp, prop, None) is None]
    if {'ab_simple', 'nab_simple'} <= set(unknown):
        unknown.remove('ab_simple')
    if sgp.cyclic and sgp.subgroup is None:  # deals with rare case of certain cyclic subgroups not in db
        unknown.remove('is_elementary')
        unknown.remove('is_hyperelementary')
        unknown.remove('monomial')

    unknown = [overall_display[prop] for prop in unknown]
    if unknown:
        main += f"  Whether it is {display_props(unknown, 'or')} has not been computed."
    return main

# function to create string of group characteristics
def create_boolean_string(gp, type="normal"):
    # We totally order the properties in two ways: by the order that they should be listed overall,
    # and by the order they should be listed in implications
    # For the first order, it's important that A come before B whenever A => B
    if not gp:
        return "Properties have not been computed"
    overall_order = [
        "cyclic",
        "abelian",
        "nonabelian",
        "pgroup",
        "is_elementary",
        "nilpotent",
        "Zgroup",
        "metacyclic",
        "supersolvable",
        "is_hyperelementary",
        "monomial",
        "metabelian",
        "solvable",
        "nab_simple",
        "ab_simple",
        "Agroup",
        "quasisimple",
        "nab_perfect",
        "ab_perfect",
        "almost_simple",
        "nonsolvable",
        "rational",
    ]
    # Only things that are implied need to be included here, and there are no constraints on the order
    impl_order = [
        "abelian",
        "nilpotent",
        "solvable",
        "supersolvable",
        "monomial",
        "nonsolvable",
        "is_elementary",
        "is_hyperelementary",
        "metacyclic",
        "metabelian",
        "Zgroup",
        "Agroup",
        "nab_perfect",
        "quasisimple",
        "almost_simple",
    ]
    short_show = {
            "cyclic",
            "abelian",
            "nonabelian",
            "nilpotent",
            "solvable",
            "nab_simple",
            "nonsolvable",
            "nab_perfect",
        }
    short_string = type == "knowl"

    # Implications should give edges of a DAG, and should be listed in the group.properties_interdependencies knowl
    implications = group_prop_implications
    for A, L in implications.items():
        for B in L:
            assert A in overall_order and B in overall_order
            assert overall_order.index(A) < overall_order.index(B)
            assert B in impl_order

    overall_display = get_group_prop_display(gp)
    assert set(overall_display) == set(overall_order)

    hence_str = display_knowl("group.properties_interdependencies", "hence")
    props = find_props(
        gp,
        overall_order,
        impl_order,
        overall_display,
        implications,
        hence_str,
        show=(short_show if short_string else overall_display),
    )
    if type == "ambient":
        main = f"The ambient group is {display_props(props)}."
    elif type == "quotient":
        main = f"The quotient is {display_props(props)}."
    elif type == "knowl":
        main = f"{display_props(props)}."
    else:
        main = f"This group is {display_props(props)}."
    unknown = [prop for prop in overall_order if getattr(gp, prop, None) is None]
    if {'ab_simple', 'nab_simple'} <= set(unknown):
        unknown.remove('ab_simple')

    unknown = [overall_display[prop] for prop in unknown]
    if unknown and type != "knowl":
        main += f"  Whether it is {display_props(unknown, 'or')} has not been computed."
    return main


def url_for_label(label):
    if label == "random":
        return url_for(".random_abstract_group")
    return url_for("abstract.by_label", label=label)


def url_for_subgroup_label(label):
    if label == "random":
        return url_for(".random_abstract_subgroup")
    return url_for("abstract.by_subgroup_label", label=label)

#label is the label of a complex character
def url_for_chartable_label(label):
    gp = ".".join(label.split(".")[:2])
    return url_for(".char_table", label=gp, char_highlight=label)

#Here the input is a dictionary with certain data from the gps_conj_classes table filled in
def url_for_cc_label(record):
    gplabel = cc_data_to_gp_label(record["group_order"], record["group_counter"])
    return url_for(".char_table", label=gplabel, cc_highlight=record["label"], cc_highlight_i=record["counter"])

@abstract_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=GroupsSearchArray())
    if request.args:
        info["search_type"] = search_type = info.get(
            "search_type", info.get("hst", "")
        )
        if search_type in ["List", "", "Random"]:
            return group_search(info)
        elif search_type in ["Subgroups", "RandomSubgroup"]:
            info["search_array"] = SubgroupSearchArray()
            return subgroup_search(info)
        elif search_type in ["ComplexCharacters", "RandomComplexCharacter"]:
            info["search_array"] = ComplexCharSearchArray()
            return complex_char_search(info)
        elif search_type in ["ConjugacyClasses"]:  # no random since lots of groups with cc don't have characters also computed
            info["search_array"] = ConjugacyClassSearchArray()
            return conjugacy_class_search(info)
    info["stats"] = GroupStats()
    info["count"] = 50
    info["order_list"] = ["1-64", "65-127", "128", "129-255", "256", "257-383", "384", "385-511", "513-1000", "1001-1500", "1501-2000", "2001-"]
    info["nilp_list"] = range(1, 10)
    info["prop_browse_list"] = [
        ("abelian=yes", "abelian"),
        ("abelian=no", "nonabelian"),
        ("solvable=yes", "solvable"),
        ("solvable=no", "nonsolvable"),
        ("simple=yes", "simple"),
        ("perfect=yes", "perfect"),
        ("rational=yes", "rational"),
    ]
    info["maxgrp"] = db.gps_groups.max("order")
    info["families"] = group_families()

    return render_template(
        "abstract-index.html",
        title="Abstract groups",
        bread=bread,
        info=info,
        learnmore=learnmore_list(),
    )


@abstract_page.route("/stats")
def statistics():
    title = "Abstract groups: Statistics"
    return render_template(
        "display_stats.html",
        info=GroupStats(),
        title=title,
        bread=get_bread([("Statistics", " ")]),
        learnmore=learnmore_list(),
    )


@abstract_page.route("/dynamic_stats")
def dynamic_statistics():
    info = to_dict(request.args, search_array=GroupsSearchArray())
    GroupStats().dynamic_setup(info)
    title = "Abstract groups: Dynamic statistics"
    return render_template(
        "dynamic_stats.html",
        info=info,
        title=title,
        bread=get_bread([("Dynamic Statistics", " ")]),
        learnmore=learnmore_list(),
    )


@abstract_page.route("/random")
def random_abstract_group():
    label = db.gps_groups.random(projection="label")
    response = make_response(redirect(url_for(".by_label", label=label), 307))
    response.headers["Cache-Control"] = "no-cache, no-store"
    return response


@abstract_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "group.abstract",
        db.gps_groups,
        url_for_label,
        title="Some interesting groups",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list(),
    )


@abstract_page.route("/<label>")
def by_label(label):
    if label_is_valid(label):
        return render_abstract_group(label)
    else:
        flash_error("The label %s is invalid.", label)
        return redirect(url_for(".index"))


AB_LABEL_RE = re.compile(r"\d+(_\d+)?(\.\d+(_\d+)?)*")
def canonify_abelian_label(label, smith=False):
    parts = defaultdict(list)
    for piece in label.split("."):
        if "_" in piece:
            base, exp = map(ZZ, piece.split("_"))
        else:
            base = ZZ(piece)
            exp = 1
        for p, e in base.factor():
            parts[p].extend([p ** e] * exp)
    for v in parts.values():
        v.sort()
    if smith:
        M = max(len(v) for v in parts.values())
        for p, qs in parts.items():
            parts[p] = [1] * (M - len(qs)) + qs
        return [prod(qs) for qs in zip(*parts.values())]
    else:
        return sum((parts[p] for p in sorted(parts)), [])


@abstract_page.route("/ab/<label>")
def by_abelian_label(label):
    # For convenience, we provide redirects for abelian groups:
    # m1_e1.m2_e2... represents C_{m1}^e1 x C_{m2}^e2 x ...
    if not AB_LABEL_RE.fullmatch(label):
        flash_error(
            r"The abelian label %s is invalid; it must be of the form m1_e1.m2_e2... representing $C_{m_1}^{e_1} \times C_{m_2}^{e_2} \times \cdots$",
            label,
        )
        return redirect(url_for(".index"))
    primary = canonify_abelian_label(label)
    # Avoid database error on a hopeless search
    dblabel = None
    if not [z for z in primary if z > 2**31-1]:
        dblabel = db.gps_groups.lucky(
            {"abelian": True, "primary_abelian_invariants": primary}, "label"
        )
    if dblabel is None:
        snf = primary_to_smith(primary)
        canonical_label = '.'.join(str(z) for z in snf)
        if canonical_label != label:
            return redirect(url_for(".by_abelian_label", label=canonical_label))
        else:
            return render_abstract_group("ab/" + canonical_label, data=primary)
    else:
        return redirect(url_for(".by_label", label=dblabel))


@abstract_page.route("/auto_gens/<label>")
def auto_gens(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null() or gp.source == "Missing":  # latter is for groups in Magma but not GAP db
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    if gp.live() or gp.aut_gens is None:
        flash_error("The generators for the automorphism group of the group with label %s have not been computed.", label)
        return redirect(url_for(".by_label", label=label))
    return render_template(
        "auto_gens_page.html",
        gp=gp,
        title="Generators of automorphism group for $%s$" % gp.tex_name,
        bread=get_bread([(label, url_for(".by_label", label=label)), ("Automorphism group generators", " ")]),
                        )


@abstract_page.route("/sub/<label>")
def by_subgroup_label(label):
    if subgroup_label_is_valid(label):
        return render_abstract_subgroup(label)
    else:
        flash_error("The label %s is invalid.", label)
        return redirect(url_for(".index"))


@abstract_page.route("/char_table/<label>")
def char_table(label):
    label = clean_input(label)
    info = to_dict(request.args,
                   dispv=sparse_cyclotomic_to_mathml)
    gp = WebAbstractGroup(label)
    if gp.is_null() or gp.source == "Missing":  # latter is for groups not in GAP but in Magma db
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    if gp.live():
        flash_error("The complex characters for the group with label %s have not been computed.", label)
        return redirect(url_for(".by_label", label=label))
    if not gp.complex_characters_known:
        flash_error("The complex characters for the group with label %s have not been computed.", label)
        return redirect(url_for(".by_label", label=label))
    if "char_highlight" in info and info["char_highlight"] not in [chtr.label for chtr in gp.characters]:
        flash_error(f"There is no character of {label} with label {info['char_highlight']}.")
        del info["char_highlight"]
    if "cc_highlight" in info and info["cc_highlight"] not in [c.label for c in gp.conjugacy_classes]:
        flash_error(f"There is no conjugacy class of {label} with label {info['cc_highlight']}.")
        del info["cc_highlight"]
    return render_template(
        "character_table_page.html",
        gp=gp,
        info=info,
        title=f"Character table for ${gp.tex_name}$",
        bread=get_bread([(label, url_for(".by_label", label=label)), ("Character table", " ")]),
    )


@abstract_page.route("/Qchar_table/<label>")
def Qchar_table(label):
    label = clean_input(label)
    info = to_dict(request.args, conv=integer_to_mathml)
    gp = WebAbstractGroup(label)
    if gp.is_null() or gp.source == "Missing": # latter is for groups not in GAP but in Magma db
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    if not gp.rational_characters_known:
        flash_error("The rational characters for the group with label %s have not been computed.", label)
        return redirect(url_for(".by_label", label=label))
    if "char_highlight" in info and info["char_highlight"] not in [chtr.label for chtr in gp.rational_characters]:
        flash_error(f"There is no rational character of {label} with label {info['char_highlight']}.")
        del info["char_highlight"]
    return render_template(
        "rational_character_table_page.html",
        gp=gp,
        info=info,
        title="Rational character table for $%s$" % gp.tex_name,
        bread=get_bread([(label, url_for(".by_label", label=label)), ("Rational character table", " ")]),
    )


def _subgroup_diagram(label, title, only, style):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null() or gp.source == "Missing":  # latter is for groups in Magma but not in GAP db
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(gp, only=only)
    info = {"dojs": dojs, "style":style}
    info.update(display_opts)
    return render_template(
        "diagram_page.html",
        info=info,
        title=title,
        bread=get_bread([("Subgroup diagram", " ")]),
        learnmore=learnmore_list(),
    )

@abstract_page.route("/diagram/<label>")
def subgroup_diagram(label):
    title = f"Diagram of subgroups up to conjugation for group {label}"
    return _subgroup_diagram(label, title, only=("subgroup", ""), style="diagram")

@abstract_page.route("/autdiagram/<label>")
def subgroup_autdiagram(label):
    title = f"Diagram of subgroups up to automorphism for group {label}"
    return _subgroup_diagram(label, title, only=("subgroup", "aut"), style="autdiagram")

@abstract_page.route("/normal_diagram/<label>")
def normal_diagram(label):
    title = f"Diagram of normal subgroups up to conjugation for group {label}"
    return _subgroup_diagram(label, title, only=("normal", ""), style="normal_diagram")

@abstract_page.route("/normal_autdiagram/<label>")
def normal_autdiagram(label):
    title = f"Diagram of normal subgroups up to automorphism for group {label}"
    return _subgroup_diagram(label, title, only=("normal", "aut"), style="normal_autdiagram")

def show_type(ab, nil, solv, smith, nilcls, dlen, clen):
    # arguments - ["abelian", "nilpotent", "solvable", "smith_abelian_invariants", "nilpotency_class", "derived_length", "composition_length"]
    if ab:
        if len(smith) == 0:
            return 'Trivial'
        if len(smith) == 1:
            return 'Cyclic'
        return f'Abelian - {len(smith)}'
    elif nil:
        return f'Nilpotent - {nilcls}'
    elif solv:
        return f'Solvable - {dlen}'
    elif clen == 1:
        return 'Simple'
    else:
        return f'Non-Solvable - {clen}'

CYCLIC_PRODUCT_RE = re.compile(r"[Cc][0-9]+(\^[0-9]+)?(\s*[*Xx]\s*[Cc][0-9]+(\^[0-9]+)?)*")
#### Searching
def group_jump(info):
    jump = info["jump"]
    # by label
    if abstract_group_label_regex.fullmatch(jump):
        return redirect(url_for(".by_label", label=jump))
    # by abelian label
    if jump.startswith("ab/") and AB_LABEL_RE.fullmatch(jump[3:]):
        return redirect(url_for(".by_abelian_label", label=jump[3:]))
    # by subgroup label
    if subgroup_label_is_valid(jump):
        return redirect(url_for(".by_subgroup_label", label=jump))
    #transitive group
    from lmfdb.galois_groups.transitive_group import Tfinder
    if Tfinder.fullmatch(jump):
        label = db.gps_transitive.lookup(jump, "abstract_label")
        if label is None:
            flash_error(f"Transitive group {jump} is not in the database")
            return redirect(url_for(".index"))
        return redirect(url_for(".by_label", label=label))
    #hash
    hre = abstract_group_hash_regex.fullmatch(jump)
    if hre:
        N, hsh = [ZZ(c) for c in hre.groups()]
        if N <= 2000 and (N < 512 or N.valuation(2) < 7):
            # Less useful here, since we mostly have group ids in this regime, but we include it for completeness
            possible_labels = list(db.gps_groups.search({"order":N, "hash": hsh}, "label"))
            if len(possible_labels) == 1:
                return redirect(url_for(".by_label", label=possible_labels[0]))
        return redirect(url_for(".index", hash=jump))
    # or as product of cyclic groups
    if CYCLIC_PRODUCT_RE.fullmatch(jump):
        invs = [n.strip() for n in jump.upper().replace("C", "").replace("X", "*").replace("^", "_").split("*")]
        return redirect(url_for(".by_abelian_label", label=".".join(invs)))
    # by name
    labs = db.gps_groups.search({"name":jump.replace(" ", "")}, projection="label", limit=2)
    if len(labs) == 1:
        return redirect(url_for(".by_label", label=labs[0]))
    elif len(labs) == 2:
        return redirect(url_for(".index", name=jump.replace(" ", "")))
    # by special name
    for family in db.gps_families.search():
        m = re.fullmatch(family["input"], jump)
        if m:
            m_dict = dict([a, int(x)] for a, x in m.groupdict().items()) # convert string to int
            lab = db.gps_special_names.lucky({"family":family["family"], "parameters":m_dict}, projection="label")
            if lab:
                return redirect(url_for(".by_label", label=lab))
            else:
                flash_error("The group %s has not yet been added to the database." % jump)
                return redirect(url_for(".index"))
    flash_error("%s is not a valid name for a group or subgroup; see %s for a list of possible families" % (jump, display_knowl('group.families', 'here')))
    return redirect(url_for(".index"))

def show_factor(n):
    if n is None or n == "":
        return ""
    if n == 0:
        return "$0$"
    return f"${latex(ZZ(n).factor())}$"

#for irrQ_degree and irrC_degree gives negative value as "-"
def remove_negatives(n):
    if n is None or n == "":
        return "?"
    elif int(n) < 0:
        return "$-$"
    return f"${n}$"


def get_url(label):
    return url_for(".by_label", label=label)


def trans_gp(val):
    if val is None:
        return ""
    return "T".join((str(val[0]),str(val[1])))

def get_trans_url(label):
    if label is None:
        return ""
    return url_for("galois_groups.by_label", label=trans_gp(label))

def display_url(label, tex):
    if label is None or missing_subs(label):
        if tex is None:
            return ''
        return f'${tex}$'
    return f'<a href="{get_url(label)}">${tex}$</a>'

def display_url_invs(label, ab_invs):
    tex = abelian_gp_display(ab_invs)
    return display_url(label, tex)

def display_url_cache(label, cache):
    tex = cache.get(label)
    return display_url(label, tex)

def get_sub_url(label):
    return url_for(".by_subgroup_label", label=label)

#This function takes in a char label and returns url for its group's char table HIGHLIGHTING ONE
def get_cchar_url(label):
    gplabel = ".".join(label.split(".")[:2])
    return url_for(".char_table", label=gplabel, char_highlight=label)

#This function takes in a char label and returns url for its rational group's char table HIGHLIGHTING ONE
def get_qchar_url(label):
    label = q_char(label)  #in case user passed in complex char
    gplabel = ".".join(label.split(".")[:2])
    return url_for(".Qchar_table", label=gplabel, char_highlight=label)


# This function takes in a conjugacy class label and returns url for its group's char table HIGHLIGHTING ONE
# Or returns just the label if conjugacy classes are known but not characters
def get_cc_url(gp_order, gp_counter, label, highlight):
    gplabel = cc_data_to_gp_label(gp_order, gp_counter)
    if isinstance(highlight, dict):
        highlight_col = highlight.get((gplabel,label))
    else:
        highlight_col = highlight
    if highlight_col is None:
        return label
    else:
        return "<a href=" + url_for(".char_table", label=gplabel, cc_highlight=label, cc_highlight_i=highlight_col) + ">" + label + "</a>"

def field_knowl(fld):
    from lmfdb.number_fields.web_number_field import WebNumberField
    field = [int(n) for n in fld]
    wnf = WebNumberField.from_coeffs(field)
    if wnf.is_null():
        return "Not computed"
    else:
        return wnf.knowl()


# This function returns a label for the conjugacy class search page for a group
def display_cc_url(numb,conj_classes_known,gp):
    if numb is None:    # for cases where we didn't compute number
        return 'not computed'
    elif conj_classes_known is False:
        return numb
    return f'<a href = "{url_for(".index", group=gp, search_type="ConjugacyClasses")}">{numb}</a>'

class Group_download(Downloader):
    table = db.gps_groups
    title = "Abstract groups"


def group_postprocess(res, info, query):
    # We want to get latex for all of the centers, central quotients, commutators and abelianizations in one query
    labels = set()
    for rec in res:
        for col in ["center_label", "central_quotient", "commutator_label", "abelian_quotient"]:
            label = rec.get(col)
            if label is not None:
                labels.add(label)
    tex_cache = {rec["label"]: rec["tex_name"] for rec in db.gps_groups.search({"label":{"$in":list(labels)}}, ["label", "tex_name"])}
    for rec in res:
        rec["tex_cache"] = tex_cache
    if "family" in info:
        if info["family"] == "any":
            fquery = {}
        else:
            fquery = {"family": info["family"]}
        fams = {rec["family"]: (rec["priority"], rec["tex_name"]) for rec in db.gps_families.search(fquery, ["family", "priority", "tex_name"])}
        fquery["label"] = {"$in":[rec["label"] for rec in res]}
        special_names = defaultdict(list)
        for rec in db.gps_special_names.search(fquery, ["label", "family", "parameters"]):
            fam, params = rec["family"], rec["parameters"]
            name = fams[fam][1].format(**params)
            if fam == "Sporadic":
                name = re.sub(r"(\d+)", r"_{\1}", name)
                if not re.match(r"[MJ]_", name):
                    name = "\\" + name
            special_names[rec["label"]].append((fams[fam][0], params.get("n"), params.get("q"), name))
        for rec in res:
            names = [x[-1] for x in sorted(special_names[rec["label"]])]
            if len(names) > 4:
                names = ", ".join(names[:4]) + ",\\dots"
            else:
                names = ", ".join(names)
            rec["family_name"] = names
    return res

group_columns = SearchColumns([
    LinkCol("label", "group.label", "Label", get_url),
    MathCol("tex_name", "group.name", "Name"),
    MathCol("family_name", "group.families", "Family name", contingent=lambda info: "family" in info, default=lambda info: "family" in info and info["family"] not in ["C", "S", "D", "A", "Q", "He", "Sporadic"]),
    ProcessedCol("order", "group.order", "Order", show_factor, align="center"),
    ProcessedCol("exponent", "group.exponent", "Exponent", show_factor, align="center"),
    MathCol("nilpotency_class", "group.nilpotent", "Nilp. class", short_title="nilpotency class", default=False),
    MathCol("derived_length", "group.derived_series", "Der. length", short_title="derived length", default=False),
    MathCol("composition_length", "group.chief_series", "Comp. length", short_title="composition length", default=False),
    MathCol("rank", "group.rank", "Rank", default=False),
    MultiProcessedCol("number_cojugacy_classes","group.conjugacy_class",r"$\card{\mathrm{conj}(G)}$",["number_conjugacy_classes","conjugacy_classes_known","label"], display_cc_url, download_col="number_conjugacy_classes", align="center", short_title="#conj(G)"),
    MathCol("number_subgroups", "group.subgroup", "Subgroups", short_title="subgroups", default=False),
    MathCol("number_subgroup_classes", "group.subgroup", r"Subgroup classes", default=False),
    MathCol("number_normal_subgroups", "group.subgroup.normal", "Normal subgroups", short_title="normal subgroups", default=False),
    MultiProcessedCol("center_label", "group.center", "Center",
                      ["center_label", "tex_cache"],
                      display_url_cache,
                      download_col="center_label"),
    MultiProcessedCol("central_quotient", "group.central_quotient_isolabel", "Central quotient",
                      ["central_quotient", "tex_cache"],
                      display_url_cache, download_col="central_quotient", default=False),
    MultiProcessedCol("commutator_label", "group.commutator_isolabel", "Commutator",
                      ["commutator_label", "tex_cache"],
                      display_url_cache, download_col="commutator_label", default=False),
    MultiProcessedCol("abelian_quotient", "group.abelianization_isolabel", "Abelianization",
                      ["abelian_quotient", "smith_abelian_invariants"],
                      display_url_invs, download_col="abelian_quotient", default=False),
    # TODO
    #MultiProcessedCol("schur_multiplier", "group.schur_multiplier", "Schur multiplier",
    #                  ["center_label", "smith_abelian_invariants"],
    #                  display_url_invs),
    ProcessedCol("aut_order", "group.automorphism", r"$\card{\mathrm{Aut}(G)}$", show_factor, align="center", short_title="automorphisms", default=False),
    ProcessedCol("outer_order", "group.outer_aut", r"$\card{\mathrm{Out}(G)}$", show_factor, align="center", short_title="outer automorphisms", default=False),
    MathCol("transitive_degree", "group.transitive_degree", "Tr. deg", short_title="transitive degree", default=False),
    MathCol("permutation_degree", "group.permutation_degree", "Perm. deg", short_title="permutation degree", default=False),
    ProcessedCol("irrC_degree", "group.min_faithful_linear", r"$\C$-irrep deg", remove_negatives, short_title=r"$\C$-irrep degree", default=False, align="center"),
    ProcessedCol("irrR_degree", "group.min_faithful_linear", r"$\R$-irrep deg", remove_negatives, short_title=r"$\R$-irrep degree", default=False, align="center"),
    ProcessedCol("irrQ_dim", "group.min_faithful_linear", r"$\Q$-irrep deg", remove_negatives, short_title=r"$\Q$-irrep degree", default=False, align="center"),
    ProcessedCol("linC_degree", "group.min_faithful_linear", r"$\C$-rep deg", remove_negatives, short_title=r"$\C$-rep degree", default=False, align="center"),
    ProcessedCol("linR_degree", "group.min_faithful_linear", r"$\R$-rep deg", remove_negatives, short_title=r"$\R$-rep degree", default=False, align="center"),
    ProcessedCol("linQ_dim", "group.min_faithful_linear", r"$\Q$-rep deg", remove_negatives, short_title=r"$\Q$-rep degree", default=False, align="center"),
    MultiProcessedCol("type", "group.type", "Type - length",
                      ["abelian", "nilpotent", "solvable", "smith_abelian_invariants", "nilpotency_class", "derived_length", "composition_length"],
                      show_type,
                      align="center")])

@search_wrap(
    table=db.gps_groups,
    title="Abstract group search results",
    err_title="Abstract groups search input error",
    columns=group_columns,
    shortcuts={"jump": group_jump, "download": Group_download()},
    bread=lambda: get_bread([("Search Results", "")]),
    learnmore=learnmore_list,
    #  credit=lambda:credit_string,
    url_for_label=url_for_label,
    postprocess=group_postprocess,
)
def group_search(info, query={}):
    group_parse(info, query)


def group_parse(info, query):
    parse_ints(info, query, "order", "order")
    parse_ints(info, query, "exponent", "exponent")
    parse_ints(info, query, "nilpotency_class", "nilpotency class")
    parse_ints(info, query, "aut_order", "aut_order")
    parse_ints(info, query, "outer_order", "outer_order")
    parse_ints(info, query, "derived_length", "derived_length")
    parse_ints(info, query, "rank", "rank")
    parse_ints(info, query, "commutator_count", "commutator length")
    parse_ints(info, query, "permutation_degree", "permutation_degree")
    parse_ints(info, query, "transitive_degree", "transitive_degree")
    parse_ints(info, query, "irrC_degree", "irrC_degree")
    parse_ints(info, query, "irrQ_degree", "irrQ_degree")
    parse_ints(info, query, "linC_degree", "linC_degree")
    parse_ints(info, query, "linQ_degree", "linQ_degree")
    parse_ints(info, query, "number_autjugacy_classes", "number_autjugacy_classes")
    parse_ints(info, query, "number_conjugacy_classes", "number_conjugacy_classes")
    parse_ints(info, query, "number_characteristic_subgroups", "number_characteristic_subgroups")
    parse_ints(info, query, "number_divisions", "number_divisions")
    parse_ints(info, query, "number_normal_subgroups", "number_normal_subgroups")
    parse_ints(info, query, "number_subgroups", "number_subgroups")
    parse_bracketed_posints(info, query, "schur_multiplier", "schur_multiplier")
    parse_multiset(info, query, "order_stats", "order_stats")
    parse_bool(info, query, "abelian", "is abelian")
    parse_bool(info, query, "cyclic", "is cyclic")
    parse_bool(info, query, "metabelian", "is metabelian")
    parse_bool(info, query, "metacyclic", "is metacyclic")
    parse_bool(info, query, "solvable", "is solvable")
    parse_bool(info, query, "supersolvable", "is supersolvable")
    parse_bool(info, query, "nilpotent", "is nilpotent")
    parse_bool(info, query, "perfect", "is perfect")
    parse_bool(info, query, "simple", "is simple")
    parse_bool(info, query, "almost_simple", "is almost simple")
    parse_bool(info, query, "quasisimple", "is quasisimple")
    parse_bool(info, query, "direct_product", "is direct product")
    parse_bool(info, query, "semidirect_product", "is semidirect product")
    parse_bool(info, query, "Agroup", "is A-group")
    parse_bool(info, query, "Zgroup", "is Z-group")
    parse_bool(info, query, "monomial", "is monomial")
    parse_bool(info, query, "rational", "is rational")
    parse_bool(info, query, "wreath_product", "is wreath product")
    parse_bracketed_posints(info, query, "exponents_of_order", "exponents_of_order")
    parse_group_label_or_order(info, query, "center_label", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "aut_group", regex=abstract_group_label_regex)
    parse_group_label_or_order(info, query, "commutator_label", regex=abstract_group_label_regex)
    parse_group_label_or_order(
        info, query, "central_quotient", regex=abstract_group_label_regex
    )
    parse_group_label_or_order(
        info, query, "abelian_quotient", regex=abstract_group_label_regex
    )
    #parse_regex_restricted(
    #    info, query, "schur_multiplier", regex=abstract_group_label_regex
    #)
    parse_regex_restricted(
        info, query, "frattini_label", regex=abstract_group_label_regex
    )
    parse_regex_restricted(info, query, "outer_group", regex=abstract_group_label_regex)
    parse_noop(info, query, "name")
    parse_ints(info, query, "order_factorization_type")
    parse_family(info, query, "family", qfield="label")
    parse_hashes(info, query, "hash", order_field="order")

subgroup_columns = SearchColumns([
    LinkCol("label", "group.subgroup_label", "Label", get_sub_url, th_class=" border-right", td_class=" border-right"),
    ColGroup("subgroup_cols", None, "Subgroup", [
        MultiProcessedCol("sub_name", "group.name", "Name",
                          ["subgroup", "subgroup_tex"],
                          display_url,
                          short_title="Sub. name", apply_download=False),
        ProcessedCol("subgroup_order", "group.order", "Order", show_factor, align="center", short_title="Sub. order"),
        CheckCol("normal", "group.subgroup.normal", "norm", short_title="Sub. normal"),
        CheckCol("characteristic", "group.characteristic_subgroup", "char", short_title="Sub. characteristic"),
        CheckCol("cyclic", "group.cyclic", "cyc", short_title="Sub. cyclic"),
        CheckCol("abelian", "group.abelian", "ab", short_title="Sub. abelian"),
        CheckCol("solvable", "group.solvable", "solv", short_title="Sub. solvable"),
        CheckCol("maximal", "group.maximal_subgroup", "max", short_title="Sub. maximal"),
        CheckCol("perfect", "group.perfect", "perf", short_title="Sub. perfect"),
        CheckCol("central", "group.central", "cent", short_title="Sub. central")]),
    SpacerCol("", th_class=" border-right", td_class=" border-right", td_style="padding:0px;", th_style="padding:0px;"), # Can't put the right border on "subgroup_cols" (since it wouldn't be full height) or "central" (since it might be hidden by the user)
    ColGroup("ambient_cols", None, "Ambient", [
        MultiProcessedCol("ambient_name", "group.name", "Name",
                          ["ambient", "ambient_tex"],
                          display_url,
                          short_title="Ambient name", apply_download=False),
        ProcessedCol("ambient_order", "group.order", "Order", show_factor, align="center", short_title="Ambient order")]),
    SpacerCol("", th_class=" border-right", td_class=" border-right", td_style="padding:0px;", th_style="padding:0px;"),
    ColGroup("quotient_cols", None, "Quotient", [
        MultiProcessedCol("quotient_name", "group.name", "Name",
                          ["quotient", "quotient_tex"],
                          display_url,
                          short_title="Quo. name", apply_download=False),
        ProcessedCol("quotient_order", "group.quotient_size", "Size", lambda n: show_factor(n) if n else "", align="center", short_title="Quo. size"),
        #next columns are None if non-normal so we set unknown to "-" instead of "?"
        CheckCol("quotient_cyclic", "group.cyclic", "cyc", unknown="$-$", short_title="Quo. cyclic"),
        CheckCol("quotient_abelian", "group.abelian", "ab", unknown="$-$", short_title="Quo. abelian"),
        CheckCol("quotient_solvable", "group.solvable", "solv", unknown="$-$", short_title="Quo. solvable"),
        CheckCol("minimal_normal", "group.maximal_quotient", "max", unknown="$-$", short_title="Quo. maximal")])],
    tr_class=["bottom-align", ""])

class Subgroup_download(Downloader):
    table = db.gps_subgroup_search

@search_wrap(
    table=db.gps_subgroup_search,
    title="Subgroup search results",
    err_title="Subgroup search input error",
    columns=subgroup_columns,
    shortcuts={"download": Subgroup_download()},
    bread=lambda: get_bread([("Search Results", "")]),
    learnmore=learnmore_list,
    url_for_label=url_for_subgroup_label,
)
def subgroup_search(info, query={}):
    info["search_type"] = "Subgroups"
    parse_ints(info, query, "subgroup_order")
    parse_ints(info, query, "ambient_order")
    parse_ints(info, query, "quotient_order", "subgroup index")
    parse_bool(info, query, "abelian")
    parse_bool(info, query, "cyclic")
    parse_bool(info, query, "solvable")
    parse_bool(info, query, "quotient_abelian")
    parse_bool(info, query, "quotient_cyclic")
    parse_bool(info, query, "quotient_solvable")
    parse_bool(info, query, "perfect")
    parse_bool(info, query, "normal")
    parse_bool(info, query, "characteristic")
    parse_bool(info, query, "maximal")
    parse_bool(info, query, "minimal_normal")
    parse_bool(info, query, "central")
    parse_bool(info, query, "split")
    parse_bool(info, query, "direct")
    parse_bool(
        info, query, "sylow", process=lambda x: ({"$gt": 1} if x else {"$lte": 1})
    )
    parse_bool(
        info, query, "hall", process=lambda x: ({"$gt": 1} if x else {"$lte": 1})
    )
    parse_bool(info, query, "nontrivproper", qfield="proper")
    parse_regex_restricted(info, query, "subgroup", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "ambient", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "quotient", regex=abstract_group_label_regex)

def print_type(val):
    if val == 0:
        return "C"
    elif val > 0:
        return "R"
    return "S"

#input a string with C, R, S and replace with -1, 1, 0
def indicator_type(strg):
    strg = strg.replace("C","0")
    strg = strg.replace("R","1")
    strg = strg.replace("S","-1")
    return strg

def char_to_sub(short_label, group, as_latex=None):
    if short_label:
        full_label = f"{group}.{short_label}"
        if as_latex:
            return f'<a href="{url_for(".by_subgroup_label", label=full_label)}">${as_latex}$</a>'
        return f'<a href="{url_for(".by_subgroup_label", label=full_label)}">{short_label}</a>'
    else:
        return "not computed"


complex_char_columns = SearchColumns([
    LinkCol("label", "group.label_complex_group_char", "Label", get_cchar_url),
    MathCol("dim", "group.representation.complex_char_deg", "Degree"),
    ProcessedCol("indicator", "group.representation.type", "Type", print_type),
    CheckCol("faithful", "group.representation.faithful", "Faithful"),
    MathCol("cyclotomic_n", "group.representation.cyclotomic_n", "Conductor", default=False),
    ProcessedCol("field", "group.representation.cyclotomic_n", "Field of Traces", field_knowl),
    LinkCol("qchar", "group.representation.rational_character", r"$\Q$-character", get_qchar_url),
    MultiProcessedCol("group", "group.name", "Group", ["group", "tex_cache"], display_url_cache, download_col="group"),
    MultiProcessedCol("image_isoclass", "group.representation.image", "Image", ["image_isoclass", "tex_cache"], display_url_cache, download_col="image_isoclass", default=False),
    MathCol("image_order", "group.representation.image", "Image Order"),
    MultiProcessedCol("kernel", "group.representation.kernel", "Kernel", ["kernel", "group"], char_to_sub, download_col="kernel", default=False),
    MathCol("kernel_order", "group.representation.kernel", "Kernel Order"),
    #ProcessedLinkCol("nt", "group.representation.min_perm_rep", "Min. Perm. Rep.", get_trans_url, trans_gp), # Data currently broken due to a bug on the computation code
    MultiProcessedCol("center", "group.representation.center", "Center", ["center", "group"], char_to_sub, download_col="center", default=False),
    MathCol("center_order", "group.representation.center", "Center Order", default=False),
    MathCol("center_index", "group.representation.center", "Center Index", default=False),
    MathCol("schur_index", "group.representation.schur_index", "Schur Index", default=False),
])


def char_postprocess(res, info, query):
    labels = set()
    qchars = set()
    for rec in res:
        for col in ["group", "image_isoclass"]:
            label = rec.get(col)
            if label is not None:
                labels.add(label)
        rec["qchar"] = q_char(rec["label"])
        qchars.add(rec["qchar"])
    tex_cache = {rec["label"]: rec["tex_name"] for rec in db.gps_groups.search({"label":{"$in":list(labels)}}, ["label", "tex_name"])}
    schur = {rec["label"]: rec["schur_index"] for rec in db.gps_qchar.search({"label":{"$in":list(qchars)}}, ["label", "schur_index"])}
    for rec in res:
        rec["tex_cache"] = tex_cache
        rec["schur_index"] = schur[rec["qchar"]]
    return res

class Complex_char_download(Downloader):
    table = db.gps_char

@search_wrap(
    table=db.gps_char,
    title="Complex character search results",
    err_title="Complex character search input error",
    columns=complex_char_columns,
    shortcuts={"download": Complex_char_download()},
    bread=lambda: get_bread([("Search Results", "")]),
    postprocess=char_postprocess,
    learnmore=learnmore_list,
    url_for_label=url_for_chartable_label,
)
def complex_char_search(info, query={}):
    info["search_type"] = "ComplexCharacters"
    if 'indicator' in info:
        info['indicator'] = indicator_type(info['indicator'])
    parse_ints(info, query, "dim")
    parse_ints(info, query, "indicator")
    parse_ints(info, query, "cyclotomic_n")
    parse_bool(info, query, "faithful")
    parse_ints(info, query, "image_order")
    parse_ints(info, query, "center_order")
    parse_ints(info, query, "center_index")
    parse_ints(info, query, "kernel_order")
    #parse_bracketed_posints(info,query,"nt",split=False,keepbrackets=True, allow0=False)
    parse_regex_restricted(info, query, "group", regex=abstract_group_label_regex)
#    parse_regex_restricted(info, query, "center", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "image_isoclass", regex=abstract_group_label_regex)
#    parse_regex_restricted(info, query, "kernel", regex=abstract_group_label_regex)


#need mathmode for MultiProcessedCol
def cc_repr(label,code , latex=True):  #default is include dollar signs
    gp = WebAbstractGroup(label)
    if latex:
        return "$" + gp.decode(code,as_str=True) + "$"
    else:  # this is for download postprocess
        if gp.element_repr_type == "Perm" or gp.element_repr_type == "PC":
            return gp.decode(code,as_str=True)
        else:   # matrices as lists
            return gp.decode(code,as_str=False)

def Power_col(i, ps):
    p = ps[i]
    return MultiProcessedCol("power_cols", None, f"{p}P", ["group_order", "group_counter", "powers","highlight_col"], lambda group_order, group_counter, powers, highlight_col: get_cc_url(group_order, group_counter, powers[i], highlight_col), align="center")


def gp_link(gp_order,gp_counter, tex_cache):
    gp = cc_data_to_gp_label(gp_order,gp_counter)
    return display_url_cache(gp, tex_cache)

conjugacy_class_columns = SearchColumns([
    MultiProcessedCol("group", "group.name", "Group", ["group_order", "group_counter", "tex_cache"], gp_link, apply_download=lambda group_order, group_counter, tex_cache: cc_data_to_gp_label(group_order, group_counter)),
    MultiProcessedCol("label", "group.label_conjugacy_class", "Label",["group_order", "group_counter", "label","highlight_col"],get_cc_url, download_col="label"),
    MathCol("order", "group.order_conjugacy_class", "Order"),
    MathCol("size", "group.size_conjugacy_class", "Size"),
    MultiProcessedCol("center", "group.centralizer", "Centralizer", ["centralizer", "group", "sub_latex"], char_to_sub, download_col="centralizer"),
    ColGroup("power_cols","group.conjugacy_class.power_classes", "Powers",
             lambda info: [Power_col(i, info["group_factors"]) for i in range(len(info["group_factors"]))],
             contingent=lambda info: info.get("group_factors",True), # group_factors not present when downloading
             orig=["powers"],
             download_together=True,
             download_col="powers"),
    MultiProcessedCol("representative","group.repr_explain","Representative",["group","representative"], cc_repr, download_col="representative"),
],db_cols=["centralizer", "counter", "group_order", "group_counter", "label", "order", "powers", "representative", "size"])
conjugacy_class_columns.languages = ['text']


def cc_postprocess(res, info, query):
    # We want to get latex for groups in one query, figure out what powers to use, and create a lookup table for counter->label
    labels = set()
    gps = set()
    centralizers = set()
    counter_to_label = {(rec["group_order"],rec["group_counter"], rec["counter"]): rec["label"] for rec in res}
    missing = defaultdict(list)
    common_support = None
    for rec in res:
        gp_order = rec.get("group_order")
        gp_counter = rec.get("group_counter")
        group = cc_data_to_gp_label(gp_order,gp_counter)
        gps.add(group)
        group_support = gp_order.prime_factors()
        if common_support is None:
            common_support = group_support
        elif common_support is not False and common_support != group_support:
            common_support = False
        for ctr in rec.get("powers", []):
            if (gp_order,gp_counter, ctr) not in counter_to_label:
                missing[gp_order,gp_counter].append(ctr)
        label = rec.get("centralizer")
        if label is not None:
            labels.add(label)
            centralizers.add(group + "." + label)
        if group is not None:
            labels.add(group)
    # We use an empty list so that [Powers_col(i,...) for i in info["group_factors"]] works
    if len(gps) == 1:  # add a message about what type representatives are
        gp = WebAbstractGroup(list(gps)[0])
        info["columns"].above_table = f"<p>{gp.repr_strg(other_page=True)}</p>"
    info["group_factors"] = common_support if common_support else []
    complex_char_known = {rec["label"]: rec["complex_characters_known"] for rec in db.gps_groups.search({'label':{"$in":list(gps)}}, ["label", "complex_characters_known"])}
    centralizer_data = {(".".join(rec["label"].split(".")[:2]), ".".join(rec["label"].split(".")[2:])): rec["subgroup_tex"] for rec in db.gps_subgroups.search({'label':{"$in":list(centralizers)}},["label","subgroup_tex"])}
    highlight_col = {}
    for rec in res:
        label = rec.get("label")
        gp_order = rec.get("group_order")
        gp_counter = rec.get("group_counter")
        rec["group"] = cc_data_to_gp_label(gp_order,gp_counter)
        group = rec.get("group")
        if (group,rec["centralizer"]) in centralizer_data:
            rec["sub_latex"] = centralizer_data[(group,rec["centralizer"])]
        else:
            rec["sub_latex"] = None
        if complex_char_known[group]:
            highlight_col[(group, label)] = rec["counter"]
        else:
            highlight_col[(group, label)] = None
    if missing:
        for rec in db.gps_conj_classes.search({"$or":[{"group_order":group_order,"group_counter":group_counter, "counter":{"$in":counters}} for (group_order, group_counter), counters in missing.items()]}, ["group_order", "group_counter", "counter", "label"]):
            gp_ord = rec.get("group_order")
            gp_counter = rec.get("group_counter")
            group = cc_data_to_gp_label(gp_ord,gp_counter)
            label = rec.get("label")
            counter_to_label[rec["group_order"],rec["group_counter"], rec["counter"]] = rec["label"]
            if complex_char_known[group]:
                highlight_col[(group, label)] = rec["counter"]
            else:
                highlight_col[(group, label)] = None
    tex_cache = {rec["label"]: rec["tex_name"] for rec in db.gps_groups.search({"label":{"$in":list(labels)}}, ["label", "tex_name"])}
    for rec in res:
        rec["tex_cache"] = tex_cache
        rec["powers"] = [counter_to_label[rec["group_order"], rec["group_counter"], ctr] for ctr in rec["powers"]]
        rec["highlight_col"] = highlight_col
    return res


class Conjugacy_class_download(Downloader):
    table = db.gps_conj_classes

    def postprocess(self, res, info, query):  # need to convert representatives to human readable, and write cc labels
        if not hasattr(self, 'counter_to_label'):
            self.counter_to_label = {}  # initialize dictionary
        gptuple = (res['group_order'],res['group_counter'])   # have we already found this group
        if gptuple not in self.counter_to_label:
            query_pow = {}  # need this dict to get all the power labels
            query_pow['group_order'] = res['group_order']
            query_pow['group_counter'] = res['group_counter']
            self.counter_to_label[gptuple] = {rec["counter"]: rec["label"] for rec in db.gps_conj_classes.search(query_pow, ["group_order", "group_counter", "counter", "label"])}  # counter-to-label dictionary for group, order pair
        res['representative'] = cc_repr(cc_data_to_gp_label(res['group_order'],res['group_counter']), res['representative'], latex=False)
        pow_list = [self.counter_to_label[gptuple][pow] for pow in res['powers']]
        res['powers'] = ",".join(pow_list)
        return res

@search_wrap(
    table=db.gps_conj_classes,
    title="Conjugacy class search results",
    err_title="Conjugacy class search input error",
    columns=conjugacy_class_columns,
    shortcuts={"download": Conjugacy_class_download()},
    bread=lambda: get_bread([("Search Results", "")]),
    postprocess=cc_postprocess,
    learnmore=learnmore_list,
#    random_projection=["group_order", "group_counter", "label", "counter"],
    url_for_label=url_for_cc_label,
)
def conjugacy_class_search(info, query={}):
    info["search_type"] = "ConjugacyClasses"
    parse_ints(info, query, "order")
    parse_ints(info, query, "size")
    parse_group(info,query, "group")


def factor_latex(n):
    return "$%s$" % web_latex(factor(n), False)

def diagram_js(gp, layers, display_opts, aut=False, normal=False):
    # Counts are not right for aut diagram if we know up to conj.
    if aut and not gp.outer_equivalence:
        autcounts = gp.aut_class_counts
    ilayer = 4
    iorder = 0
    if normal:
        ilayer += 1
        iorder += 1
    if not aut and not gp.outer_equivalence:
        ilayer += 2
        iorder += 2
    if gp.outer_equivalence and ilayer > 3:
        ilayer -= 2
    ll = [
        [
            grp.subgroup,
            grp.short_label,
            grp.subgroup_tex,
            grp.count if (gp.outer_equivalence or not aut) else autcounts[grp.aut_label],
            grp.subgroup_order,
            gp.tex_images.get(grp.subgroup_tex, gp.tex_images["?"]),
            grp.diagramx[ilayer],
            grp.diagramx[iorder]
        ]
        for grp in layers[0]
    ]
    orders = [sub[4] for sub in ll]
    order_ctr = Counter(orders)
    orders = sorted(order_ctr)
    Omega = {}
    by_Omega = defaultdict(list)
    for n in orders:
        W = sum(e for p, e in n.factor())
        Omega[n] = W
        by_Omega[W].append(n)
    # We would normally make order_lookup a dictionary, but we're passing it to the horrible language known as javascript
    order_lookup = [[n, Omega[n], by_Omega[Omega[n]].index(n)] for n in orders]
    max_width = max(sum(order_ctr[n] for n in by_Omega[W]) for W in by_Omega)
    display_opts["w"] = max(display_opts["w"], min(100 * max_width, 20000))
    display_opts["layers"] = max(display_opts["layers"], len(by_Omega))
    display_opts["h"] = 160 * display_opts["layers"]

    return [ll, layers[1]], order_lookup

def diagram_js_string(gp, only=None):
    glist = [[], [], [], []]
    order_lookup = [[], [], [], []]
    display_opts = defaultdict(int)
    limit = (100 if only is None else 0)
    for i, pair in enumerate([("subgroup", ""), ("subgroup", "aut"), ("normal", ""), ("normal", "aut")]):
        sub_all, sub_aut = pair
        if (only is None or only == pair) and gp.diagram_count(sub_all, sub_aut, limit=limit):
            glist[i], order_lookup[i] = diagram_js(gp, gp.subgroup_lattice(sub_all, sub_aut), display_opts, aut=bool(sub_aut), normal=(sub_all == "normal"))

    if any(glist):
        return f'var [sdiagram,glist] = make_sdiagram("subdiagram", "{gp.label}", {glist}, {order_lookup}, {display_opts["layers"]});', display_opts
    else:
        return "", display_opts

# Writes individual pages
def render_abstract_group(label, data=None):
    info = {}
    if data is None:
        label = clean_input(label)
        gp = WebAbstractGroup(label)
    elif isinstance(data, list): # abelian group
        gp = WebAbstractGroup(label, data=data)
    if gp.is_null() or gp.source == "Missing": #groups of order 6561 are not in GAP but are labeled in Magma
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    # check if it fails to be a potential label even

    info["boolean_characteristics_string"] = create_boolean_string(gp)
    info['pos_int_and_factor'] = pos_int_and_factor
    info['conv'] = integer_to_mathml
    info['dispv'] = sparse_cyclotomic_to_mathml
    if gp.live():
        title = f"Abstract group {label}"
        friends = []
        downloads = []
    else:
        if gp.has_subgroups:
            if gp.subgroup_inclusions_known:
                info["dojs"], display_opts = diagram_js_string(gp)
                info["wide"] = display_opts["w"] > 1600 # boolean

            info["max_sub_cnt"] = gp.max_sub_cnt
            info["max_quo_cnt"] = gp.max_quo_cnt

        title = f"Abstract group ${gp.tex_name}$"

        # disable until we can fix downloads
        downloads = [("Group to Gap", url_for(".download_group", label=label, download_type="gap")),
                                         ("Group to Magma", url_for(".download_group", label=label, download_type="magma")),
                #            ("Group to Oscar", url_for(".download_group", label=label, download_type="oscar")),
                                         ("Underlying data", url_for(".gp_data", label=label)),
        ]

        # "internal" friends
        sbgp_of_url = (
            " /Groups/Abstract/?subgroup=" + label + "&search_type=Subgroups"
        )
        sbgp_url = (
            "/Groups/Abstract/?ambient=" + label + "&search_type=Subgroups"
        )
        quot_url = (
            "/Groups/Abstract/?quotient=" + label + "&search_type=Subgroups"
        )
        friends = [
            ("Subgroups", sbgp_url),
            ("Extensions", quot_url),
            ("Supergroups", sbgp_of_url),
        ]

        if gp.complex_characters_known:
            char_url = url_for(".index", group=label, search_type="ComplexCharacters")
            friends += [("Complex characters", char_url)]

        # "external" friends
        if gap_group_label_regex.fullmatch(label):
            gap_ints = [int(y) for y in label.split(".")]
        else:
            gap_ints = [-1,-1]
        gap_str = str(gap_ints).replace(" ", "")
        if db.g2c_curves.count({"aut_grp_label": label}) > 0:
            g2c_url = f"/Genus2Curve/Q/?aut_grp_label={label}"
            friends += [("As the automorphism of a genus 2 curve", g2c_url)]
            if db.hgcwa_passports.count({"group": gap_str}) > 0:
                auto_url = (
                    "/HigherGenus/C/Aut/?group=%5B"
                    + str(gap_ints[0])
                    + "%2C"
                    + str(gap_ints[1])
                    + "%5D"
                )
            friends += [("... and of a higher genus curve", auto_url)]
        elif db.hgcwa_passports.count({"group": gap_str}) > 0:
            auto_url = (
                "/HigherGenus/C/Aut/?group=%5B"
                + str(gap_ints[0])
                + "%2C"
                + str(gap_ints[1])
                + "%5D"
            )
            friends += [("As the automorphism of a curve", auto_url)]

        if abstract_group_label_regex.fullmatch(label) and len(gp.transitive_friends) > 0:
            gal_gp_url = "/GaloisGroup/?gal=" + label
            friends += [("As a transitive group", gal_gp_url)]

        if db.gps_st.count({"component_group": label}) > 0:
            st_url = (
                "/SatoTateGroup/?"
                + 'include_irrational=yes&'
                + 'component_group=%5B'
                + str(gap_ints[0])
                + "%2C"
                + str(gap_ints[1])
                + "%5D"
            )
            friends += [("As the component group of a Sato-Tate group", st_url)]

    bread = get_bread([(label, "")])
    learnmore_gp_picture = ('Picture description', url_for(".picture_page"))

    return render_template(
        "abstract-show-group.html",
        title=title,
        bread=bread,
        info=info,
        gp=gp,
        code=gp.code_snippets(),
        properties=gp.properties(),
        friends=friends,
        learnmore=learnmore_list_add(*learnmore_gp_picture),
        KNOWL_ID=f"group.abstract.{label}",
        downloads=downloads,
    )


def render_abstract_subgroup(label):
    info = {}
    label = clean_input(label)
    seq = WebAbstractSubgroup(label)
    if seq.is_null():
        flash_error("No subgroup with label %s was found in the database.", label)
        return redirect(url_for(".index"))

    info["create_boolean_string"] = create_boolean_string
    info["create_boolean_subgroup_string"] = create_boolean_subgroup_string
    info["pos_int_and_factor"] = pos_int_and_factor

    if seq.subgroup_tex != "?":
        if seq.normal:
            title = r"Normal subgroup $%s \trianglelefteq %s$"
        else:
            title = r"Non-normal subgroup $%s \subseteq %s$"
        title = title % (seq.subgroup_tex, seq.ambient_tex)
    else:
        if seq.normal:
            title = r"Normal subgroup of $%s$"
        else:
            title = r"Non-normal subgroup of $%s$"
        title = title % (seq.ambient_tex)

    properties = [
        ("Label", label),
        ("Order", factor_latex(seq.subgroup_order)),
        ("Index", factor_latex(seq.quotient_order)),
        ("Normal", "Yes" if seq.normal else "No"),
    ]
    downloads = [
        ("Underlying data", url_for(".sgp_data", label=label))
    ]

    bread = get_bread([(label,)])

    return render_template(
        "abstract-show-subgroup.html",
        title=title,
        bread=bread,
        info=info,
        seq=seq,
        properties=properties,
        # friends=friends,
        downloads=downloads,
        learnmore=learnmore_list(),
    )


def make_knowl(title, knowlid):
    return '<a title="%s" knowl="%s">%s</a>' % (title, knowlid, title)


@abstract_page.route("/subinfo/<ambient>/<short_label>")
def shortsubinfo(ambient, short_label):
    label = "%s.%s" % (ambient, short_label)
    if not subgroup_label_is_valid(label):
        # Should only come from code, so return nothing if label is bad
        return ""
    wsg = WebAbstractSubgroup(label)
    # helper function

    def subinfo_getsub(title, knowlid, lab):
        full_lab = "%s.%s" % (ambient, lab)
        h = WebAbstractSubgroup(full_lab) if lab else None
        prop = display_knowl(knowlid, title)
        if lab:
            return f"<tr><td>{prop}</td><td>{h.make_span()}</td></tr>\n"
        else:
            return f"<tr><td>{prop}</td><td>not computed</td></tr>\n"

    ans = (
        'Information on the subgroup <span class="%s" data-sgid="%s">$%s$</span><br>\n'
        % (wsg.spanclass(), wsg.label, wsg.subgroup_tex if '?' not in wsg.subgroup_tex else '')
    )
    ans += f"<p>{create_boolean_subgroup_string(wsg, type='knowl')}</p>"
    ans += "<table>"
    ans += f"<tr><td>{display_knowl('group.order', 'Order')}</td><td>${wsg.subgroup_order}"
    if wsg.subgroup_order > 1 and not is_prime(wsg.subgroup_order):
        ans += "="+latex(factor(wsg.subgroup_order))
    ans += "$</td></tr>"
    if wsg.normal:
        ans += f"<tr><td>{display_knowl('group.quotient', 'Quotient')}</td><td>{wsg.display_quotient()}</td></tr>"
    else:
        ans += f"<tr><td>Number of conjugates</td><td>{wsg.count}</td></tr>"
    ans += subinfo_getsub("Normalizer", "group.subgroup.normalizer", wsg.normalizer)
    ans += subinfo_getsub(
        "Normal closure", "group.subgroup.normal_closure", wsg.normal_closure
    )
    ans += subinfo_getsub("Centralizer", "group.centralizer", wsg.centralizer)
    ans += subinfo_getsub("Core", "group.core", wsg.core)
    # ans += '<tr><td>Coset action</td><td>%s</td></tr>\n' % wsg.coset_action_label
    ## There was a bug in the Magma code computing generators, so we disable this for the moment
    # gp = WebAbstractGroup(ambient) # needed for generators
    # if wsg.subgroup_order > 1:
    #    ans += f"<tr><td>{display_knowl('group.generators', 'Generators')}</td><td>${gp.show_subgroup_generators(wsg)}$</td></tr>"
    # if not wsg.characteristic:
    #    ans += f"<tr><td>Number of autjugates</td><td>{wsg.conjugacy_class_count}</td></tr>"
    alt_tex = wsg.label if '?' in wsg.subgroup_tex else rf'${wsg.subgroup_tex}$'
    ans += (
        '<tr><td></td><td style="text-align: right"><a href="%s">%s subgroup homepage</a></td>'
        % (url_for_subgroup_label(wsg.label), alt_tex)
    )
    if wsg.subgroup:
        ans += (
            '<tr><td></td><td style="text-align: right"><a href="%s">$%s$ abstract group homepage</a></td></tr>'
            % (url_for_label(wsg.subgroup), wsg.subgroup_tex)
        )
    ans += "</table>"
    return ans


@abstract_page.route("/Completeness")
def completeness_page():
    t = "Completeness of the abstract groups data"
    bread = get_bread("Completeness")
    return render_template(
        "single.html",
        kid="rcs.cande.groups.abstract",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Complete"),
    )


@abstract_page.route("/Labels")
def labels_page():
    t = "Labels for abstract groups"
    bread = get_bread("Labels")
    return render_template(
        "single.html",
        kid="group.label",
        learnmore=learnmore_list_remove("label"),
        title=t,
        bread=bread,
    )


@abstract_page.route("/Reliability")
def reliability_page():
    t = "Reliability of the abstract groups data"
    bread = get_bread("Reliability")
    return render_template(
        "single.html",
        kid="rcs.rigor.groups.abstract",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )


@abstract_page.route("/GroupPictures")
def picture_page():
    t = "Pictures for abstract groups"
    bread = get_bread("Group Pictures")
    return render_template(
        "single.html",
        kid="portrait.groups.abstract",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Picture")
    )

@abstract_page.route("picture/<label>.svg")
def picture(label):
    if label_is_valid(label):
        label = clean_input(label)
        gp = WebAbstractGroup(label)
        if gp.is_null() or gp.source == "Missing": # latter is for groups in Magma but not GAP db
            flash_error("No group with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        # The user specifically requested the image, so we don't impose a limit on the number of conjugacy classes
        try:
            img = gp.image()
        except Exception:
            flash_error("Error generating image for %s.", label)
            return redirect(url_for(".index"))
        else:
            svg_io = BytesIO()
            svg_io.write(img.encode("utf-8"))
            svg_io.seek(0)
            return send_file(svg_io, mimetype='image/svg+xml')
    else:
        flash_error("The label %s is invalid.", label)
        return redirect(url_for(".index"))

@abstract_page.route("/Source")
def how_computed_page():
    t = "Source of the abstract group data"
    bread = get_bread("Source")
    return render_template(
        "multi.html",
        kids=["rcs.source.groups.abstract",
              "rcs.ack.groups.abstract",
              "rcs.cite.groups.abstract"],
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )

@abstract_page.route("/data/<label>")
def gp_data(label):
    if not abstract_group_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Abstract group data - {label}"
    group_order, group_counter = label.split(".")
    group_order = int(group_order)
    if group_counter.isdigit():
        group_counter = int(group_counter)
    else:
        group_counter = class_to_int(group_counter) + 1  # we start labeling at 1
    return datapage([label, [group_order, group_counter], label, label, label], ["gps_groups", "gps_conj_classes", "gps_qchar", "gps_char", "gps_subgroups"], bread=bread, title=title, label_cols=["label", ["group_order","group_counter"], "group", "group", "ambient"])

@abstract_page.route("/sdata/<label>")
def sgp_data(label):
    if not subgroup_label_is_valid(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_subgroup_label(label)), ("Data", " ")])
    title = f"Abstract subgroup data - {label}"
    data = db.gps_subgroup_search.lookup(label, ["ambient", "subgroup", "quotient"])
    if data is None:
        return abort(404)
    if data["quotient"] is None:
        return datapage([label, data["subgroup"], data["ambient"]], ["gps_subgroups", "gps_groups", "gps_groups"], bread=bread, title=title)
    else:
        return datapage([label, data["subgroup"], data["ambient"], data["quotient"]], ["gps_subgroups", "gps_groups", "gps_groups", "gps_groups"], bread=bread, title=title)


# need to write characters in GAP or Magma formats for downloads
def download_cyclotomics(n,vals, dltype):
    s = ""
    val = vals[0]
    c = val[0]  # coefficient
    if c == 0:
        return 0
    e = val[1]  # exponent
    if c == 1 and e == 0:  # special case of 1
        s += str(1)
    elif c != 1:   #don't put leading 1s
        s += str(c)
    if e != 0:
        if c != 1:
            s += "*"
        s += "E(" + str(n) + ")"
        if e != 1:
            s += "^" + str(e)

    for i in range(1,len(vals)):
        val = vals[i]
        c = val[0]  # coefficient
        e = val[1]  # exponent
        if c > 0:
            s += "+"
        if c == 1 and e == 0:  # special case of 1
            s += str(1)
        if c == -1 and e != 0:
            s += "-"   # we don't want -1E
        elif c != 1:
            s += str(c)
        if e != 0:
            if abs(c) != 1:
                s += "*"
            s += "E(" + str(n) + ")"
            if e != 1:
                s += "^" + str(e)
    if dltype == "magma":  # Magma needs different format.
        return s.replace("E(" + str(n) + ")", "K.1")
    return s


# create preable for downloading individual group
def download_preable(com1, com2, dltype, cc_known):
    if dltype == "gap":
        f = "#"
    else:
        f = ""
    s = com1
    s += f + " Various presentations of this group are stored in this file: \n"
    s += f + "\t GPC is polycyclic presentation GPerm is permutation group \n"
    s += f + "\t GLZ, GLFp, GLZA, GLZq, GLFq if they exist are matrix groups \n \n"
    s += f + " Many characteristics of the group are stored as booleans in a record: \n"
    s += f + "\t Agroup, Zgroup, abelian, almost_simple,cyclic, metabelian, \n"
    s += f + "\t metacyclic, monomial, nilpotent, perfect, quasisimple, rational, \n"
    s += f + "\t solvable, supersolvable \n \n"
    if cc_known:
        if dltype == "gap":
            s += f + " The character table is stored as a record chartbl_n_i where n is the order \n"
            s += f + " of the group and i is which group of that order it is. The record is \n"
            s += f + " converted to a character table using ConvertToLibraryCharacterTableNC \n"
        if dltype == "magma":
            s += f + " The character table is stored as chartbl_n_i where n is the order of \n"
            s += f + " the group and i is which group of that order it is. Conjugacy classes \n"
            s += f + " are stored in the variable 'C' with elements from the group 'G'. \n"
    s += com2
    return s


# create construction of group for downloading, G is WebAbstractGroup
def download_construction_string(G,dltype):
    # add Lie groups?
    s = ""
    snippet = G.code_snippets()
    if "PC" in G.representations:
        gp_str = str(snippet['presentation'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GPC :=").replace("G.", "GPC.").replace("G,", "GPC,")
    if "Perm" in G.representations:
        gp_str = str(snippet['permutation'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GPerm :=")
    if "GLZ" in G.representations:
        gp_str = str(snippet['GLZ'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GLZ :=")
    if "GLFp" in G.representations:
        gp_str = str(snippet['GLFp'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GLFp :=")
    if "GLZN" in G.representations:
        gp_str = str(snippet['GLZN'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GLZN :=")
    if "GLZq" in G.representations:
        gp_str = str(snippet['GLZq'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GLZq :=")
    if "GLFq" in G.representations:
        gp_str = str(snippet['GLFq'][dltype]) + "\n"
        s += gp_str.replace("G :=", "GLFq :=")
    return str(s)


# create boolean string for downloading, G is WebAbstractGroup
def download_boolean_string(G,dltype,ul_label):
    if dltype == "magma":
        s = "RF := recformat< Agroup, Zgroup, abelian, almost_simple, cyclic, metabelian, metacyclic, monomial, nilpotent, perfect, quasisimple, rational, solvable, supersolvable  : BoolElt >; \n"
        s += "booleans_" + ul_label + " := rec< RF |  "
    elif dltype == "gap":
        s = "booleans_" + ul_label + " := rec( "
    else:
        return ""

    s += "Agroup := " + str(G.Agroup).lower() + ", \n"
    s += "Zgroup := " +	str(G.Zgroup).lower() + ", \n"
    s += "abelian := " + str(G.abelian).lower() + ", \n"
    s += "almost_simple := " + str(G.almost_simple).lower() + ", \n"
    s += "cyclic := " + str(G.cyclic).lower() + ", \n"
    s += "metabelian := " + str(G.metabelian).lower() + ", \n"
    s += "metacyclic := " + str(G.metacyclic).lower() + ", \n"
    s += "monomial := " + str(G.monomial).lower() + ", \n"
    s += "nilpotent := " + str(G.nilpotent).lower() + ", \n"
    s += "perfect := " + str(G.perfect).lower() + ", \n"
    s += "quasisimple := " + str(G.quasisimple).lower() + ", \n"
    s += "rational := " + str(G.rational).lower() + ", \n"
    s += "solvable := " + str(G.solvable).lower() + ", \n"
    s += "supersolvable := " + str(G.supersolvable).lower() + " \n" # no comma since last one

    # close record
    if dltype == "gap":
        s += "); \n"
    if dltype == "magma":
        s += ">; \n"
    return s


def download_char_table_magma(G, ul_label):
    gp_type = G.element_repr_type

    if gp_type == "PC":
        s = "G:= GPC;\n"
    elif gp_type == "Perm":
        s = "G:= GPerm;\n"
    else:
        repr_data = G.representations[gp_type]
        str_d = str(repr_data['d'])  # need later
    if gp_type == "GLZ":
        s = "G:= GLZ;\n"
    if gp_type == "GLFp":
        s = "G:= GLFp;\n"
    if gp_type == "GLZN":
        s = "G:= GLZN;\n"
    if gp_type == "GLZq":
        s = "G:= GLZq;\n"
    if gp_type == "GLFq":
        s = "G:= GLFq;\n"
    if gp_type == "Lie":   # need to check this for other Lie groups
        repr_data = G.representations['Lie'][0]
        str_d = str(repr_data['d'])  # need later
        s = "G:= " + repr_data['family'] + "(" + str_d + "," + str(repr_data['q']) + "); \n"

    s += "C := SequenceToConjugacyClasses([car<Integers(), Integers(), G> |"
    for conj in G.conjugacy_classes:
        if gp_type == "Lie":
            s += "< " + str(conj.order) + ", " + str(conj.size) + ", Matrix(" + str_d + ", " + str(G.decode_as_matrix(conj.representative,rep_type=gp_type, ListForm=True, LieType=(gp_type == "Lie"))) + ")>,"
        elif gp_type != "PC" and gp_type != "Perm":
            s += "< " + str(conj.order) + ", " + str(conj.size) + ", Matrix(" + str_d + ", " + str(G.decode_as_matrix(conj.representative,rep_type=gp_type, ListForm=True, LieType=(gp_type == gp_type))) + ")>,"
        else:
            s += "< " + str(conj.order) + ", " + str(conj.size) + ", " + str(G.decode(conj.representative,rep_type=gp_type, as_magma=True)) + ">,"
    s = s[:-1]  # get rid of last comma
    s += "]); \n"

    s += "CR := CharacterRing(G);\n"

    for char in G.characters:
        if char.cyclotomic_n != 1:  # number field
            s += "K := CyclotomicField(" + str(char.cyclotomic_n) + ": Sparse := true);\n"
            s += "S := [ K |"
            for val in char.values:
                s += str(download_cyclotomics(str(char.cyclotomic_n),val, "magma"))
                s += ","
            s = s[:-1]  # get rid of last comma
            s += "]; \n"
            s += "x := CR!S; \n"
        else:
            s += "x := CR!\\" + str([val[0][0] for val in char.values]) + "; \n"
        s += "x`IsCharacter := true;\n"
        s += "x`Schur := " + str(char.indicator) + ";\n"
        s += "x`IsIrreducible := true; \n"
    s += "_ := CharacterTable(G : Check := 0); \n"
    s += "chartbl_" + G.label.replace(".","_") + ":= KnownIrreducibles(CR); \n"
    return s


def download_char_table_gap(G,ul_label):
    tbl = "chartbl_" + G.label.replace(".","_")
    s = tbl + ":=rec(); \n"
    s += tbl + ".IsFinite:= true; \n"
    s += tbl + ".UnderlyingCharacteristic:= 0; \n"

    gp_type = G.element_repr_type

    if gp_type == "PC":
        s += tbl + ".UnderlyingGroup:= GPC;\n"
    if gp_type == "Perm":
        s += tbl + ".UnderlyingGroup:= GPerm;\n"
    if gp_type == "GLZ":
        s += tbl + ".UnderlyingGroup:= GLZ;\n"
    if gp_type == "GLFp":
        s += tbl + ".UnderlyingGroup:= GLFp;\n"
    if gp_type == "GLZN":
        s += tbl + ".UnderlyingGroup:= GLZN;\n"
    if gp_type == "GLZq":
        s += tbl + ".UnderlyingGroup:= GLZq;\n"
    if gp_type == "GLFq":
        s += tbl + ".UnderlyingGroup:= GLFq;\n"

    s += tbl + ".Size:= " + str(G.order) + ";\n"
    s += tbl + '.InfoText:= "Character table for group ' + G.label + ' downloaded from the LMFDB."; \n'
    s += tbl + '.Identifier:= " ' + G.name + ' "; \n'
    s += tbl + ".NrConjugacyClasses:= " + str(G.number_conjugacy_classes) + "; \n"

    # process info from each conjugacy class
    size_centralizers, class_names,order_class_reps, cc_reps = ([] for i in range(4))
    num_primes = G.num_primes_for_power_maps
    power_maps = [[ ] for i in range(num_primes)]
    for conj in G.conjugacy_classes:
        for i in range(num_primes):
            power_maps[i].append(conj.powers[i])
        #power_maps.append(conj.powers)
        size_centralizers.append(int(conj.group_order/conj.size))
        class_names.append(conj.label)
        order_class_reps.append(conj.order)
        if gp_type != "PC" and gp_type != "Perm":  # need to do matrix directly to include right format
            cc_reps.append(G.decode_as_matrix(conj.representative,rep_type=gp_type,ListForm=True))
        else:
            cc_reps.append(G.decode(conj.representative,rep_type=gp_type))

    cl_names = str(class_names).replace("'",'"')  # need " for GAP instead of '
    pwr_maps = "[ , "
    for i in range(len(power_maps)-1):
        pwr_maps += str(power_maps[i]) + ", "
    pwr_maps += str(power_maps[len(power_maps)-1]) + "]"  # PowerMaps needs a blank entry in front

    s += tbl + ".ConjugacyClasses:= " + str(cc_reps) + ";\n"
    s += tbl + ".IdentificationOfConjugacyClasses:= " + str(list(range(1,G.number_conjugacy_classes+1))) + ";\n"
    s += tbl + ".ComputedPowerMaps:= "  + str(pwr_maps) + ";\n"
    s += tbl + ".SizesCentralizers:= "  + str(size_centralizers) + ";\n"
    s += tbl + ".ClassNames:= "  + str(cl_names) + ";\n"
    s += tbl + ".OrderClassRepresentatives:= "  + str(order_class_reps) + ";\n"

    irr_values = []
    for char in G.characters:
        irr_values_individual = [download_cyclotomics(char.cyclotomic_n,char.values[i],"gap") for i in range(len(char.values))]
        irr_values.append(irr_values_individual)
    irr = str(irr_values).replace("'","")
    s += tbl + ".Irr:= " + str(irr) + ";\n"

    # end material
    s += "ConvertToLibraryCharacterTableNC(" + tbl + "); \n"
    return s


def download_char_table(G,dltype,ul_label):  # G is web abstract group
    if dltype == "gap":
        return download_char_table_gap(G,ul_label)
    elif dltype == "magma":
        return download_char_table_magma(G,ul_label)
    else:
        return ""


@abstract_page.route("/<label>/download/<download_type>")
def download_group(**args):
    dltype = args["download_type"]
    label = args["label"]
#    com = "#"  # single line comment start
    com1 = ""  # multiline comment start
    com2 = ""  # multiline comment end

    wag = WebAbstractGroup(label)

    ul_label = wag.label.replace(".","_")
    filename = "group" + ul_label
    mydate = time.strftime("%d %B %Y")
    if dltype == "gap":
        filename += ".g"
#        com = ""
        com1 = "#"
        com2 = ""
    elif dltype == "magma":
        #        com = ""
        com1 = "/*"
        com2 = "*/"
        filename += ".m"
#    elif dltype == "oscar":
#        com = ""
#        com1 = "#="
#        com2 = "=#"
    s = com1 + " Group " + label + " downloaded from the LMFDB on %s." % (mydate) + " " + com2
    s += "\n \n"

    s += download_preable(com1, com2,dltype, wag.complex_characters_known)
    s += "\n \n"

    s += com1 + " Constructions " + com2 + "\n"
    s += download_construction_string(wag,dltype)
    s += "\n \n"

    s += com1 + " Booleans " + com2 + "\n"
    s += download_boolean_string(wag,dltype, ul_label)
    s += "\n \n"

    if wag.complex_characters_known:
        s += com1 + " Character Table " + com2 + "\n"
        s += download_char_table(wag,dltype, ul_label)

    response = make_response(s)
    response.headers['Content-type'] = 'text/plain'
    return response

    #strIO = BytesIO()
    #strIO.write(s.encode("utf-8"))
    #strIO.seek(0)
    #return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)


class GroupsSearchArray(SearchArray):
    noun = "group"
    sorts = [
            ("", "order", ["order", "counter"]),
            ("exponent", "exponent", ["exponent", "order", "counter"]),
            ("nilpotency_class", "nilpotency class", ["nilpotency_class", "order", "counter"]),
            ("derived_length", "derived length", ["derived_length", "order", "counter"]),
            ("composition_length", "composition length", ["composition_length", "order", "counter"]),
            ("rank", "rank", ["rank", "eulerian_function", "order", "counter"]),
            #("center_label", "center", ["center_label", "order", "counter"]),
            #("commutator_label", "commutator", ["commutator_label", "order", "counter"]),
            #("central_quotient", "central quotient", ["central_quotient", "order", "counter"]),
            #("abelian_quotient", "abelianization", ["abelian_quotient", "order", "counter"]),
            ("aut_order", "automorphisms", ["aut_order", "aut_group", "order", "counter"]),
            ("number_subgroups", "subgroups", ["number_subgroups", "order", "counter"]),
            ("number_subgroup_classes", "subgroup classes", ["number_subgroup_classes", "order", "counter"]),
            ("number_normal_subgroups", "normal subgroups", ["number_normal_subgroups", "order", "counter"]),
            ("number_conjugacy_classes", "conjugacy classes", ["number_conjugacy_classes", "order", "counter"]),
            ("number_autjugacy_classes", "autjugacy classes", ["number_autjugacy_classes", "order", "counter"]),
            ("number_divisions", "divisions", ["number_divisions", "order", "counter"]),
            ("transitive_degree", "transitive degree", ["transitive_degree", "counter"]),
            ("permutation_degree", "permutation degree", ["permutation_degree", "counter"]),
            ("irrC_degree", r"$\C$-irrep degree", ["irrC_degree", "counter"]),
            ("irrQ_degree", r"$\Q$-irrep degree", ["irrQ_degree", "counter"])
    ]
    jump_example = "8.3"
    jump_egspan = "e.g. 8.3, GL(2,3), 8T34, C3:C4, C2*A5, C16.D4, 6#1, or 12.4.2.b1.a1"
    jump_prompt = "Label or name"
    jump_knowl = "group.find_input"

    def __init__(self):
        order = TextBox(
            name="order",
            label="Order",
            knowl="group.order",
            example="3",
            example_span="4, or a range like 3..5",
        )
        exponent = TextBox(
            name="exponent",
            label="Exponent",
            knowl="group.exponent",
            example="2, 3, 7",
            example_span="2, or list of integers like 2, 3, 7",
        )
        nilpclass = TextBox(
            name="nilpotency_class",
            label="Nilpotency class",
            knowl="group.nilpotent",
            example="3",
            example_span="4, or a range like 3..5",
        )
        aut_group = TextBox(
            name="aut_group",
            label="Automorphism group",
            knowl="group.automorphism",
            example="4.2",
            example_span="4.2",
        )
        aut_order = TextBox(
            name="aut_order",
            label="Automorphism group order",
            short_label="Automorphisms",
            knowl="group.automorphism",
            example="3",
            example_span="4, or a range like 3..5",
        )
        derived_length = TextBox(
            name="derived_length",
            label="Derived length",
            knowl="group.derived_series",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True,
        )
        frattini_label = TextBox(
            name="frattini_label",
            label="Frattini subgroup",
            knowl="group.frattini_subgroup",
            example="4.2",
            example_span="4.2",
            advanced=True,
        )
        outer_group = TextBox(
            name="outer_group",
            label="Outer aut. group",
            knowl="group.outer_aut",
            example="4.2",
            example_span="4.2",
            advanced=True,
        )
        outer_order = TextBox(
            name="outer_order",
            label="Outer aut. group order",
            short_label="Outer automorphisms",
            knowl="group.outer_aut",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True,
        )
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="group.rank",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True,
        )
        abelian = YesNoBox(
            name="abelian", label="Abelian", knowl="group.abelian", example_col=True
        )
        metabelian = YesNoBox(
            name="metabelian",
            label="Metabelian",
            knowl="group.metabelian",
            advanced=True,
            example_col=True,
        )
        cyclic = YesNoBox(
            name="cyclic",
            label="Cyclic",
            knowl="group.cyclic",
            example_col=True,
        )
        metacyclic = YesNoBox(
            name="metacyclic",
            label="Metacyclic",
            knowl="group.metacyclic",
            advanced=True,
            example_col=True,
        )
        solvable = YesNoBox(
            name="solvable",
            label="Solvable",
            knowl="group.solvable",
            example_col=True,
        )
        supersolvable = YesNoBox(
            name="supersolvable",
            label="Supersolvable",
            knowl="group.supersolvable",
            advanced=True,
            example_col=True,
        )
        nilpotent = YesNoBox(
            name="nilpotent",
            label="Nilpotent",
            knowl="group.nilpotent",
            example_col=True,
        )
        simple = YesNoBox(
            name="simple",
            label="Simple",
            knowl="group.simple",
            example_col=True,
        )
        almost_simple = YesNoBox(
            name="almost_simple",
            label="Almost simple",
            knowl="group.almost_simple",
            example_col=True,
            advanced=True,
        )
        quasisimple = YesNoBox(
            name="quasisimple",
            label="Quasisimple",
            knowl="group.quasisimple",
            advanced=True,
            example_col=True,
        )
        perfect = YesNoBox(
            name="perfect",
            label="Perfect",
            knowl="group.perfect",
            example_col=True,
        )
        direct_product = YesNoBox(
            name="direct_product",
            label="Direct product",
            knowl="group.direct_product",
            example_col=True,
        )
        semidirect_product = YesNoBox(
            name="semidirect_product",
            label="Semidirect product",
            knowl="group.semidirect_product",
            example_col=True,
        )
        permutation_degree = TextBox(
            name="permutation_degree",
            label="Min. permutation degree",
            knowl="group.permutation_degree",
            example="3",
            example_span="4, or a range like 3..5",
        )
        transitive_degree = TextBox(
            name="transitive_degree",
            label="Min. transitive degree",
            knowl="group.transitive_degree",
            example="3",
            example_span="4, or a range like 3..5",
        )
        irrC_degree = TextBox(
            name="irrC_degree",
            label=r"Min. degree of $\C$-irrep",
            knowl="group.min_faithful_linear",
            example="3",
            example_span="-1, or a range like 3..5",
            advanced=True,
        )
        irrQ_degree = TextBox(
            name="irrQ_degree",
            label=r"Min. degree of $\Q$-irrep",
            knowl="group.min_faithful_linear",
            example="3",
            example_span="-1, or a range like 3..5",
            advanced=True,
        )
        linC_degree = TextBox(
            name="linC_degree",
            label=r"Min. degree of $\C$-rep",
            knowl="group.min_faithful_linear",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True,
        )
        linQ_degree = TextBox(
            name="linQ_degree",
            label=r"Min. degree of $\Q$-rep",
            knowl="group.min_faithful_linear",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True,
        )
        schur_multiplier = TextBox(
            name="schur_multiplier",
            label="Schur multiplier",
            knowl="group.schur_multiplier",
            example="[2,4,12]",
            example_span="[2,4,12]",
            advanced=True,
        )
        Agroup = YesNoBox(
            name="Agroup",
            label="A-group",
            knowl="group.a_group",
            advanced=True,
            example_col=True,
        )
        Zgroup = YesNoBox(
            name="Zgroup",
            label="Z-group",
            knowl="group.z_group",
            advanced=True,
            example_col=True,
        )
        monomial = YesNoBox(
            name="monomial",
            label="Monomial",
            knowl="group.monomial",
            advanced=True,
        )
        rational = YesNoBox(
            name="rational",
            label="Rational",
            knowl="group.rational_group",
            advanced=True,
            example_col=True,
        )
        center_label = TextBox(
            name="center_label",
            label="Center",
            knowl="group.center_isolabel",
            example="4.2, 8",
            example_span="4 or 4.2 (order or label)",
        )
        commutator_label = TextBox(
            name="commutator_label",
            label="Commutator",
            knowl="group.commutator_isolabel",
            example="4.2, 8",
            example_span="4 or 4.2 (order or label)",
        )
        abelian_quotient = TextBox(
            name="abelian_quotient",
            label="Abelianization",
            knowl="group.abelianization_isolabel",
            example="4.2, 8",
            example_span="4 or 4.2 (order or label)",
        )
        central_quotient = TextBox(
            name="central_quotient",
            label="Central quotient",
            knowl="group.central_quotient_isolabel",
            example="4.2, 8",
            example_span="4 or 4.2 (order or label)",
        )
        order_stats = TextBox(
            name="order_stats",
            label="Order statistics",
            knowl="group.order_stats",
            example="1^1, 2^3, 3^2",
            example_span="1^1, 2^3, 3^2",
        )
        exponents_of_order = TextBox(
            name="exponents_of_order",
            label="Order factorization",
            knowl="group.order_factorization",
            example="[2,1]",
            example_span="[2,1] or [8]",
            advanced=True,
        )
        commutator_count = TextBox(
            name="commutator_count",
            label="Commutator length",
            knowl="group.commutator_length",
            example="2-",
            example_span="1 or 2-4",
            advanced=True,
        )
        wreath_product = YesNoBox(
            name="wreath_product",
            label="Wreath product",
            knowl="group.wreath_product",
            advanced=True,
        )
        name = SneakyTextBox(
            name="name",
            label="Name",
            knowl="group.find_input",
            example="C16.D4",
        )
        order_factorization_type = SneakySelectBox(
            name="order_factorization_type",
            label="Order",
            knowl="group.order_factorization_type",
            options=([("", ""),
                      ("0", "1"),
                      ("1", "p"),
                      ("2", "p^2"),
                      ("3", "p^{3-6}"),
                      ("7", "p^{7+}"),
                      ("11", "squarefree"),
                      ("22", "p^2q,p^2q^2"),
                      ("31", "p^3q,p^4q"),
                      ("51", "p^{5+}q"),
                      ("32", "p^{3+}q^2"),
                      ("33", "p^{3+}q^{3+}"),
                      ("222", "p^{1,2}q^{1,2}r^{1,2}..."),
                      ("311", "p^{3+}qr..."),
                      ("321", "other")]),
        )
        # Numbers of things boxes
        number_subgroups = TextBox(
            name="number_subgroups",
            label="Number of subgroups",
            knowl="group.subgroup",
            example="3",
            example_span="4, or a range like 3..5",
        )
        number_normal_subgroups = TextBox(
            name="number_normal_subgroups",
            label="Num. of normal subs",
            knowl="group.subgroup.normal",
            example="3",
            example_span="4, or a range like 3..5",
        )
        number_conjugacy_classes = TextBox(
            name="number_conjugacy_classes",
            label="Num. of conj. classes",
            knowl="group.conjugacy_class",
            example="3",
            example_span="4, or a range like 3..5",
        )
        number_autjugacy_classes = TextBox(
            name="number_autjugacy_classes",
            label="Num. of aut. classes",
            knowl="group.autjugacy_class",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
        )
        number_characteristic_subgroups = TextBox(
            name="number_characteristic_subgroups",
            label="Num. of char. subgroups",
            knowl="group.characteristic_subgroup",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
        )
        number_divisions = TextBox(
            name="number_divisions ",
            label="Number of divisions",
            knowl="group.division",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
        )
        family = SelectBox(
            name="family",
            options=[("", "")] + group_families(deTeX=True) + [("any", "any")],
            knowl="group.families",
            label="Family",
        )
        hsh = SneakyTextBox(
            name="hash",
            label="Hash",
            knowl="group.hash",
            example="5120#4714647875464396655",
        )

        count = CountBox()

        self.browse_array = [
            [order, exponent],
            [aut_group, nilpclass],
            [aut_order, commutator_label],
            [center_label, abelian_quotient],
            [central_quotient, frattini_label],
            [abelian, direct_product],
            [cyclic, semidirect_product],
            [nilpotent, perfect],
            [simple, solvable],
            [transitive_degree, permutation_degree],
            [number_subgroups, number_normal_subgroups],
            [number_conjugacy_classes, number_autjugacy_classes],
            [order_stats, rank],
            [irrC_degree, irrQ_degree],
            [linC_degree, linQ_degree],
            [almost_simple, derived_length],
            [quasisimple, supersolvable],
            [outer_group, metabelian],
            [outer_order, metacyclic],
            [Agroup, monomial],
            [Zgroup, rational],
            [schur_multiplier, wreath_product],
            [number_characteristic_subgroups, number_divisions],
            [exponents_of_order, commutator_count],
            [count, family],
        ]

        self.refine_array = [
            [order, exponent, nilpclass, nilpotent],
            [center_label, commutator_label, central_quotient, abelian_quotient],
            [abelian, cyclic, solvable, simple],
            [perfect, direct_product, semidirect_product, wreath_product],
            [aut_group, aut_order, transitive_degree, permutation_degree],
            [number_subgroups, number_normal_subgroups, number_conjugacy_classes],
            [order_stats, family, exponents_of_order, commutator_count],
            [irrC_degree, irrQ_degree, linC_degree, linQ_degree],
            [outer_group, outer_order, metabelian, metacyclic],
            [almost_simple, quasisimple, Agroup, Zgroup],
            [frattini_label, derived_length, rank, schur_multiplier],
            [supersolvable, monomial, rational],
            [number_characteristic_subgroups, number_autjugacy_classes, number_divisions],
            [name, order_factorization_type, hsh],
        ]

    sort_knowl = "group.sort_order"

class SubgroupSearchArray(SearchArray):
    null_column_explanations = { # No need to display warnings for these
        "quotient": False,
        "quotient_abelian": False,
        "quotient_solvable": False,
        "quotient_cyclic": False,
        "direct": False,
        "split": False,
    }
    sorts = [("", "ambient order", ['ambient_order', 'ambient_counter', 'quotient_order', 'counter']),
             ("sub_ord", "subgroup order", ['subgroup_order', 'ambient_order', 'ambient_counter', 'counter']),
             ("sub_ind", "subgroup index", ['quotient_order', 'ambient_order', 'ambient_counter', 'counter'])]
    def __init__(self):
        abelian = YesNoBox(name="abelian", label="Abelian", knowl="group.abelian")
        cyclic = YesNoBox(name="cyclic", label="Cyclic", knowl="group.cyclic")
        solvable = YesNoBox(name="solvable", label="Solvable", knowl="group.solvable")
        quotient_abelian = YesNoBox(
            name="quotient_abelian", label="Abelian quotient", knowl="group.abelian"
        )
        quotient_cyclic = YesNoBox(
            name="quotient_cyclic", label="Cyclic quotient", knowl="group.cyclic"
        )
        quotient_solvable = YesNoBox(
            name="quotient_solvable", label="Solvable quotient", knowl="group.solvable"
        )
        perfect = YesNoBox(name="perfect", label="Perfect", knowl="group.perfect")
        normal = YesNoBox(name="normal", label="Normal", knowl="group.subgroup.normal")
        characteristic = YesNoBox(
            name="characteristic",
            label="Characteristic",
            knowl="group.characteristic_subgroup",
        )
        maximal = YesNoBox(
            name="maximal", label="Maximal", knowl="group.maximal_subgroup"
        )
        minimal_normal = YesNoBox(
            name="minimal_normal",
            label="Maximal quotient",
            knowl="group.maximal_quotient",
        )
        central = YesNoBox(name="central", label="Central", knowl="group.central")
        direct = YesNoBox(
            name="direct", label="Direct product", knowl="group.direct_product"
        )
        split = YesNoBox(
            name="split", label="Semidirect product", knowl="group.semidirect_product"
        )
        # stem = YesNoBox(
        #    name="stem",
        #    label="Stem",
        #    knowl="group.stem_extension")
        hall = YesNoBox(name="hall", label="Hall subgroup", knowl="group.subgroup.hall")
        sylow = YesNoBox(
            name="sylow", label="Sylow subgroup", knowl="group.sylow_subgroup"
        )
        subgroup = TextBox(
            name="subgroup",
            label="Subgroup label",
            knowl="group.subgroup_isolabel",
            example="8.4",
        )
        quotient = TextBox(
            name="quotient",
            label="Quotient label",
            knowl="group.quotient_isolabel",
            example="16.5",
        )
        ambient = TextBox(
            name="ambient",
            label="Ambient label",
            knowl="group.ambient_isolabel",
            example="128.207",
        )
        subgroup_order = TextBox(
            name="subgroup_order",
            label="Subgroup order",
            knowl="group.order",
            example="8",
            example_span="4, or a range like 3..5",
        )
        quotient_order = TextBox(
            name="quotient_order",
            label="Subgroup index",
            knowl="group.subgroup.index",
            example="16",
        )
        ambient_order = TextBox(
            name="ambient_order",
            label="Ambient order",
            knowl="group.order",
            example="128",
        )
        nontrivproper = YesNoBox(name="nontrivproper", label=display_knowl('group.trivial_subgroup', 'Non-trivial') + " " + display_knowl('group.proper_subgroup', 'proper'))

        self.refine_array = [
            [subgroup, subgroup_order, cyclic, abelian, solvable],
            [normal, characteristic, perfect, maximal, central, nontrivproper],
            [ambient, ambient_order, direct, split, hall, sylow],
            [
                quotient,
                quotient_order,
                quotient_cyclic,
                quotient_abelian,
                quotient_solvable,
                minimal_normal,
            ],
        ]

    def search_types(self, info):
        # Note: info will never be None, since this isn't accessible on the browse page
        return [("Subgroups", "Search again"), ("RandomSubgroup", "Random subgroup")]


class ComplexCharSearchArray(SearchArray):
    sorts = [("", "group", ['group_order', 'group_counter', 'dim', 'label']),
             ("dim", "degree", ['dim', 'group_order', 'group_counter', 'label'])]
    def __init__(self):
        faithful = YesNoBox(name="faithful", label="Faithful", knowl="group.representation.faithful")
        dim = TextBox(
            name="dim",
            label="Degree",
            knowl="group.representation.complex_char_deg",
            example="3",
            example_span="3, or a range like 3..5"
        )
        conductor = TextBox(
            name="cyclotomic_n",
            label="Conductor",
            knowl="group.representation.cyclotomic_n",
            example="4",
            example_span="4, or a range like 3..5"
        )
        indicator = TextBox(
            name="indicator",
            label="Type",
            knowl="group.representation.type",
            example="R, C, S, or -1, 0, 1",
        )
        group = TextBox(
            name="group",
            label="Group",
            knowl="group.name",
            example="128.207",
        )
        image_isoclass = TextBox(
            name="image_isoclass",
            label="Image",
            knowl="group.representation.image",
            example="12.4",
        )
        image_order = TextBox(
            name="image_order",
            label="Image Order (Kernel Index)",
            knowl="group.representation.image",
            example="4",
            example_span="4, or a range like 3..5",
        )
        kernel_order = TextBox(
            name="kernel_order",
            label="Kernel Order",
            knowl="group.representation.kernel",
            example="4, or a range like 3..5",
        )
        center_order = TextBox(
            name="center_order",
            label="Center Order",
            knowl="group.representation.center",
            example="4",
            example_span="4, or a range line 3..5",
        )
        center_index = TextBox(
            name="center_index",
            label="Center Index",
            knowl="group.representation.center",
            example="4",
            example_span="4, or a range line 3..5",
        )
        #nt = TextBox(
        #    name="nt",
        #    label="Minimum Perm. Rep.",
        #    knowl="group.representation.min_perm_rep",
        #    example="[4,2]",
        #)

        self.refine_array = [
            [dim, indicator, faithful,conductor],
            [group, image_isoclass, image_order, kernel_order],
            [center_order, center_index] #, nt]

        ]
    def search_types(self, info):
        # Note: since we don't access this from the browse page, info will never be None
        return [("ComplexCharacters", "Search again"), ("RandomComplexCharacter", "Random")]


class ConjugacyClassSearchArray(SearchArray):
    sorts = [
        ("", "group", ['group_order','group_counter','order','size']),
        ("order", "order", ['order', 'group_order', 'group_counter','size']),
        ("size", "size", ['size', 'order', 'group_order', 'group_counter']),
    ]

    def __init__(self):
        group = TextBox(
            name="group",
            label="Group",
            knowl="group.name",
            example="128.207, or 12",
        )
        order = TextBox(
            name="order",
            label="Order",
            knowl="group.order_conjugacy_class",
            example="3",
            example_span="3, or a range like 3..5"
        )
        size = TextBox(
            name="size",
            label="Size",
            knowl="group.size_conjugacy_class",
            example="4",
            example_span="4, or a range like 3..5"
        )

        self.refine_array = [
            [group,order,size]
        ]
    def search_types(self, info):
        # Note: since we don't access this from the browse page, info will never be None
        return [("ConjugacyClasses", "Search again")]


def abstract_group_namecache(labels, cache=None, reverse=None):
    # Note that, when called by knowl_cache from transitive_group.py,
    # the resulting cache will have two types of records: abstract group ones with keys
    # "label", "order" and "tex_name", and transitive group ones with keys
    # "label", "order", "gapid" and "pretty".  The labels will be of different kinds (6.1 vs 3T2),
    # and serve as keys for the cache dictionary.
    if cache is None:
        cache = {}
    for rec in db.gps_groups.search({"label": {"$in": labels}}, ["label", "order", "tex_name"]):
        label = rec["label"]
        cache[label] = rec
        if reverse is not None:
            tex_name = rec.get("tex_name")
            for nTj in reverse[label]:
                if "pretty" in cache[nTj]:
                    continue
                cache[nTj]["pretty"] = f"${tex_name}$" if tex_name else ""
    return cache

def sub_display_knowl(label, name=None):
    if not name:
        name = f"Subgroup {label}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=sub_data">{name}</a>'

def cc_data(gp, label, typ="complex", representative=None):
    # representative allows us to use this mechanism for Galois
    # group conjugacy classes as well
    if typ == "rational":
        wag = WebAbstractGroup(gp)
        rcc = wag.conjugacy_class_divisions
        if not rcc:
            return "Data for conjugacy class {} not found.".format(label)
        for div in rcc:
            if div.label == label:
                break
        else:
            return "Data for conjugacy class {} missing.".format(label)
        classes = div.classes
        wacc = classes[0]
        mult = len(classes)
        ans = "<h3>Rational conjugacy class {}</h3>".format(label)
        if mult > 1:
            ans += "<br>Rational class is a union of {} conjugacy classes".format(mult)
            ans += "<br>Total size of class: {}".format(wacc.size * mult)
        else:
            ans += "<br>Rational class is a single conjugacy class"
            ans += "<br>Size of class: {}".format(wacc.size)
    else:
        wacc = WebAbstractConjClass(gp, label)
        if not wacc:
            return "Data for conjugacy class {} not found.".format(label)
        ans = "<h3>Conjugacy class {}</h3>".format(label)
        ans += "<br>Size of class: {}".format(wacc.size)
    ans += "<br>Order of elements: {}".format(wacc.order)
    if wacc.centralizer is None:
        ans += "<br>Centralizer: not computed"
    else:
        group = cc_data_to_gp_label(wacc.group_order,wacc.group_counter)
        centralizer = f"{group}.{wacc.centralizer}"
        wcent = WebAbstractSubgroup(centralizer)
        ans += "<br>Centralizer: {}".format(
            sub_display_knowl(centralizer, "$" + wcent.subgroup_tex + "$")
        )

    if representative:
        ans += "<br>Representative: "+representative
    elif wacc.representative is None:
        ans += "<br>Representative: not computed"
    else:
        if label == '1A':
            ans += "<br>Representative: id"
        else:
            gp_value = WebAbstractGroup(gp)
            repn = gp_value.decode(wacc.representative, as_str=True)
            ans += "<br>Representative: {}".format("$" + repn + "$")
    return Markup(ans)


def rchar_data(label):
    mychar = WebAbstractRationalCharacter(label)
    ans = "<h3>Rational character {}</h3>".format(label)
    ans += "<br>Degree: {}".format(mychar.qdim)
    if mychar.faithful:
        ans += "<br>Faithful character"
    else:
        ans += "<br>Not faithful"
    ans += "<br>Multiplicity: {}".format(mychar.multiplicity)
    ans += "<br>Schur index: {}".format(mychar.schur_index)

    # Currently the data for nt is broken due to a bug in the compute code
    #nt = mychar.nt
    #ans += "<br>Smallest container: {}T{}".format(nt[0], nt[1])

    #if mychar._data.get("image"):
    #    txt = "Image"
    #    imageknowl = (
    #        '<a title = "{0} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=qrep_data&args={0}">{0}</a>'.format(mychar.image)
    #    )
    #    if mychar.schur_index > 1:
    #        txt = r"Image of ${}\ *\ ${}".format(mychar.schur_index, label)
    #    ans += "<br>{}: {}".format(txt, imageknowl)
    #else:
    #    ans += "<br>Image: not computed"
    return Markup(ans)


def cchar_data(label):
    from lmfdb.number_fields.web_number_field import formatfield
    mychar = WebAbstractCharacter(label)
    gplabs = label.split(".")
    gplabel = ".".join(gplabs[:2])
    ans = "<h3>Complex character {}</h3>".format(label)
    ans += "<br>Degree: {}".format(mychar.dim)
    if mychar.faithful:
        ans += "<br>Faithful character"
    else:
        if mychar.kernel is None:
            ans += "<br>Not faithful but kernel not computed."
        else:
            ker = WebAbstractSubgroup(f"{mychar.group}.{mychar.kernel}")
            ans += "<br>Not faithful with kernel {}".format(
                sub_display_knowl(ker.label, "$" + ker.subgroup_tex + "$")
            )

    # Currently the data for nt is broken due to a bug in the compute code
    #nt = mychar.nt
    ans += "<br>Frobenius-Schur indicator: {}".format(mychar.indicator)
    #ans += "<br>Smallest container: {}T{}".format(nt[0], nt[1])
    ans += "<br>Field of character values: {}".format(formatfield(mychar.field))
    #ans += "<br>Rational character: {}".format(q_char(label))
    ans += f'<div align="right"><a href="{url_for("abstract.Qchar_table", label=gplabel, char_highlight=q_char(label))}">{q_char(label)} rational character</a></div>'
    #if mychar._data.get("image"):
    #    imageknowl = (
    #        '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=crep_data&args=%s">%s</a>'
    #        % (mychar.image, mychar.image, mychar.image)
    #    )
    #    ans += "<br>Image: {}".format(imageknowl)
    #else:
    #    ans += "<br>Image: not computed"
    return Markup(ans)


def crep_data(label):
    info = db.gps_crep.lookup(label)
    ans = r"<h3>Subgroup of $\GL_{{ {}  }}(\C)$: {}</h3>".format(info["dim"], label)
    ans += "<br>Order: ${}$".format(info["order"])
    ans += "<br>Abstract group: {}".format(
        abstract_group_display_knowl(info["group"], info["group"])
    )
    ans += "<br>Group name: ${}$".format(group_names_pretty(info["group"]))
    ans += "<br>Dimension: ${}$".format(info["dim"])
    ans += "<br>Irreducible: {}".format(info["irreducible"])
    ans += f"<br>{pluralize(len(info['gens']), 'Matrix generator', omit_n=True)}: "
    N = info["cyc_order_mat"]
    genlist = ["$" + dispcyclomat(N, gen) + "$" for gen in info["gens"]]
    ans += ",".join(genlist)
    return Markup(ans)


def qrep_data(label):
    info = db.gps_qrep.lookup(label)
    ans = r"<h3>Subgroup of $\GL_{{ {}  }}(\Q)$: {}</h3>".format(info["dim"], label)
    ans += "<br>Order: ${}$".format(info["order"])
    ans += "<br>Abstract group: {}".format(
        abstract_group_display_knowl(info["group"], info["group"])
    )
    ans += "<br>Group name: ${}$".format(group_names_pretty(info["group"]))
    ans += "<br>Dimension: ${}$".format(info["dim"])
    ans += "<br>Irreducible: {}".format(info["irreducible"])
    ans += f"<br>{pluralize(len(info['gens']), 'Matrix generator', omit_n=True)}: "
    genlist = ["$" + dispZmat(gen) + "$" for gen in info["gens"]]
    ans += ",".join(genlist)
    return Markup(ans)


def sub_data(label):
    label = label.split(".")
    return Markup(shortsubinfo(".".join(label[:2]), ".".join(label[2:])))


def group_data(label, ambient=None, aut=False, profiledata=None):
    gp = None
    quotient_tex = None
    if profiledata is None:
        quotient_label = "None"
    else:
        profiledata = profiledata.split("$")
        for i, c in enumerate(profiledata):
            if c in ["None", "?"]:
                profiledata[i] = None
        if len(profiledata) == 7 and profiledata[3] is not None:
            quotient_label = profiledata[3]
            quotient_tex = profiledata[5]
        else:
            quotient_label = "None"
    if label == "None":
        if profiledata is None:
            return Markup("Error in group_data function: No label or profiledata")
        if len(profiledata) < 3:
            return Markup("Error in group_data function: Not enough profiledata")
        order = int(profiledata[0].split(".")[0])
        # Now restore profiledata[0] to be None, used in sub_matches below
        profiledata[0] = None
        tex_name = profiledata[2]
        if tex_name is None:
            ans = "Unidentified group<br />"
        else:
            ans = f"Group ${tex_name}$<br />"
        ans += f"Order: {order}<br />"
        if profiledata[1] is None:
            ans += "Isomorphism class has not been identified<br />"
        else:
            # TODO: add search link to groups with this order and hash
            ans += f"{display_knowl('group.hash', 'Hash')} : {profiledata[1]}<br />"
        isomorphism_label = "Subgroups with this data:"
    else:
        if label.startswith("ab/"):
            data = canonify_abelian_label(label[3:])
            url = url_for("abstract.by_abelian_label", label=label[3:])
        else:
            data = None
            url = url_for("abstract.by_label", label=label)
        gp = WebAbstractGroup(label, data=data)
        # dealing with groups identified in magma but not in gap so can't do live pages˚
        ord = label.split(".")[0]
        if missing_subs(label) and gp.source == "Missing":
            ans = 'The group {} is not available in GAP, but see the list of <a href="{}">{}</a>.'.format(
                label,
                f"/Groups/Abstract/?subgroup_order={ord}&ambient={ambient}&search_type=Subgroups",
                "subgroups with this order")
            return Markup(ans)
        ans = f"Group ${gp.tex_name}$: "
        ans += create_boolean_string(gp, type="knowl")
        ans += f"<br />Label: {gp.label}<br />"
        order = gp.order
        ans += f"Order: {order}<br />"
        ans += f"Exponent: {gp.exponent}<br />"
        if quotient_label == "None":
            if aut == "True":
                isomorphism_label = "Representatives of classes of subgroups up to automorphism with this isomorphism type: "
            else:
                isomorphism_label = "Representatives of classes of subgroups up to conjugation with this isomorphism type: "
        else:
            if aut == "True":
                isomorphism_label = "Representatives of classes of subgroups up to automorphism with this isomorphism type and quotient: "
            else:
                isomorphism_label = "Representatives  of classes of subgroups up to conjugation with this isomorphism type and quotient: "
    if quotient_label != "None":
        if quotient_label.startswith("ab/"):
            data = canonify_abelian_label(quotient_label[3:])
            quotient_url = url_for("abstract.by_abelian_label", label=quotient_label[3:])
        else:
            data = None
            quotient_url = url_for("abstract.by_label", label=quotient_label)
        qgp = WebAbstractGroup(quotient_label, data=data)
        if not quotient_tex:
            quotient_tex = qgp.tex_name
        ans += f"Quotient ${quotient_tex}$: "
        ans += create_boolean_string(qgp, type="knowl")
        ans += f"<br />Quotient label: {qgp.label}<br />"
        ans += f"Quotient order: {qgp.order}<br />"
        ans += f"Quotient exponent: {qgp.exponent}<br />"
    elif profiledata is not None and len(profiledata) == 6:
        if quotient_tex in [None, "?"]:
            quotient_tex = profiledata[5]
        if quotient_tex in [None, "?"]:
            ans += "identified quotient<br />"
        else:
            ans += f"Quotient ${quotient_tex}$<br />"
        ambient_order = int(ambient.split(".")[0])
        ans += f"Quotient order: {ambient_order // order}<br />"
        if profiledata[4] is None:
            ans += "Quotient isomorphism class has not been identified<br />"
        else:
            # TODO: add hash knowl and search link to groups with this order and hash
            ans += f"Quotient hash: {profiledata[4]}<br />"

    if gp and not gp.live():
        if ambient is None:
            if gp.number_subgroups is not None:
                ans += "It has {} subgroups".format(gp.number_subgroups)
                if gp.number_normal_subgroups is not None:
                    if gp.number_normal_subgroups < gp.number_subgroups:
                        ans += " in {} conjugacy classes, {} normal, ".format(
                            gp.number_subgroup_classes, gp.number_normal_subgroups
                        )
                    else:
                        ans += ", all normal, "
                    if gp.number_characteristic_subgroups is not None:
                        if gp.number_characteristic_subgroups < gp.number_normal_subgroups:
                            ans += str(gp.number_characteristic_subgroups)
                        else:
                            ans += "all"
                        ans += " characteristic.<br />"
                    else:
                        ans = ans[:-2] + ".<br />"
                else:
                    ans += ".<br />"
        else:
            ambient = WebAbstractGroup(ambient)

            def sub_matches(H):
                if profiledata is None:
                    return H.subgroup == label
                if len(profiledata) == 3 and label != "None":
                    return H.subgroup == label
                if len(profiledata) == 7 and label != "None" and quotient_label != "None":
                    return H.subgroup == label and H.quotient == quotient_label
                return all(a == b for a, b in zip(profiledata, (H.subgroup, H.subgroup_hash, H.subgroup_tex, H.quotient, H.quotient_hash, H.quotient_tex)))

            subs = [H for H in ambient.subgroups.values() if sub_matches(H)]
            if aut == "True" and not ambient.outer_equivalence:
                # TODO: need to deal with non-canonical labels
                subs = [H for H in subs if H.label.split(".")[-1] == "a1"]
            subs.sort(key=lambda H: label_sortkey(H.label))
            ans += '<div align="right">'
            ans += isomorphism_label
            for H in subs:
                ans += '<a href="{}">{}</a>&nbsp;'.format(
                    url_for("abstract.by_subgroup_label", label=H.label), H.label
                )
            ans += "</div><br />"
    else:
        ans += '<a href="{}">{}</a>&nbsp;'.format(
            f"/Groups/Abstract/?subgroup_order={order}&ambient={ambient}&search_type=Subgroups",
            "Subgroups with this order")
    if label != "None":
        ans += f'<div align="right"><a href="{url}">{label} home page</a></div>'
    if quotient_label != "None":
        ans += f'<div align="right"><a href="{quotient_url}">{quotient_label} home page</a></div>'
    return Markup(ans)

def semidirect_data(label):
    gp = WebAbstractGroup(label)
    ans = f"Semidirect product expressions for ${gp.tex_name}$:<br />\n"
    for sub, cnt, labels in gp.semidirect_products:
        ans += fr"{sub.knowl(paren=True)} $\,\rtimes\,$ {sub.quotient_knowl(paren=True)}"
        if cnt > 1:
            ans += f" in {cnt} ways"
        ans += ' via '
        ans += ", ".join(f'<a href="{url_for("abstract.by_subgroup_label", label=label+"."+sublabel)}">{sublabel}</a>' for sublabel in labels)
        ans += "<br />\n"
    return Markup(ans)

def nonsplit_data(label):
    gp = WebAbstractGroup(label)
    ans = f"Nonsplit product expressions for ${gp.tex_name}$:<br />\n"
    ans += "<table>\n"
    for sub, cnt, labels in gp.nonsplit_products:
        ans += fr"<tr><td>{sub.knowl(paren=True)} $\,.\,$ {sub.quotient_knowl(paren=True)}</td><td>"
        if cnt > 1:
            ans += f" in {cnt} ways"
        ans += ' via </td>'
        ans += "".join([f'<td><a href="{url_for("abstract.by_subgroup_label", label=label+"."+sublabel)}">{sublabel}</a></td>' for sublabel in labels])
        ans += "</tr>\n"
    ans += "</table>"
    return Markup(ans)

def possibly_split_data(label):
    gp = WebAbstractGroup(label)
    ans = f"Possibly nonsplit product expressions for ${gp.tex_name}$:<br />\n"
    ans += "<table>\n"
    for sub, cnt, labels in gp.possibly_split_products:
        ans += fr"<tr><td>{sub.knowl(paren=True)} $\,.\,$ {sub.quotient_knowl(paren=True)}</td><td>"
        if cnt > 1:
            ans += f" in {cnt} ways"
        ans += ' via </td>'
        ans += "".join([f'<td><a href="{url_for("abstract.by_subgroup_label", label=label+"."+sublabel)}">{sublabel}</a></td>' for sublabel in labels])
        ans += "</tr>\n"
    ans += "</table>"
    return Markup(ans)

def trans_expr_data(label):
    tex_name = db.gps_groups.lookup(label, "tex_name")
    ans = f"Transitive permutation representations of ${tex_name}$:<br />\n"
    ans += f"<table>\n<tr><th>{display_knowl('gg.label', 'Label')}</th><th>{display_knowl('gg.parity', 'Parity')}</th><th>{display_knowl('gg.primitive', 'Primitive')}</th></tr>\n"
    for rec in db.gps_transitive.search({"abstract_label":label}, ["label", "parity", "prim"]):
        ans += f'<tr><td><a href="{url_for("galois_groups.by_label", label=rec["label"])}">{rec["label"]}</a></td><td class="right">${rec["parity"]}$</td><td class="center">{"yes" if rec["prim"] == 1 else "no"}</td></tr>' # it would be nice to use &#x2713; and &#x2717; (check and x), but if everything is no then it's confusing
    ans += "</table>"
    return Markup(ans)

def aut_data(label):
    gp = WebAbstractGroup(label)
    ans = f"${gp.tex_name}$ as an automorphism group:<br />\n"
    for aut, disp in gp.as_aut_gp:
        ans += f'<a href="{url_for("abstract.by_label", label=aut)}">${disp}$</a><br />\n'
    return Markup(ans)

def dyn_gen(f, args):
    r"""
    Called from the generic dynamic knowl.

    INPUT:

    - ``f`` is the name of a function to call, which has to be in ``flist``,
      which is at the bottom of this file

    - ``args`` is a string with the arguments, which are concatenated together
      with ``%7C``, which is the encoding of the pipe symbol
    """
    func = flist[f]
    arglist = args.split("|")
    return func(*arglist)


# list of legal dynamic knowl functions
flist = {
    "cc_data": cc_data,
    "sub_data": sub_data,
    "rchar_data": rchar_data,
    "cchar_data": cchar_data,
    "group_data": group_data,
    "crep_data": crep_data,
    "qrep_data": qrep_data,
    "semidirect_data": semidirect_data,
    "nonsplit_data": nonsplit_data,
    "possibly_split_data": possibly_split_data,
    "aut_data": aut_data,
    "trans_expr_data": trans_expr_data,
}


def order_stats_list_to_string(o_list):
    s = ""
    for pair in o_list:
        assert len(pair) == 2
        s += "%s^%s" % (pair[0], pair[1])
        if o_list.index(pair) != len(o_list) - 1:
            s += ","
    return s


sorted_code_names = ['presentation', 'permutation', 'matrix', 'transitive']

Fullname = {'magma': 'Magma', 'gap': 'Gap'}
Comment = {'magma': '//', 'gap': '#'}
