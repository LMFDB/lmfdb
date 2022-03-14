# -*- coding: utf-8 -*-

import re

import time
from collections import defaultdict, Counter
from flask import (
    Markup,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    abort,
)
from six import BytesIO
from string import ascii_lowercase
from sage.all import ZZ, latex, factor, prod, Permutations
from sage.misc.cachefunc import cached_function

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    flash_error,
    to_dict,
    display_knowl,
    SearchArray,
    TextBox,
    SneakyTextBox,
    CountBox,
    YesNoBox,
    parse_ints,
    parse_bool,
    clean_input,
    parse_regex_restricted,
    parse_bracketed_posints,
    parse_noop,
    dispZmat,
    dispcyclomat,
    search_wrap,
    web_latex,
)
from lmfdb.utils.search_parsing import parse_multiset
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, CheckCol, SpacerCol, ProcessedCol, SearchCol, MultiProcessedCol, ColGroup
from lmfdb.api import datapage
from . import abstract_page  # , abstract_logger
from .web_groups import (
    WebAbstractCharacter,
    WebAbstractConjClass,
    WebAbstractGroup,
    WebAbstractRationalCharacter,
    WebAbstractSubgroup,
    group_names_pretty,
)
from .stats import GroupStats


abstract_group_label_regex = re.compile(r"^(\d+)\.(([a-z]+)|(\d+))$")
abstract_subgroup_label_regex = re.compile(
    r"^(\d+)\.([a-z0-9]+)\.(\d+)\.[a-z]+(\d+)(\.[a-z]+\d+)?$"
)
# order_stats_regex = re.compile(r'^(\d+)(\^(\d+))?(,(\d+)\^(\d+))*')


def yesno(val):
    return "yes" if val else "no"


# For dynamic knowls
@app.context_processor
def ctx_abstract_groups():
    return {
        "cc_data": cc_data,
        "sub_data": sub_data,
        "rchar_data": rchar_data,
        "cchar_data": cchar_data,
        "dyn_gen": dyn_gen,
        "semidirect_expressions_knowl": semidirect_expressions_knowl,
        "semidirect_data": semidirect_data,
        "nonsplit_expressions_knowl": nonsplit_expressions_knowl,
        "nonsplit_data": nonsplit_data,
        "autgp_expressions_knowl": autgp_expressions_knowl,
        "aut_data": aut_data,
    }


