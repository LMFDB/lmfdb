import re

from lmfdb import db

from flask import url_for
from sage.all import (
    Permutations,
    SymmetricGroup,
    ZZ,
    factor,
    latex,
    lazy_attribute,
    prod,
)
from sage.libs.gap.libgap import libgap
from collections import Counter, defaultdict
from lmfdb.utils import (
    display_knowl,
    sparse_cyclotomic_to_latex,
    to_ordinal,
    web_latex,
)
from .circles import find_packing

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")


def group_names_pretty(label):
    if isinstance(label, str):
        pretty = db.gps_groups.lookup(label, "tex_name")
    else:
        pretty = label.tex_name
    if pretty:
        return pretty
    else:
        return label


def group_pretty_image(label):
    pretty = group_names_pretty(label)
    img = db.gps_images.lookup(pretty, "image")
    if img:
        return str(img)
    # fallback which should always be in the database
    img = db.gps_images.lookup("?", "image")
    if img:
        return str(img)
    # we should not get here


def product_sort_key(sub):
    s = sub.subgroup_tex_parened + sub.quotient_tex_parened
    s = (
        s.replace("{", "")
        .replace("}", "")
        .replace(" ", "")
        .replace(r"\rm", "")
        .replace(r"\times", "x")
    )
    v = []
    for c in "SALwOQDC":
        # A rough preference order for groups S_n (and SL_n), A_n, GL_n, wreath products, OD_n, Q_n, D_n, and finally C_n
        v.append(-s.count(c))
    return len(s), v


class WebObj(object):
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            data = self._get_dbdata()
        self._data = data
        if data is not None:
            for key, val in self._data.items():
                setattr(self, key, val)

    @classmethod
    def from_data(cls, data):
        return cls(data["label"], data)

    def _get_dbdata(self):
        return self.table.lookup(self.label)


# Abstract Group object
class WebAbstractGroup(WebObj):
    table = db.gps_groups

    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)

    def properties(self):
        nilp_str = f"Yes, of class {self.nilpotency_class}" if self.nilpotent else "No"
        solv_str = f"Yes, of length {self.derived_length}" if self.solvable else "No"
        props = [
            ("Label", self.label),
            ("Order", web_latex(factor(self.order))),
            ("Exponent", web_latex(factor(self.exponent))),
            (None, self.image()),
            ("Abelian", "Yes" if self.abelian else "No"),
            ("Nilpotent", nilp_str),
            ("Solvable", solv_str),
            ("Simple", "Yes" if self.simple else "No"),
            (r"#$\operatorname{Aut}(G)$", web_latex(factor(self.aut_order))),
            (r"#$\operatorname{Out}(G)$", web_latex(factor(self.outer_order))),
            ("Rank", f"${self.rank}$"),
            ("Perm deg.", f"${self.transitive_degree}$"),
            # ("Faith. dim.", str(self.faithful_reps[0][0])),
        ]
        if not self.abelian:
            props[8:8] = [
                (r"#$G^{\mathrm{ab}}$", web_latex(self.Gab_order_factor())),
                ("#$Z(G)$", web_latex(self.cent_order_factor())),
            ]
        return props

    @lazy_attribute
    def subgroups(self):
        return {
            subdata["short_label"]: WebAbstractSubgroup(subdata["label"], subdata)
            for subdata in db.gps_subgroups.search({"ambient": self.label})
        }

    def add_layers(self):
        subs = self.subgroups
        topord = max(sub.subgroup_order for sub in subs.values())
        top = [z.short_label for z in subs.values() if z.subgroup_order == topord][0]
        top.layer = 0
        seen = set()
        layer = [subs[top]]
        added_something = True # prevent data error from causing infinite loop
        while len(seen) < len(subs) and added_something:
            new_layer = []
            added_something = False
            for H in layer:
                for new in H.contains:
                    if new not in seen:
                        seen.add(new)
                        added_something = True
                        K = subs[new]
                        new_layer.append(K)
                        K.layer = H.layer + 1
            layer = new_layer

    # special subgroups
    def special_search(self, sp):
        for lab, gp in self.subgroups.items():
            if sp in gp.special_labels:
                return lab  # is label what we want to return?
                # H = subs['lab']
                # return group_names_pretty(H.subgroup)

    @lazy_attribute
    def fitting(self):
        return self.special_search("F")

    @lazy_attribute
    def radical(self):
        return self.special_search("R")

    @lazy_attribute
    def socle(self):
        return self.special_search("S")

    # series

    def series_search(self, sp):
        ser_str = r"^%s\d+" % sp
        ser_re = re.compile(ser_str)
        subs = self.subgroups
        ser = []
        for lab, H in subs.items():
            for spec_lab in H.special_labels:
                if ser_re.match(spec_lab):
                    # ser.append((H.subgroup, spec_lab)) # returning right thing?
                    ser.append((H.short_label, spec_lab))
        # sort
        def sort_ser(p, ch):
            return int(((p[1]).split(ch))[1])

        def sort_ser_sp(p):
            return sort_ser(p, sp)

        return [el[0] for el in sorted(ser, key=sort_ser_sp)]

    @lazy_attribute
    def chief_series(self):
        return self.series_search("C")

    @lazy_attribute
    def derived_series(self):
        return self.series_search("D")

    @lazy_attribute
    def lower_central_series(self):
        return self.series_search("L")

    @lazy_attribute
    def upper_central_series(self):
        return self.series_search("U")

    @lazy_attribute
    def diagram_ok(self):
        return self.number_subgroup_classes < 100

    @lazy_attribute
    def subgroup_profile(self):
        by_order = defaultdict(Counter)
        for s in self.subgroups.values():
            by_order[s.subgroup_order][s.subgroup, s.subgroup_tex] += s.conjugacy_class_count
        return by_order

    @lazy_attribute
    def subgroup_autprofile(self):
        seen = set()
        by_order = defaultdict(Counter)
        for s in self.subgroups.values():
            if s.aut_label not in seen:
                by_order[s.subgroup_order][s.subgroup, s.subgroup_tex] += 1
                seen.add(s.aut_label)
        return by_order

    @lazy_attribute
    def conjugacy_classes(self):
        cl = [
            WebAbstractConjClass(self.label, ccdata["label"], ccdata)
            for ccdata in db.gps_groups_cc.search({"group": self.label})
        ]
        divs = defaultdict(list)
        autjs = defaultdict(list)
        for c in cl:
            divkey = re.sub(r"([^\d])-?\d+?$", r"\1", c.label)
            divs[divkey].append(c)
            autjs[c.aut_label].append(c)
        ccdivs = []
        for divkey, ccs in divs.items():
            div = WebAbstractDivision(self.label, divkey, ccs)
            for c in ccs:
                c.division = div
            ccdivs.append(div)
        ccdivs.sort(key=lambda x: x.classes[0].counter)
        self.conjugacy_class_divisions = ccdivs
        autccs = []
        for autkey, ccs in autjs.items():
            autj = WebAbstractAutjClass(self.label, autkey, ccs)
            for c in ccs:
                c.autjugacy_class = autj
            autccs.append(autj)
        autccs.sort(key=lambda x: x.classes[0].counter)
        self.autjugacy_classes = autccs
        return sorted(cl, key=lambda x: x.counter)

    # These are the power-conjugacy classes
    @lazy_attribute
    def conjugacy_class_divisions(self):
        cl = self.conjugacy_classes  # creates divisions
        assert cl
        return self.conjugacy_class_divisions

    @lazy_attribute
    def autjugacy_classes(self):
        cl = self.conjugacy_classes  # creates autjugacy classes
        assert cl
        return self.autjugacy_classes

    @lazy_attribute
    def sorted_cc_divisions(self):
        ccdivs = [
            {"label": k, "classes": v}
            for k, v in self.conjugacy_class_divisions.items()
        ]
        ccdivs.sort(key=lambda x: x["classes"][0].counter)
        return ccdivs

    @lazy_attribute
    def cc_to_div(self):
        # Need to map cc's to their divisions
        ctor = {}
        for k, vs in self.conjugacy_class_divisions.items():
            for v in vs:
                ctor[v.label] = k
        return ctor

    @lazy_attribute
    def characters(self):
        # Should join with creps once we have images and join queries
        chrs = [
            WebAbstractCharacter(chardata["label"], chardata)
            for chardata in db.gps_char.search({"group": self.label})
        ]
        return sorted(chrs, key=lambda x: x.counter)

    @lazy_attribute
    def rational_characters(self):
        # Should join with creps once we have images and join queries
        chrs = [
            WebAbstractRationalCharacter(chardata["label"], chardata)
            for chardata in db.gps_qchar.search({"group": self.label})
        ]
        return sorted(chrs, key=lambda x: x.counter)

    @lazy_attribute
    def maximal_subgroup_of(self):
        # Could show up multiple times as non-conjugate maximal subgroups in the same ambient group
        # So we should elimintate duplicates from the following list
        return [
            WebAbstractSupergroup(self, "sub", supdata["label"], supdata)
            for supdata in db.gps_subgroups.search(
                {"subgroup": self.label, "maximal": True},
                sort=["ambient_order", "ambient"],
                limit=10,
            )
        ]

    @lazy_attribute
    def maximal_quotient_of(self):
        # Could show up multiple times as a quotient of different normal subgroups in the same ambient group
        # So we should elimintate duplicates from the following list
        return [
            WebAbstractSupergroup(self, "quo", supdata["label"], supdata)
            for supdata in db.gps_subgroups.search(
                {"quotient": self.label, "minimal_normal": True},
                sort=["ambient_order", "ambient"],
            )
        ]

    def most_product_expressions(self):
        return max(1, len(self.semidirect_products), len(self.nonsplit_products))

    @lazy_attribute
    def display_direct_product(self):
        # Need to pick an ordering
        # return [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]
        C = dict(self.direct_factorization)
        # We can use the list of subgroups to get the latex
        latex_lookup = {}
        sort_key = {}
        for sub in self.subgroups.values():
            slab = sub.subgroup
            if slab in C:
                latex_lookup[slab] = sub.subgroup_tex_parened
                sort_key[slab] = (
                    not sub.abelian,
                    sub.subgroup_order.is_prime_power(get_data=True)[0]
                    if sub.abelian
                    else sub.subgroup_order,
                    sub.subgroup_order,
                )
                if len(latex_lookup) == len(C):
                    break
        df = sorted(self.direct_factorization, key=lambda x: sort_key[x[0]])
        s = r" \times ".join(
            "%s%s" % (latex_lookup[label], "^%s" % e if e > 1 else "")
            for (label, e) in df
        )
        return s

    @lazy_attribute
    def semidirect_products(self):
        semis = []
        count = Counter()
        for sub in self.subgroups.values():
            if sub.normal and sub.split and not sub.direct:
                pair = (sub.subgroup, sub.quotient)
                if pair not in count:
                    semis.append(sub)
                count[pair] += 1
        semis.sort(key=product_sort_key)
        return [(sub, count[sub.subgroup, sub.quotient]) for sub in semis]

    @lazy_attribute
    def nonsplit_products(self):
        nonsplit = []
        count = Counter()
        for sub in self.subgroups.values():
            if sub.normal and not sub.split:
                pair = (sub.subgroup, sub.quotient)
                if pair not in count:
                    nonsplit.append(sub)
                count[pair] += 1
        nonsplit.sort(key=product_sort_key)
        return [(sub, count[sub.subgroup, sub.quotient]) for sub in nonsplit]

    # Subgroups up to conjugacy -- this one is no longer used
    @lazy_attribute
    def subgroup_layers(self):
        # Need to update to account for possibility of not having all inclusions
        subs = self.subgroups
        topord = max(sub.subgroup_order for sub in subs.values())
        top = [z.short_label for z in subs.values() if z.subgroup_order == topord][0]
        layers = [[subs[top]]]
        seen = set([top])
        added_something = True  # prevent data error from causing infinite loop
        # print "starting while"
        while len(seen) < len(subs) and added_something:
            layers.append([])
            added_something = False
            for H in layers[-2]:
                # print H.counter
                # print "contains", H.contains
                for new in H.contains:
                    if new not in seen:
                        seen.add(new)
                        added_something = True
                        layers[-1].append(subs[new])
        edges = []
        for g in subs:
            for h in subs[g].contains:
                edges.append([h, g])
        return [layers, edges]

    # Subgroups up to conjugacy
    @lazy_attribute
    def subgroup_lattice(self):
        # Need to update to account for possibility of not having all inclusions
        if self.outer_equivalence:
            raise RuntimeError("Subgroups not known up to conjugacy")
        subs = self.subgroups
        nodes = list(subs.values())
        edges = []
        for g in subs:
            for h in subs[g].contains:
                edges.append([h, g])
        return [nodes, edges]

    # Subgroups up to autjugacy
    @lazy_attribute
    def subgroup_lattice_aut(self):
        # Need to update to account for possibility of not having all inclusions
        # It would be better to add pages for subgroups up to automorphism with links to the conjugacy classes within
        subs = self.subgroups
        if self.outer_equivalence:
            nodes = list(subs.values())
            edges = []
            for g in subs:
                for h in subs[g].contains:
                    edges.append([h, g])
        else:
            nodes = []
            edges = set()  # avoid multiedges; this may not be the desired behavior
            for g in subs.values():
                if g.short_label.endswith(".a1"):
                    nodes.append(g)
                glabel = g.aut_label + ".a1"
                for h in g.contains:
                    hlabel = ".".join(h.split(".")[:-1]) + ".a1"
                    edges.add((hlabel, glabel))
            edges = [list(edge) for edge in edges]
        return [nodes, edges]

    @lazy_attribute
    def tex_images(self):
        all_tex = list(set(H.subgroup_tex for H in self.subgroups.values())) + ["?"]
        return {
            rec["label"]: rec["image"]
            for rec in db.gps_images.search({"label": {"$in": all_tex}}, ["label", "image"])
        }

    def sylow_subgroups(self):
        """
        Returns a list of pairs (p, P) where P is a WebAbstractSubgroup representing a p-Sylow subgroup.
        """
        syl_dict = {}
        for sub in self.subgroups.values():
            if sub.sylow > 0:
                syl_dict[sub.sylow] = sub
        syl_list = []
        for p, e in factor(self.order):
            if p in syl_dict:
                syl_list.append((p, syl_dict[p]))
        return syl_list

    def series(self):
        data = [
            [
                "group.%s" % ser,
                ser.replace("_", " ").capitalize(),
                [self.subgroups[i] for i in getattr(self, ser)],
                "-".join(map(str, getattr(self, ser))),
                r"\rhd",
            ]
            for ser in [
                "derived_series",
                "chief_series",
                "lower_central_series",
                "upper_central_series",
            ]
        ]
        data[3][4] = r"\lhd"
        data[3][2].reverse()
        return data

    def schur_multiplier_text(self):
        if not self.schur_multiplier:
            return "C_1"
        entries = []
        for key, value in Counter(self.schur_multiplier).items():
            entry = "C_{%s}" % key
            if value != 1:
                entry += "^{%s}" % value
            entries.append(entry)
        return r" \times ".join(entries)

    def schur_multiplier_label(self):
        if self.schur_multiplier:
            return ".".join(str(e) for e in self.schur_multiplier)
        else:  # trivial group has to be handled separately
            return "1"

    @lazy_attribute
    def rep_dims(self):
        return sorted(
            set(
                [rep.dim for rep in self.characters]
                + [rep.qdim for rep in self.rational_characters]
            )
        )

    @lazy_attribute
    def irrep_stats(self):
        D = Counter([rep.dim for rep in self.characters])
        return [D[d] for d in self.rep_dims]

    @lazy_attribute
    def ratrep_stats(self):
        D = Counter([rep.qdim for rep in self.rational_characters])
        return [D[d] for d in self.rep_dims]

    @lazy_attribute
    def cc_stats(self):
        return sorted(Counter([cc.order for cc in self.conjugacy_classes]).items())

    @lazy_attribute
    def division_stats(self):
        return sorted(
            Counter([div.order for div in self.conjugacy_class_divisions]).items()
        )

    @lazy_attribute
    def autc_stats(self):
        return sorted(Counter([cc.order for cc in self.autjugacy_classes]).items())

    @lazy_attribute
    def G(self):
        # Reconstruct the group from the data stored above
        if self.order == 1:  # trvial
            return libgap.TrivialGroup()
        elif self.elt_rep_type == 0:  # PcGroup
            return libgap.PcGroupCode(self.pc_code, self.order)
        elif self.elt_rep_type < 0:  # Permutation group
            gens = [self.decode(g) for g in self.perm_gens]
            return libgap.Group(gens)
        else:
            # TODO: Matrix groups
            raise NotImplementedError

    @lazy_attribute
    def pcgs(self):
        return self.G.Pcgs()

    @lazy_attribute
    def pcgs_relative_orders(self):
        return [ZZ(c) for c in self.pcgs.RelativeOrders()]

    def decode_as_pcgs(self, code, getvec=False):
        # Decode an element
        vec = []
        if code < 0 or code >= self.order:
            raise ValueError
        for m in reversed(self.pcgs_relative_orders):
            c = code % m
            vec.insert(0, c)
            code = code // m
        if getvec:
            # Need to combine some generators
            w = []
            e = 0
            for i, (c, m) in reversed(list(enumerate(zip(vec, self.pcgs_relative_orders)))):
                e += c
                if i + 1 in self.gens_used:
                    w.append(e)
                    e = 0
                else:
                    e *= m
            w.reverse()
            return w
        else:
            return self.pcgs.PcElementByExponents(vec)

    def decode_as_pcgs_str(self, code):
        vec = self.decode_as_pcgs(code, getvec=True)
        s = ""
        assert len(vec) <= 26, "we are assuming that we have at most 26 generators"
        for i, c in enumerate(vec):
            if c == 1:
                s += chr(97 + i)  # breaks if we have more than 26 generators...
            elif c != 0:
                s += "%s^{%s}" % (chr(97 + i), c)
        return s

    def decode_as_perm(self, code):
        # code should be an integer with 0 <= m < factorial(n)
        n = -self.elt_rep_type
        return str(SymmetricGroup(n)(Permutations(n).unrank(code)))

    def show_subgroup_generators(self, H):
        if H.subgroup_order == 1:
            return ""
        if self.elt_rep_type == 0:  # PC group
            return ", ".join(self.decode_as_pcgs_str(g) for g in H.generators)
        elif self.elt_rep_type < 0:  # permutation group
            return ", ".join(self.decode_as_perm(g) for g in H.generators)
        else:  # matrix groups
            raise NotImplementedError

    # @lazy_attribute
    # def fp_isom(self):
    #    G = self.G
    #    P = self.pcgs
    #    def position(x):
    #        # Return the unique generator
    #        vec = P.ExponentsOfPcElement(x)
    #        if sum(vec) == 1:
    #            for i in range(len(vec)):
    #                if vec[i]:
    #                    return i
    #    gens = G.GeneratorsOfGroup()
    #    # We would like to remove extraneous generators, but can't figure out how to do so
    #    rords = P.RelativeOrders()
    #    for i, (g, r) in enumerate(zip(gens, rords)):
    #        j = position(g**r)
    #        if j is None:
    #            # g^r is not another generator

    def write_element(self, elt):
        # Given a decoded element or free group lift, return a latex form for printing on the webpage.
        if self.elt_rep_type == 0:
            s = str(elt)
            assert self.ngens <= 26, "we are assuming that we have at most 26 generators"
            # reversed so that we don't replace f1 in f10.
            for i in reversed(range(self.ngens)):
                s = s.replace("f%s" % (i + 1), chr(97 + i))
            return s

    # TODO: is this the presentation we want?
    def presentation(self):
        # chr(97) = "a"
        if self.elt_rep_type == 0:
            # We use knowledge of the form of the presentation to construct it manually.
            gens = list(self.G.GeneratorsOfGroup())
            pcgs = self.G.FamilyPcgs()
            used = [u - 1 for u in sorted(self.gens_used)]  # gens_used is 1-indexed
            rel_ords = [ZZ(p) for p in self.G.FamilyPcgs().RelativeOrders()]
            pure_powers = []
            rel_powers = []
            comm = []
            relators = []

            def print_elt(vec):
                s = ""
                e = 0
                u = used[-1]
                i = len(used) - 1
                for j, (c, p) in reversed(list(enumerate(zip(vec, rel_ords)))):
                    e *= p
                    e += c
                    if j == u:
                        if e == 1:
                            s = chr(97 + i) + s
                        elif e > 1:
                            s = "%s^{%s}" % (chr(97 + i), e) + s
                        i -= 1
                        u = used[i]
                        e = 0
                return s

            ngens = len(used)
            assert len(ngens) <= 26, "we are assuming that we have at most 26 generators"
            for i in range(ngens):
                a = used[i]
                e = prod(rel_ords[a:] if i == ngens - 1 else rel_ords[a : used[i + 1]])
                ae = pcgs.ExponentsOfPcElement(gens[a] ** e)
                if all(x == 0 for x in ae):
                    pure_powers.append("%s^{%s}" % (chr(97 + i), e))
                else:
                    rel_powers.append("%s^{%s}=%s" % (chr(97 + i), e, print_elt(ae)))
                for j in range(i + 1, ngens):
                    b = used[j]
                    if all(
                        x == 0 for x in pcgs.ExponentsOfCommutator(b + 1, a + 1)
                    ):  # back to 1-indexed
                        if not self.abelian:
                            comm.append("[%s,%s]" % (chr(97 + i), chr(97 + j)))
                    else:
                        v = pcgs.ExponentsOfConjugate(b + 1, a + 1)  # back to 1-indexed
                        relators.append(
                            "%s^{%s}=%s" % (chr(97 + j), chr(97 + i), print_elt(v))
                        )
            show_gens = ", ".join(chr(97 + i) for i in range(len(used)))
            if pure_powers or comm:
                rel_powers = ["=".join(pure_powers + comm) + "=1"] + rel_powers
            relators = ", ".join(rel_powers + relators)
            return r"\langle %s \mid %s \rangle" % (show_gens, relators)
        elif self.elt_rep_type < 0:
            return r"\langle %s \rangle" % (
                ", ".join(map(self.decode_as_perm, self.perm_gens))
            )
        else:
            raise NotImplementedError

    def is_null(self):
        return self._data is None

    # TODO if prime factors get large, use factors in database
    def order_factor(self):
        return latex(factor(self.order))

    ###automorphism group
    def show_aut_group(self):
        if self.aut_group is None:
            if self.aut_order is None:
                return r"$\textrm{Not computed}$"
            else:
                return f"Group of order ${self.aut_order_factor()}$"
        else:
            url = url_for(".by_label", label=self.aut_group)
            return f'<a href="{url}">${group_names_pretty(self.aut_group)}$</a>, of order ${self.aut_order_factor()}$'

    # TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return latex(factor(self.aut_order))

    ###outer automorphism group
    def show_outer_group(self):
        if self.outer_group is None:
            if self.outer_order is None:
                return r"$\textrm{Not computed}$"
            else:
                return f"Group of order ${self.out_order_factor()}$"
        else:
            url = url_for(".by_label", label=self.outer_group)
            return f'<a href="{url}">${group_names_pretty(self.outer_group)}$</a>, of order ${self.out_order_factor()}$'

    # TODO if prime factors get large, use factors in database
    def out_order_factor(self):
        return latex(factor(self.outer_order))

    def show_composition_factors(self):
        CF = Counter(self.composition_factors)
        display = {
            rec["label"]: rec["tex_name"]
            for rec in db.gps_groups.search(
                {"label": {"$in": list(set(CF))}}, ["label", "tex_name"]
            )
        }
        from .main import url_for_label

        def exp(n):
            return "" if n == 1 else f" ({n})"

        return ", ".join(
            f'<a href="{url_for_label(label)}">${display[label]}$</a>{exp(e)}'
            for (label, e) in CF.items()
        )

    ###special subgroups
    def cent(self):
        return self.special_search("Z")

    def cent_label(self):
        return self.subgroups[self.cent()].subgroup_tex

    def central_quot(self):
        return self.subgroups[self.cent()].quotient_tex

    def cent_order_factor(self):
        return (self.order // ZZ(self.cent().split(".")[0])).factor()

    def comm(self):
        return self.special_search("D")

    def comm_label(self):
        return self.subgroups[self.comm()].subgroup_tex

    def abelian_quot(self):
        return self.subgroups[self.comm()].quotient_tex

    def abelian_quot_primary(self):
        return r" \times ".join(
            ("C_{%s}^{%s}" % (q, e) if e > 1 else "C_{%s}" % q)
            for (q, e) in Counter(self.primary_abelian_invariants).items()
        )

    def abelianization_label(self):
        return ".".join(str(m) for m in self.smith_abelian_invariants)

    def Gab_order_factor(self):
        return ZZ(self._data["abelian_quotient"].split(".")[0]).factor()

    def fratt(self):
        return self.special_search("Phi")

    def fratt_label(self):
        return self.subgroups[self.fratt()].subgroup_tex

    def frattini_quot(self):
        return self.subgroups[self.fratt()].quotient_tex

    def gen_noun(self):
        if self.rank == 1:
            return "generators"
        elif self.rank == 2:
            return "generating pairs"
        elif self.rank == 3:
            return "generating triples"
        elif self.rank == 4:
            return "generating quadruples"
        else:
            return f"generating {self.rank}-tuples"

    @lazy_attribute
    def max_sub_cnt(self):
        return db.gps_subgroups.count_distinct(
            "ambient", {"subgroup": self.label, "maximal": True}, record=False
        )

    @lazy_attribute
    def max_quo_cnt(self):
        return db.gps_subgroups.count_distinct(
            "ambient", {"quotient": self.label, "minimal_normal": True}, record=False
        )

    @staticmethod
    def sparse_cyclotomic_to_latex(n, dat):
        # The indirection is because we want to make this a staticmethod
        return sparse_cyclotomic_to_latex(n, dat)

    def image(self):
        circles, R = find_packing([(c.size, c.order) for c in self.conjugacy_classes])
        R = R.ceiling()
        circles = "\n".join(
            f'<circle cx="{x}" cy="{y}" r="{rad}" fill="rgb({r},{g},{b})" />'
            for (x, y, rad, (r, g, b)) in circles
        )
        return f'<img><svg xmlns="http://www.w3.org/2000/svg" viewBox="-{R} -{R} {2*R} {2*R}" width="200" height="150">\n{circles}</svg></img>'

    # The following attributes are used in create_boolean_string
    @property
    def nonabelian(self):
        return not self.abelian

    @property
    def nonsolvable(self):
        return not self.solvable

    @property
    def ab_simple(self):  # prime cyclic
        return self.simple and self.abelian

    @property
    def nab_simple(self):
        return self.simple and not self.abelian

    @property
    def ab_perfect(self):  # trivial
        return self.perfect and self.abelian

    @property
    def nab_perfect(self):
        return self.perfect and not self.abelian

    @property
    def is_elementary(self):
        return self.elementary > 1

    @property
    def is_hyperelementary(self):
        return self.hyperelementary > 1


class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups

    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        s = self.subgroup_tex
        self.subgroup_tex_parened = s if self._is_atomic(s) else "(%s)" % s
        if self._data.get("quotient"):
            q = self.quotient_tex
            self.quotient_tex_parened = q if self._is_atomic(q) else "(%s)" % q

    def spanclass(self):
        s = "subgp"
        if self.characteristic:
            s += " chargp"
        elif self.normal:
            s += " normgp"
        return s

    def make_span(self):
        return '<span class="{}" data-sgid="{}">${}$</span>'.format(
            self.spanclass(), self.label, self.subgroup_tex
        )

    @staticmethod
    def _is_atomic(s):
        return not any(sym in s for sym in [".", ":", r"\times", r"\rtimes", r"\wr"])

    def show_special_labels(self):
        raw = [x.split(".")[-1] for x in self.special_labels]
        specials = []
        for x in raw:
            if (
                x == "N" or x == "M"
            ):  # labels for normal subgroups and maximal subgroups
                continue
            if x == "Z":
                specials.append(display_knowl("group.center", "center"))
            elif x == "D":
                specials.append(
                    display_knowl("group.commutator_subgroup", "commutator subgroup")
                )
            elif x == "F":
                specials.append(
                    display_knowl("group.fitting_subgroup", "Fitting subgroup")
                )
            elif x == "Phi":
                specials.append(
                    display_knowl("group.frattini_subgroup", "Frattini subgroup")
                )
            elif x == "R":
                specials.append(display_knowl("group.radical", "radical"))
            elif x == "S":
                specials.append(display_knowl("group.socle", "socle"))
            else:
                n = to_ordinal(int(x[1:]) + 1)
                if x.startswith("U"):
                    specials.append(
                        "%s term in the %s"
                        % (
                            n,
                            display_knowl("group.upper_central_series", "upper central series"),
                        )
                    )
                elif x.startswith("L"):
                    specials.append(
                        "%s term in the %s"
                        % (
                            n,
                            display_knowl("group.lower_central_series", "lower central series"),
                        )
                    )
                elif x.startswith("D"):
                    specials.append(
                        "%s term in the %s"
                        % (n, display_knowl("group.derived_series", "derived series"))
                    )
                # Don't show chief series since it's not canonical
        if self.sylow:
            specials.append(
                display_knowl("group.sylow_subgroup", "%s-Sylow subgroup" % self.sylow)
            )
        return ", ".join(specials)

    def _lookup(self, label, data, Wtype):
        for rec in data:
            if rec["label"] == label:
                return Wtype(label, rec)
            elif rec.get("short_label") == label:
                return Wtype(rec["label"], rec)

    @lazy_attribute
    def _full(self):
        """
        Get information from gps_groups for each of the abstract groups included here (the subgroup, the ambient group and the quotient, if normal)
        """
        labels = [self.subgroup, self.ambient]
        if self.normal:
            labels.append(self.quotient)
        if self.weyl_group is not None:
            labels.append(self.weyl_group)
        if self.aut_weyl_group is not None:
            labels.append(self.aut_weyl_group)
        if self.projective_image is not None:
            labels.append(self.projective_image)
        return list(
            db.gps_groups.search({"label": {"$in": labels}})
        )  # should maybe project and just retrieve needed cols

    @lazy_attribute
    def sub(self):
        S = self._lookup(self.subgroup, self._full, WebAbstractGroup)
        # We set various properties from S for create_boolean_subgroup_string
        for prop in [
            "pgroup",
            "is_elementary",
            "Zgroup",
            "metacyclic",
            "supersolvable",
            "is_hyperelementary",
            "monomial",
            "metabelian",
            "nab_simple",
            "ab_simple",
            "Agroup",
            "quasisimple",
            "ab_perfect",
            "almost_simple",
            "rational",
        ]:
            setattr(self, prop, getattr(S, prop))
        return S

    @lazy_attribute
    def amb(self):
        return self._lookup(self.ambient, self._full, WebAbstractGroup)

    @lazy_attribute
    def quo(self):
        return self._lookup(self.quotient, self._full, WebAbstractGroup)

    @lazy_attribute
    def weyl(self):
        if self.weyl_group is not None:
            return self._lookup(self.weyl_group, self._full, WebAbstractGroup)

    @lazy_attribute
    def aut_weyl(self):
        if self.aut_weyl_group is not None:
            return self._lookup(self.aut_weyl_group, self._full, WebAbstractGroup)

    @lazy_attribute
    def proj_img(self):
        if self.projective_image is not None:
            return self._lookup(self.projective_image, self._full, WebAbstractGroup)

    @lazy_attribute
    def _others(self):
        """
        Get information from gps_subgroups for each of the other subgroups referred to
        (centralizer, complements, contained_in, contains, core, normal_closure, normalizer)
        """
        labels = []

        def make_full(label):
            return "%s.%s" % (self.ambient, label)

        for label in [
            self.centralizer,
            self.core,
            self.normal_closure,
            self.normalizer,
        ]:
            if label:
                labels.append(make_full(label))
        for llist in [self.complements, self.contained_in, self.contains]:
            if llist:
                labels.extend([make_full(label) for label in llist])
        return list(db.gps_subgroups.search({"label": {"$in": labels}}))

    def autjugate_subgroups(self):
        return [
            H
            for H in self.amb.subgroups.values()
            if H.aut_label == self.aut_label and H.label != self.label
        ]

    @lazy_attribute
    def centralizer_(self):
        return self._lookup(self.centralizer, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def core_(self):
        return self._lookup(self.core, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def normal_closure_(self):
        return self._lookup(self.normal_closure, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def normalizer_(self):
        return self._lookup(self.normalizer, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def complements_(self):
        if self.complements is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.complements]

    @lazy_attribute
    def contained_in_(self):
        if self.contained_in is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.contained_in]

    @lazy_attribute
    def contains_(self):
        if self.contains is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.contains]

    # The following attributes are used in create_subgroup_boolean_string
    @lazy_attribute
    def semidirect(self):
        return self.split and not self.direct

    @lazy_attribute
    def nab_perfect(self):
        return self.perfect and not self.abelian

    @lazy_attribute
    def nonabelian(self):
        return not self.abelian

    @lazy_attribute
    def nonsolvable(self):
        return not self.solvable

    @lazy_attribute
    def is_sylow(self):
        return self.sylow > 1

    @lazy_attribute
    def is_hall(self):
        return self.hall > 1

    @lazy_attribute
    def thecenter(self):
        return any(x.split(".")[-1] == "Z" for x in self.special_labels)

    @lazy_attribute
    def thecommutator(self):
        return any(x.split(".")[-1] == "D" for x in self.special_labels)

    @lazy_attribute
    def thefrattini(self):
        return any(x.split(".")[-1] == "Phi" for x in self.special_labels)

    @lazy_attribute
    def thefitting(self):
        return any(x.split(".")[-1] == "F" for x in self.special_labels)

    @lazy_attribute
    def theradical(self):
        return any(x.split(".")[-1] == "R" for x in self.special_labels)

    @lazy_attribute
    def thesocle(self):
        return any(x.split(".")[-1] == "S" for x in self.special_labels)


# Conjugacy class labels do not contain the group
class WebAbstractConjClass(WebObj):
    table = db.gps_groups_cc

    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        if data is None:
            data = db.gps_groups_cc.lucky({"group": ambient_gp, "label": label})
        WebObj.__init__(self, label, data)

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={self.ambient_gp}%7C{self.labe}%7Ccomplex">{name}</a>'

class WebAbstractDivision(object):
    def __init__(self, ambient_gp, label, classes):
        self.ambient_gp = ambient_gp
        self.label = label
        self.classes = classes
        self.order = classes[0].order

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={self.ambient_gp}%7C{self.label}%7Crational">{name}</a>'

class WebAbstractAutjClass(object):
    def __init__(self, ambient_gp, label, classes):
        self.ambient_gp = ambient_gp
        self.label = label
        self.classes = classes
        self.order = classes[0].order


class WebAbstractCharacter(WebObj):
    table = db.gps_char

    def type(self):
        if self.indicator == 0:
            return "C"
        if self.indicator > 0:
            return "R"
        return "S"

    def display_knowl(self, name=None):
        label = self.label
        if not name:
            name = label
        return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cchar_data&args={label}">{name}</a>'


class WebAbstractRationalCharacter(WebObj):
    table = db.gps_qchar

    def display_knowl(self, name=None):
        label = self.label
        if not name:
            name = label
        return (
            '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=rchar_data&args=%s">%s</a>'
            % (name, label, name)
        )


class WebAbstractSupergroup(WebObj):
    table = db.gps_subgroups

    def __init__(self, sub_or_quo, typ, label, data=None):
        self.sub_or_quo_gp = sub_or_quo
        self.typ = typ
        WebObj.__init__(self, label, data)