def learnmore_list():
    return [
        ("Source and acknowledgements", url_for(".how_computed_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Abstract  group labeling", url_for(".labels_page")),
    ]


def learnmore_list_remove(matchstring):
    return filter(lambda t: t[0].find(matchstring) < 0, learnmore_list())


def subgroup_label_is_valid(lab):
    return abstract_subgroup_label_regex.fullmatch(lab)


def label_is_valid(lab):
    return abstract_group_label_regex.fullmatch(lab)


def get_bread(tail=[]):
    base = [("Groups", url_for(".index")), ("Abstract", url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def display_props(proplist):
    if len(proplist) == 1:
        return proplist[0]
    elif len(proplist) == 2:
        return " and ".join(proplist)
    else:
        return ", ".join(proplist[:-1]) + f", and {proplist[-1]}"


def find_props(
    gp,
    overall_order,
    impl_order,
    overall_display,
    impl_display,
    implications,
    hence_str,
    show,
):
    props = []
    noted = set()
    for prop in overall_order:
        if not getattr(gp, prop) or prop in noted or prop not in show:
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
            impl_display.get(B, overall_display.get(B))
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


def get_group_prop_display(gp):
    # We want elementary and hyperelementary to display which primes, but only once
    elementaryp = ",".join(str(p) for (p, e) in ZZ(gp.elementary).factor())
    hyperelementaryp = ",".join(
        str(p)
        for (p, e) in ZZ(gp.hyperelementary).factor()
        if not p.divides(gp.elementary)
    )
    if (
        gp.order == 1
    ):  # here it will be implied from cyclic, so both are in the implication list
        elementaryp = " (for every $p$)"
        hyperelementaryp = ""
    elif gp.pgroup:  # We don't display p since there's only one in play
        elementaryp = hyperelementaryp = ""
    elif gp.cyclic:  # both are in the implication list
        elementaryp = f" ($p = {elementaryp}$)"
        if gp.elementary == gp.hyperelementary:
            hyperelementaryp = ""
        else:
            hyperelementaryp = f" (also for $p = {hyperelementaryp}$)"
    elif gp.is_elementary:  # Now elementary is a top level implication
        elementaryp = f" for $p = {elementaryp}$"
        if gp.elementary == gp.hyperelementary:
            hyperelementaryp = ""
        else:
            hyperelementaryp = f" (also for $p = {hyperelementaryp}$)"
    elif gp.hyperelementary:  # Now hyperelementary is a top level implication
        hyperelementaryp = f" for $p = {hyperelementaryp}$"
    overall_display = {
        "cyclic": display_knowl("group.cyclic", "cyclic"),
        "abelian": display_knowl("group.abelian", "abelian"),
        "nonabelian": display_knowl("group.abelian", "nonabelian"),
        "nilpotent": f"{display_knowl('group.nilpotent', 'nilpotent')} of class {gp.nilpotency_class}",
        "supersolvable": display_knowl("group.supersolvable", "supersolvable"),
        "monomial": display_knowl("group.monomial", "monomial"),
        "solvable": f"{display_knowl('group.solvable', 'solvable')} of {display_knowl('group.derived_series', 'length')} {gp.derived_length}",
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


def get_group_impl_display(gp):
    # Mostly we display things the same in implication lists, but there are a few extra parentheses
    return {
        "nilpotent": f"{display_knowl('group.nilpotent', 'nilpotent')} (of class {gp.nilpotency_class})",
        "solvable": f"{display_knowl('group.solvable', 'solvable')} (of {display_knowl('group.derived_series', 'length')} {gp.derived_length})",
    }


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
        "direct": f"a {display_knowl('group.direct_product', 'direct factor')}",
        "semidirect": f"a {display_knowl('group.semidirect_product', 'semidirect factor')}",
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
    if type == "normal":
        overall_display.update(get_group_prop_display(sgp.sub))
        impl_display = get_group_impl_display(sgp.sub)
    else:
        impl_display = {}

    assert set(overall_display) == set(overall_order)
    hence_str = display_knowl(
        "group.subgroup_properties_interdependencies", "hence"
    )  # This needs to contain both kind of implications....
    props = find_props(
        sgp,
        overall_order,
        impl_order,
        overall_display,
        impl_display,
        implications,
        hence_str,
        show=overall_display,
    )
    if type == "normal":
        return f"The subgroup is {display_props(props)}."
    else:
        return f"This subgroup is {display_props(props)}."


# function to create string of group characteristics
def create_boolean_string(gp, type="normal"):
    # We totally order the properties in two ways: by the order that they should be listed overall,
    # and by the order they should be listed in implications
    # For the first order, it's important that A come before B whenever A => B
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
    short_show = set(
        [
            "cyclic",
            "abelian",
            "nonabelian",
            "nilpotent",
            "solvable",
            "nab_simple",
            "nonsolvable",
            "nab_perfect",
        ]
    )
    short_string = type == "knowl"

    # Implications should give edges of a DAG, and should be listed in the group.properties_interdependencies knowl
    implications = group_prop_implications
    for A, L in implications.items():
        for B in L:
            assert A in overall_order and B in overall_order
            assert overall_order.index(A) < overall_order.index(B)
            assert B in impl_order

    overall_display = get_group_prop_display(gp)
    impl_display = get_group_impl_display(gp)
    assert set(overall_display) == set(overall_order)

    hence_str = display_knowl("group.properties_interdependencies", "hence")
    props = find_props(
        gp,
        overall_order,
        impl_order,
        overall_display,
        impl_display,
        implications,
        hence_str,
        show=(short_show if short_string else overall_display),
    )
    if type == "ambient":
        return f"The ambient group is {display_props(props)}."
    elif type == "quotient":
        return f"The quotient is {display_props(props)}"
    elif type == "knowl":
        return f"{display_props(props)}."
    else:
        return f"This group is {display_props(props)}."


def url_for_label(label):
    if label == "random":
        return url_for(".random_abstract_group")
    return url_for("abstract.by_label", label=label)


def url_for_subgroup_label(label):
    if label == "random":
        return url_for(".random_abstract_subgroup")
    return url_for("abstract.by_subgroup_label", label=label)


@abstract_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=GroupsSearchArray())
    if request.args:
        info["search_type"] = search_type = info.get(
            "search_type", info.get("hst", "List")
        )
        if search_type in ["List", "Random"]:
            return group_search(info)
        elif search_type in ["Subgroups", "RandomSubgroup"]:
            info["search_array"] = SubgroupSearchArray()
            return subgroup_search(info)
    info["stats"] = GroupStats()
    info["count"] = 50
    info["order_list"] = ["1-63", "64-127", "128-255", "256-383", "384-511"]
    info["nilp_list"] = range(1, 8)
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
    dblabel = db.gps_groups.lucky(
        {"abelian": True, "primary_abelian_invariants": primary}, "label"
    )
    if dblabel is None:
        return render_abstract_group("ab/" + label, data=primary)
    else:
        return redirect(url_for(".by_label", label=dblabel))


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
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    return render_template(
        "character_table_page.html",
        gp=gp,
        title="Character table for %s" % label,
        bread=get_bread([("Character table", " ")]),
        learnmore=learnmore_list(),
    )


@abstract_page.route("/Qchar_table/<label>")
def Qchar_table(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    return render_template(
        "rational_character_table_page.html",
        gp=gp,
        title="Rational character table for %s" % label,
        bread=get_bread([("Rational character table", " ")]),
        learnmore=learnmore_list(),
    )


@abstract_page.route("/diagram/<label>")
def sub_diagram(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(gp, conj=True, aut=False)
    info = {"dojs": dojs, "type": "conj"}
    info.update(display_opts)
    return render_template(
        "diagram_page.html",
        info=info,
        title="Diagram of subgroups up to conjugation for group %s" % label,
        bread=get_bread([("Subgroup diagram", " ")]),
        learnmore=learnmore_list(),
    )

@abstract_page.route("/autdiagram/<label>")
def aut_diagram(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(gp, conj=False, aut=True)
    info = {"dojs": dojs, "type": "aut"}
    info.update(display_opts)
    return render_template(
        "diagram_page.html",
        info=info,
        title="Diagram of subgroups up to automorphism for group %s" % label,
        bread=get_bread([("Subgroup diagram", " ")]),
        learnmore=learnmore_list(),
    )


def show_type(ab, nil, solv, smith, nilcls, dlen, clen):
    # arguments - ["abelian", "nilpotent", "solvable", "smith_abelian_invariants", "nilpotency_class", "derived_length", "composition_length"]
    if ab:
        return f'Abelian - {len(smith)}'
    elif nil:
        return f'Nilpotent - {nilcls}'
    elif solv:
        return f'Solvable - {dlen}'
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
    # or as product of cyclic groups
    if CYCLIC_PRODUCT_RE.fullmatch(jump):
        invs = [n.strip() for n in jump.upper().replace("C", "").replace("X", "*").replace("^", "_").split("*")]
        return redirect(url_for(".by_abelian_label", label = ".".join(invs)))
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
                raise RuntimeError("The group %s has not yet been added to the database." % jump)
    raise ValueError("%s is not a valid name for a group; see %s for a list of possible families" % (jump, display_knowl('group.families', 'here')))

def group_download(info):
    t = "Stub"
    bread = get_bread([("Jump", "")])
    return render_template(
        "single.html",
        kid="rcs.groups.abstract.source",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )

def show_factor(n):
    return f"${latex(ZZ(n).factor())}$"

def get_url(label):
    return url_for(".by_label", label=label)

def get_sub_url(label):
    return url_for(".by_subgroup_label", label=label)

group_columns = SearchColumns([
    LinkCol("label", "group.label", "Label", get_url, default=True),
    MathCol("tex_name", "group.name", "Name", default=True),
    ProcessedCol("order", "group.order", "Order", show_factor, default=True, align="center"),
    ProcessedCol("exponent", "group.exponent", "Exponent", show_factor, default=True, align="center"),
    MathCol("nilpotency_class", "group.nilpotent", "Nilp. class", short_title="nilpotency class"),
    MathCol("derived_length", "group.derived_series", "Der. length", short_title="derived length"),
    MathCol("composition_length", "group.chief_series", "Comp. length", short_title="composition length"),
    MathCol("rank", "group.rank", "Rank"),
    MathCol("number_conjugacy_classes", "group.conjugacy_class", r"$\card{\mathrm{conj}(G)}$", default=True, short_title="conjugacy classes"),
    MathCol("number_subgroup_classes", "group.subgroup", r"Subgroup classes"),
    SearchCol("center_label", "group.center", "Center", default=True, align="center"),
    SearchCol("central_quotient", "group.central_quotient_isolabel", "Central quotient", align="center"),
    SearchCol("commutator_label", "group.commutator_isolabel", "Commutator", align="center"),
    SearchCol("abelian_quotient", "group.abelianization_isolabel", "Abelianization", align="center"),
    ProcessedCol("outer_order", "group.outer_aut", r"$\card{\mathrm{Out}(G)}$", show_factor, default=True, align="center", short_title="outer automorphisms"),
    ProcessedCol("aut_order", "group.automorphism", r"$\card{\mathrm{Aut}(G)}$", show_factor, align="center", short_title="automorphisms"),
    MultiProcessedCol("type", "group.type", "Type - length",
                      ["abelian", "nilpotent", "solvable", "smith_abelian_invariants", "nilpotency_class", "derived_length", "composition_length"],
                      show_type,
                      default=True, align="center")])
group_columns.dummy_download=True

@search_wrap(
    table=db.gps_groups,
    title="Abstract group search results",
    err_title="Abstract groups search input error",
    columns=group_columns,
    shortcuts={"jump": group_jump, "download": group_download},
    bread=lambda: get_bread([("Search Results", "")]),
    learnmore=learnmore_list,
    #  credit=lambda:credit_string,
    url_for_label=url_for_label,
)
def group_search(info, query={}):
    group_parse(info, query)


def group_parse(info, query):
    parse_ints(info, query, "order", "order")
    parse_ints(info, query, "exponent", "exponent")
    parse_ints(info, query, "nilpotency_class", "nilpotency class")
    parse_ints(info, query, "number_conjugacy_classes", "number of conjugacy classes")
    parse_ints(info, query, "aut_order", "aut_order")
    parse_ints(info, query, "outer_order", "outer_order")
    parse_ints(info, query, "derived_length", "derived_length")
    parse_ints(info, query, "rank", "rank")
    parse_ints(info, query, "commutator_count", "commutator length")
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
    parse_regex_restricted(
        info, query, "center_label", regex=abstract_group_label_regex
    )
    parse_regex_restricted(info, query, "aut_group", regex=abstract_group_label_regex)
    parse_regex_restricted(
        info, query, "commutator_label", regex=abstract_group_label_regex
    )
    parse_regex_restricted(
        info, query, "central_quotient", regex=abstract_group_label_regex
    )
    parse_regex_restricted(
        info, query, "abelian_quotient", regex=abstract_group_label_regex
    )
    parse_regex_restricted(
        info, query, "frattini_label", regex=abstract_group_label_regex
    )
    parse_regex_restricted(info, query, "outer_group", regex=abstract_group_label_regex)
    parse_noop(info, query, "name")

subgroup_columns = SearchColumns([
    LinkCol("label", "group.subgroup_label", "Label", get_sub_url, default=True, th_class=" border-right", td_class=" border-right"),
    ColGroup("subgroup_cols", None, "Subgroup", [
        MultiProcessedCol("sub_name", "group.name", "Name",
                          ["subgroup", "subgroup_tex"],
                          lambda sub, tex: '<a href="%s">$%s$</a>' % (get_url(sub), tex),
                          default=True, short_title="Sub. name"),
        ProcessedCol("subgroup_order", "group.order", "Order", show_factor, default=True, align="center", short_title="Sub. order"),
        CheckCol("normal", "group.subgroup.normal", "norm", default=True, short_title="Sub. normal"),
        CheckCol("characteristic", "group.characteristic_subgroup", "char", default=True, short_title="Sub. characteristic"),
        CheckCol("cyclic", "group.cyclic", "cyc", default=True, short_title="Sub. cyclic"),
        CheckCol("abelian", "group.abelian", "ab", default=True, short_title="Sub. abelian"),
        CheckCol("solvable", "group.solvable", "solv", default=True, short_title="Sub. solvable"),
        CheckCol("maximal", "group.maximal_subgroup", "max", default=True, short_title="Sub. maximal"),
        CheckCol("perfect", "group.perfect", "perf", default=True, short_title="Sub. perfect"),
        CheckCol("central", "group.central", "cent", default=True, short_title="Sub. central")],
             default=True),
    SpacerCol("", default=True, th_class=" border-right", td_class=" border-right", td_style="padding:0px;", th_style="padding:0px;"), # Can't put the right border on "subgroup_cols" (since it wouldn't be full height) or "central" (since it might be hidden by the user)
    ColGroup("ambient_cols", None, "Ambient", [
        MultiProcessedCol("ambient_name", "group.name", "Name",
                          ["ambient", "ambient_tex"],
                          lambda amb, tex: '<a href="%s">$%s$</a>' % (get_url(amb), tex),
                          default=True, short_title="Ambient name"),
        ProcessedCol("ambient_order", "group.order", "Order", show_factor, default=True, align="center", short_title="Ambient order")],
             default=True),
    SpacerCol("", default=True, th_class=" border-right", td_class=" border-right", td_style="padding:0px;", th_style="padding:0px;"),
    ColGroup("quotient_cols", None, "Quotient", [
        MultiProcessedCol("quotient_name", "group.name", "Name",
                          ["quotient", "quotient_tex"],
                          lambda quo, tex: '<a href="%s">$%s$</a>' % (get_url(quo), tex) if quo else "",
                          default=True, short_title="Quo. name"),
        ProcessedCol("quotient_order", "group.order", "Order", lambda n: show_factor(n) if n else "", default=True, align="center", short_title="Quo. order"),
        CheckCol("quotient_cyclic", "group.cyclic", "cyc", default=True, short_title="Quo. cyclic"),
        CheckCol("quotient_abelian", "group.abelian", "ab", default=True, short_title="Quo. abelian"),
        CheckCol("quotient_solvable", "group.solvable", "solv", default=True, short_title="Quo. solvable"),
        CheckCol("minimal_normal", "group.maximal_quotient", "max", default=True, short_title="Quo. maximal")],
             default=True)],
    tr_class=["bottom-align", ""])
subgroup_columns.dummy_download = True

@search_wrap(
    table=db.gps_subgroups,
    title="Subgroup search results",
    err_title="Subgroup search input error",
    columns=subgroup_columns,
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
    parse_bool(info, query, "proper")
    parse_regex_restricted(info, query, "subgroup", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "ambient", regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, "quotient", regex=abstract_group_label_regex)

def factor_latex(n):
    return "$%s$" % web_latex(factor(n), False)

def diagram_js(gp, layers, display_opts, aut=False):
    ll = [
        [
            grp.subgroup,
            grp.short_label,
            grp.subgroup_tex,
            grp.count,
            grp.subgroup_order,
            gp.tex_images.get(grp.subgroup_tex, gp.tex_images["?"]),
            grp.diagramx[0] if aut else (grp.diagramx[2] if grp.normal else grp.diagramx[1]),
            grp.diagram_aut_x if aut else grp.diagram_x
        ]
        for grp in layers[0]
    ]
    orders = [sub[4] for sub in ll]
    order_ctr = Counter(orders)
    orders = sorted(order_ctr)
    Omega = {}
    by_Omega = defaultdict(list)
    for n in orders:
        W = sum(e for (p,e) in n.factor())
        Omega[n] = W
        by_Omega[W].append(n)
    # We would normally make order_lookup a dictionary, but we're passing it to the horrible language known as javascript
    order_lookup = [[n, Omega[n], by_Omega[Omega[n]].index(n)] for n in orders]
    max_width = max(sum(order_ctr[n] for n in by_Omega[W]) for W in by_Omega)
    display_opts["w"] = min(100 * max_width, 20000)
    display_opts["h"] = 160 * len(by_Omega)

    return [ll, layers[1]], order_lookup, len(by_Omega)

def diagram_js_string(gp, conj, aut):
    glist = [[],[]]
    display_opts = {}
    if aut:
        glist[1], order_lookup, num_layers = diagram_js(gp, gp.subgroup_lattice_aut, display_opts, aut=True)
    # We call conj second so that it overrides w and h, since it will be bigger
    if conj and not gp.outer_equivalence:
        glist[0], order_lookup, num_layers = diagram_js(gp, gp.subgroup_lattice, display_opts)
    if not glist[0] and not glist[1]:
        order_lookup = []
        num_layers = 0
    return f'var [sdiagram,glist] = make_sdiagram("subdiagram", "{gp.label}", {glist}, {order_lookup}, {num_layers});', display_opts

# Writes individual pages
def render_abstract_group(label, data=None):
    info = {}
    if data is None:
        label = clean_input(label)
        gp = WebAbstractGroup(label)
    elif isinstance(data, list): # abelian group
        gp = WebAbstractGroup(label, data=data)
    if gp.is_null():
        flash_error("No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    # check if it fails to be a potential label even

    info["boolean_characteristics_string"] = create_boolean_string(gp)

    if gp.live():
        title = f"Abstract group {label}"
        friends = []
        downloads = []
    else:
        prof = list(gp.subgroup_profile.items())
        prof.sort(key=lambda z: -z[0])  # largest to smallest
        info["subgroup_profile"] = [
            (z[0], display_profile_line(z[1], ambient=label, aut=False)) for z in prof
        ]
        autprof = list(gp.subgroup_autprofile.items())
        autprof.sort(key=lambda z: -z[0])  # largest to smallest
        info["subgroup_autprofile"] = [
            (z[0], display_profile_line(z[1], ambient=label, aut=True)) for z in autprof
        ]

        info["dojs"], display_opts = diagram_js_string(gp, conj=gp.diagram_ok, aut=True)
        info["wide"] = display_opts["w"] > 1600 # boolean

        info["max_sub_cnt"] = gp.max_sub_cnt
        info["max_quo_cnt"] = gp.max_quo_cnt

        title = "Abstract group " + "$" + gp.tex_name + "$"

        downloads = [
            (
                "Code for Magma",
                url_for(".download_group", label=label, download_type="magma"),
            ),
            ("Code for Gap", url_for(".download_group", label=label, download_type="gap")),
            ("Underlying data", url_for(".gp_data", label=label)),
        ]

        # "internal" friends
        sbgp_of_url = (
            " /Groups/Abstract/?hst=Subgroups&subgroup=" + label + "&search_type=Subgroups"
        )
        sbgp_url = (
            "/Groups/Abstract/?hst=Subgroups&ambient=" + label + "&search_type=Subgroups"
        )
        quot_url = (
            "/Groups/Abstract/?hst=Subgroups&quotient=" + label + "&search_type=Subgroups"
        )

        friends = [
            ("Subgroups", sbgp_url),
            ("Extensions", quot_url),
            ("Supergroups", sbgp_of_url),
        ]

        # "external" friends
        gap_ints = [int(y) for y in label.split(".")]
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

        if db.gps_transitive.count({"gapidfull": gap_str}) > 0:
            gal_gp_url = (
                "/GaloisGroup/?gal=%5B"
                + str(gap_ints[0])
                + "%2C"
                + str(gap_ints[1])
                + "%5D"
            )
            friends += [("As a transitive group", gal_gp_url)]

        if db.gps_st.count({"component_group": label}) > 0:
            st_url = (
                "/SatoTateGroup/?hst=List&component_group=%5B"
                + str(gap_ints[0])
                + "%2C"
                + str(gap_ints[1])
                + "%5D&search_type=List"
            )
            friends += [("As the component group of a Sato-Tate group", st_url)]

    bread = get_bread([(label, "")])

    return render_template(
        "abstract-show-group.html",
        title=title,
        bread=bread,
        info=info,
        gp=gp,
        properties=gp.properties(),
        friends=friends,
        learnmore=learnmore_list(),
        KNOWL_ID=f"group.abstract.{label}",
        downloads=downloads,
    )


def render_abstract_subgroup(label):
    info = {}
    label = clean_input(label)
    seq = WebAbstractSubgroup(label)

    info["create_boolean_string"] = create_boolean_string
    info["create_boolean_subgroup_string"] = create_boolean_subgroup_string
    info["factor_latex"] = factor_latex

    if seq.normal:
        title = r"Normal subgroup $%s \trianglelefteq %s$"
    else:
        title = r"Non-normal subgroup $%s \subseteq %s$"
    title = title % (seq.subgroup_tex, seq.ambient_tex)

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
        h = WebAbstractSubgroup(full_lab)
        prop = display_knowl(knowlid, title)
        return f"<tr><td>{prop}</td><td>{h.make_span()}</td></tr>\n"

    ans = (
        'Information on the subgroup <span class="%s" data-sgid="%s">$%s$</span><br>\n'
        % (wsg.spanclass(), wsg.label, wsg.subgroup_tex)
    )
    ans += f"<p>{create_boolean_subgroup_string(wsg, type='knowl')}</p>"
    ans += "<table>"
    if wsg.normal:
        ans += f"<tr><td>{display_knowl('group.quotient', 'Quotient')}</td><td>${wsg.quotient_tex}$</td></tr>"
    else:
        ans += f"<tr><td>Number of conjugates</td><td>{wsg.count}</td></tr>"
    ans += subinfo_getsub("Normalizer", "group.subgroup.normalizer", wsg.normalizer)
    ans += subinfo_getsub(
        "Normal closure", "group.subgroup.normal_closure", wsg.normal_closure
    )
    ans += subinfo_getsub("Centralizer", "group.subgroup.centralizer", wsg.centralizer)
    ans += subinfo_getsub("Core", "group.core", wsg.core)
    # ans += '<tr><td>Coset action</td><td>%s</td></tr>\n' % wsg.coset_action_label
    ## There was a bug in the Magma code computing generators, so we disable this for the moment
    # gp = WebAbstractGroup(ambient) # needed for generators
    # if wsg.subgroup_order > 1:
    #    ans += f"<tr><td>{display_knowl('group.generators', 'Generators')}</td><td>${gp.show_subgroup_generators(wsg)}$</td></tr>"
    # if not wsg.characteristic:
    #    ans += f"<tr><td>Number of autjugates</td><td>{wsg.conjugacy_class_count}</td></tr>"
    ans += (
        '<tr><td></td><td style="text-align: right"><a href="%s">$%s$ subgroup homepage</a></td>'
        % (url_for_subgroup_label(wsg.label), wsg.subgroup_tex)
    )
    ans += (
        '<tr><td></td><td style="text-align: right"><a href="%s">$%s$ abstract group homepage</a></td></tr>'
        % (url_for_label(wsg.subgroup), wsg.subgroup_tex)
    )
    # print ""
    # print ans
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
    return datapage(label, ["gps_groups", "gps_groups_cc", "gps_qchar", "gps_char", "gps_subgroups"], bread=bread, title=title, label_cols=["label", "group", "group", "group", "ambient"])

@abstract_page.route("/sdata/<label>")
def sgp_data(label):
    if not abstract_subgroup_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_subgroup_label(label)), ("Data", " ")])
    title = f"Abstract subgroup data - {label}"
    data = db.gps_subgroups.lookup(label, ["ambient", "subgroup", "quotient"])
    if data is None:
        return abort(404)
    if data["quotient"] is None:
        return datapage([label, data["subgroup"], data["ambient"]], ["gps_subgroups", "gps_groups", "gps_groups"], bread=bread, title=title)
    else:
        return datapage([label, data["subgroup"], data["ambient"], data["quotient"]], ["gps_subgroups", "gps_groups", "gps_groups", "gps_groups"], bread=bread, title=title)

@abstract_page.route("/<label>/download/<download_type>")
def download_group(**args):
    dltype = args["download_type"]
    label = args["label"]
    com = "#"  # single line comment start
    com1 = ""  # multiline comment start
    com2 = ""  # multiline comment end

    gp_data = db.gps_groups.lucky({"label": label})

    filename = "group" + label
    mydate = time.strftime("%d %B %Y")
    if dltype == "gap":
        filename += ".g"
    if dltype == "magma":
        com = ""
        com1 = "/*"
        com2 = "*/"
        filename += ".m"
    s = com1 + "\n"
    s += com + " Group " + label + " downloaded from the LMFDB on %s.\n" % (mydate)
    s += (
        com
        + " If the group is solvable, G is the  polycyclic group  matching the one presented in LMFDB."
    )
    s += com + " Generators will be stored as a, b, c,... to match LMFDB.  \n"
    s += (
        com
        + " If the group is nonsolvable, G is a permutation group giving with generators as in LMFDB."
    )
    s += com + " \n"
    s += "\n" + com2
    s += "\n"

    if gp_data["solvable"]:
        s += "gpsize:=  " + str(gp_data["order"]) + "; \n"
        s += "encd:= " + str(gp_data["pc_code"]) + "; \n"

        if dltype == "magma":
            s += "G:=SmallGroupDecoding(encd,gpsize); \n"
        elif dltype == "gap":
            s += "G:=PcGroupCode(encd, gpsize); \n"

        gen_index = gp_data["gens_used"]
        num_gens = len(gen_index)
        for i in range(num_gens):
            s += ascii_lowercase[i] + ":= G." + str(gen_index[i]) + "; \n"

    # otherwise nonsolvable MAY NEED TO CHANGE WITH MATRIX GROUPS??
    else:
        d = -gp_data["elt_rep_type"]
        s += "d:=" + str(d) + "; \n"
        s += "Sd:=SymmetricGroup(d); \n"

        # Turn Lehmer code into permutations
        list_gens = []
        for perm in gp_data["perm_gens"]:
            perm_decode = Permutations(d).unrank(perm)
            list_gens.append(perm_decode)

        if dltype == "magma":
            s += "G:=sub<Sd | " + str(list_gens) + ">; \n"
        elif dltype == "gap":
            #          MAKE LIST2
            s += "List_Gens:=" + str(list_gens) + "; \n \n"
            s += "LGens:=[]; \n"
            s += "for gens in List_Gens do AddSet(LGens,PermList(gens)); od;\n"
            s += "G:=Subgroup(Sd,LGens);"

    strIO = BytesIO()
    strIO.write(s.encode("utf-8"))
    strIO.seek(0)
    return send_file(
        strIO, attachment_filename=filename, as_attachment=True, add_etags=False
    )


def display_profile_line(data, ambient, aut):
    l = []
    for label, tex in sorted(data, key=data.get, reverse=True):
        cnt = data[label, tex]
        l.append(
            abstract_group_display_knowl(label, name=f"${tex}$", ambient=ambient, aut=aut)
            + (" x " + str(cnt) if cnt > 1 else "")
        )
    return ", ".join(l)


class GroupsSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    sorts = [("", "order", ["order", "counter"]),
             ("exponent", "exponent", ["exponent", "order", "counter"]),
             ("nilpotency_class", "nilpotency class", ["nilpotency_class", "order", "counter"]),
             ("derived_length", "derived length", ["derived_length", "order", "counter"]),
             ("composition_length", "composition length", ["composition_length", "order", "counter"]),
             ("rank", "rank", ["rank", "eulerian_function", "order", "counter"]),
             #("center_label", "center", ["center_label", "order", "counter"]),
             #("commutator_label", "commutator", ["commutator_label", "order", "counter"]),
             #("central_quotient", "central quotient", ["central_quotient", "order", "counter"]),
             #("abelian_quotient", "abelianization", ["abelian_quotient", "order", "counter"]),
             ("aut_order", "automorphism group", ["aut_order", "aut_group", "order", "counter"]),
             ("number_conjugacy_classes", "conjugacy classes", ["number_conjugacy_classes", "order", "counter"]),
             ("number_subgroup_classes", "subgroup classes", ["number_subgroup_classes", "order", "counter"])]
    jump_example = "8.3"
    jump_egspan = "e.g. 8.3, GL(2,3), C3:C4, C2*A5 or C16.D4"
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
            example="4.2",
            example_span="4.2",
        )
        commutator_label = TextBox(
            name="commutator_label",
            label="Commutator",
            knowl="group.commutator_isolabel",
            example="4.2",
            example_span="4.2",
        )
        abelian_quotient = TextBox(
            name="abelian_quotient",
            label="Abelianization",
            knowl="group.abelianization_isolabel",
            example="4.2",
            example_span="4.2",
        )
        central_quotient = TextBox(
            name="central_quotient",
            label="Central quotient",
            knowl="group.central_quotient_isolabel",
            example="4.2",
            example_span="4.2",
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
            [
                almost_simple,
                derived_length,
            ],
            [
                quasisimple,
                supersolvable,
            ],
            [outer_group, metabelian],
            [outer_order, metacyclic],
            [Agroup, monomial],
            [Zgroup, rational],
            [wreath_product],
            [order_stats, rank],
            [exponents_of_order, commutator_count],
            [count],
        ]

        self.refine_array = [
            [order, exponent, nilpclass, nilpotent],
            [center_label, commutator_label, central_quotient, abelian_quotient],
            [abelian, cyclic, solvable, simple],
            [perfect, direct_product, semidirect_product],
            [aut_group, aut_order, outer_group, outer_order],
            [metabelian, metacyclic, almost_simple, quasisimple],
            [Agroup, Zgroup, derived_length, frattini_label],
            [supersolvable, monomial, rational, rank],
            [order_stats, exponents_of_order, commutator_count, wreath_product],
            [name],
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
    sorts = [("", "ambient order", ['ambient_order', 'ambient', 'quotient_order', 'subgroup']),
             ("sub_ord", "subgroup order", ['subgroup_order', 'ambient_order', 'ambient', 'subgroup']),
             ("sub_ind", "subgroup index", ['quotient_order', 'ambient_order', 'ambient', 'subgroup'])]
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
        proper = YesNoBox(name="proper", label="Proper", knowl="group.proper_subgroup")

        self.refine_array = [
            [subgroup, subgroup_order, cyclic, abelian, solvable],
            [normal, characteristic, perfect, maximal, central, proper],
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
        if info is None:
            return [("Subgroups", "List of subgroups"), ("RandomSubgroup", "Random subgroup")]
        else:
            return [("Subgroups", "Search again"), ("RandomSubgroup", "Random subgroup")]

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

@cached_function(key=lambda label,name,pretty,ambient,aut,cache: (label,name,pretty,ambient,aut))
def abstract_group_display_knowl(label, name=None, pretty=True, ambient=None, aut=False, cache={}):
    # If you have the group in hand, set the name using gp.tex_name since that will avoid a database call
    if not name:
        if pretty:
            if label in cache and "tex_name" in cache[label]:
                name = cache[label]["tex_name"]
            else:
                name = db.gps_groups.lookup(label, "tex_name")
            if name is None:
                name = f"Group {label}"
            else:
                name = f"${name}$"
        else:
            name = f"Group {label}"
    if ambient is None:
        args = label
    else:
        args = f"{label}%7C{ambient}%7C{aut}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={args}&func=group_data">{name}</a>'


def sub_display_knowl(label, name=None):
    if not name:
        name = f"Subgroup {label}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=sub_data">{name}</a>'

def semidirect_expressions_knowl(label, name=None):
    if not name:
        name = f"Semidirect product expressions for {label}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=semidirect_data">{name}</a>'

def nonsplit_expressions_knowl(label, name=None):
    if not name:
        name = f"Nonsplit product expressions for {label}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=nonsplit_data">{name}</a>'

def autgp_expressions_knowl(label, name=None):
    if not name:
        name = f"Expressions for {label} as an automorphism group"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=aut_data">{name}</a>'

def cc_data(gp, label, typ="complex"):
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
    centralizer = f"{wacc.group}.{wacc.centralizer}"
    wcent = WebAbstractSubgroup(centralizer)
    ans += "<br>Centralizer: {}".format(
        sub_display_knowl(centralizer, "$" + wcent.subgroup_tex + "$")
    )
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
    nt = mychar.nt
    ans += "<br>Smallest container: {}T{}".format(nt[0], nt[1])
    if mychar._data.get("image"):
        txt = "Image"
        imageknowl = (
            '<a title = "{0} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=qrep_data&args={0}">{0}</a>'.format(mychar.image)
        )
        if mychar.schur_index > 1:
            txt = r"Image of ${}\ *\ ${}".format(mychar.schur_index, label)
        ans += "<br>{}: {}".format(txt, imageknowl)
    else:
        ans += "<br>Image: not computed"
    return Markup(ans)


def cchar_data(label):
    from lmfdb.number_fields.web_number_field import formatfield
    mychar = WebAbstractCharacter(label)
    ans = "<h3>Complex character {}</h3>".format(label)
    ans += "<br>Degree: {}".format(mychar.dim)
    if mychar.faithful:
        ans += "<br>Faithful character"
    else:
        ker = WebAbstractSubgroup(f"{mychar.group}.{mychar.kernel}")
        ans += "<br>Not faithful with kernel {}".format(
            sub_display_knowl(ker.label, "$" + ker.subgroup_tex + "$")
        )
    nt = mychar.nt
    ans += "<br>Frobenius-Schur indicator: {}".format(mychar.indicator)
    ans += "<br>Smallest container: {}T{}".format(nt[0], nt[1])
    ans += "<br>Field of character values: {}".format(formatfield(mychar.field))
    if mychar._data.get("image"):
        imageknowl = (
            '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=crep_data&args=%s">%s</a>'
            % (mychar.image, mychar.image, mychar.image)
        )
        ans += "<br>Image: {}".format(imageknowl)
    else:
        ans += "<br>Image: not computed"
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
    plural = "" if len(info["gens"]) == 1 else "s"
    ans += "<br>Matrix generator{}: ".format(plural)
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
    plural = "" if len(info["gens"]) == 1 else "s"
    ans += "<br>Matrix generator{}: ".format(plural)
    genlist = ["$" + dispZmat(gen) + "$" for gen in info["gens"]]
    ans += ",".join(genlist)
    return Markup(ans)


def sub_data(label):
    label = label.split(".")
    return Markup(shortsubinfo(".".join(label[:2]), ".".join(label[2:])))


def group_data(label, ambient=None, aut=False):
    if label.startswith("ab/"):
        data = canonify_abelian_label(label[3:])
        url = url_for("abstract.by_abelian_label", label=label[3:])
    else:
        data = None
        url = url_for("abstract.by_label", label=label)
    gp = WebAbstractGroup(label, data=data)
    ans = f"Group ${gp.tex_name}$: "
    ans += create_boolean_string(gp, type="knowl")
    ans += f"<br />Label: {gp.label}<br />"
    ans += f"Order: {gp.order}<br />"
    ans += f"Exponent: {gp.exponent}<br />"

    if not gp.live():
        if ambient is None:
            ans += "It has {} subgroups".format(gp.number_subgroups)
            if gp.number_normal_subgroups < gp.number_subgroups:
                ans += " in {} conjugacy classes, {} normal, ".format(
                    gp.number_subgroup_classes, gp.number_normal_subgroups
                )
            else:
                ans += ", all normal, "
            if gp.number_characteristic_subgroups < gp.number_normal_subgroups:
                ans += str(gp.number_characteristic_subgroups)
            else:
                ans += "all"
            ans += " characteristic.<br />"
        else:
            ambient = WebAbstractGroup(ambient)
            subs = [H for H in ambient.subgroups.values() if H.subgroup == label]
            if aut and not ambient.outer_equivalence:
                subs = [H for H in subs if H.label.split(".")[-1] == "a1"]
            subs.sort(
                key=lambda H: H.label
            )  # It would be better to split the label apart and sort numerically, but that's too much work
            ans += '<div align="right">'
            ans += "Subgroups with this isomorphism type: "
            for H in subs:
                ans += '<a href="{}">{}</a>&nbsp;'.format(
                    url_for("abstract.by_subgroup_label", label=H.label), H.label
                )
            ans += "</div><br />"
    ans += f'<div align="right"><a href="{url}">{label} home page</a></div>'
    return Markup(ans)

def semidirect_data(label):
    gp = WebAbstractGroup(label)
    ans = f"Semidirect product expressions for ${gp.tex_name}$:<br />\n"
    for sub, cnt, labels in gp.semidirect_products:
        ans += fr"${sub.subgroup_tex_parened}~\rtimes~{sub.quotient_tex_parened}$"
        if cnt > 1:
            ans += f" in {cnt} ways"
        ans += ' via '
        ans += ", ".join([f'<a href="{url_for("abstract.by_subgroup_label", label=label+"."+sublabel)}">{sublabel}</a>' for sublabel in labels])
        ans += "<br />\n"
    return Markup(ans)

def nonsplit_data(label):
    gp = WebAbstractGroup(label)
    ans = f"Nonsplit product expressions for ${gp.tex_name}$:<br />\n"
    ans += "<table>\n"
    for sub, cnt, labels in gp.nonsplit_products:
        ans += f"<tr><td>${sub.subgroup_tex_parened}~.~{sub.quotient_tex_parened}$</td><td>"
        if cnt > 1:
            ans += f" in {cnt} ways"
        ans += ' via </td>'
        ans += "".join([f'<td><a href="{url_for("abstract.by_subgroup_label", label=label+"."+sublabel)}">{sublabel}</a></td>' for sublabel in labels])
        ans += "</tr>\n"
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
    f is the name of a function to call, which has to be in flist, which
      is at the bottom of this file
    args is a string with the arguments, which are concatenated together
      with %7C, which is the encoding of the pipe symbol
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
    "aut_data": aut_data,
}


def order_stats_list_to_string(o_list):
    s = ""
    for pair in o_list:
        assert len(pair) == 2
        s += "%s^%s" % (pair[0], pair[1])
        if o_list.index(pair) != len(o_list) - 1:
            s += ","
    return s
