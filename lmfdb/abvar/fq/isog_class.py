# -*- coding: utf-8 -*-

"""
TODO
- add geometric_number_fields, geometric_galois_groups
- add search on max twist degree?
- has geometric supersingular factor (has a degree 1 factor geometrically)
- search on discriminant over the center (absolute norm down to Q)
- Use the polredabs polynomial to give the places.  It's a bit weird to have Q(sqrt(-1)) represented using the polynomial x^2 - 1481250*x + 95367431640625
"""

from flask import url_for
from collections import Counter

from lmfdb.utils import encode_plot, display_float
from lmfdb.logger import make_logger

from lmfdb import db
from lmfdb.app import app

from sage.all import Factorization, FreeAlgebra
from sage.misc.latex import latex
from sage.misc.cachefunc import cached_method
from sage.misc.lazy_attribute import lazy_attribute
from sage.plot.all import line, points, circle, Graphics
from sage.rings.all import Integer, QQ, RR, ZZ

from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.utils import (
    coeff_to_poly,
    display_knowl,
    integer_divisors,
    list_to_factored_poly_otherorder,
    web_latex,
)
from lmfdb.number_fields.web_number_field import nf_display_knowl, field_pretty
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
from lmfdb.abvar.fq.web_abvar import av_display_knowl, av_data  # , av_knowl_guts

def maxq(g, p):
    # This should eventually move to stats
    maxspec = {
        2: {1: 1024, 2: 1024, 3: 16, 4: 4, 5: 2, 6: 2},
        3: {1: 729, 2: 729, 3: 9, 4: 3, 5: 3},
        5: {1: 625, 2: 625, 3: 25, 4: 5},
        7: {1: 343, 2: 343, 3: 7},
    }
    maxgen = {1: 500, 2: 211, 3: 25}
    if p < 10:
        return maxspec[p][g]
    else:
        return maxgen[g]

logger = make_logger("abvarfq")

#########################
#   Label manipulation
#########################

def validate_label(label):
    parts = label.split(".")
    if len(parts) != 3:
        raise ValueError("it must be of the form g.q.iso, with g a dimension and q a prime power")
    g, q, iso = parts
    try:
        g = int(g)
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is an integer")
    try:
        q = Integer(q)
        if not q.is_prime_power():
            raise ValueError
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is a prime power")
    coeffs = iso.split("_")
    if len(coeffs) != g:
        raise ValueError("the final part must be of the form c1_c2_..._cg, with g=%s components" % (g))
    if not all(c.isalpha() and c == c.lower() for c in coeffs):
        raise ValueError("the final part must be of the form c1_c2_..._cg, with each ci consisting of lower case letters")


def diagram_js(layers, display_opts):
    ll = [
        [
            node.label, # grp.subgroup
            node.label, # grp.short_label
            node.tex, # grp.subgroup_tex
            1, # grp.count (never want conjugacy class counts)
            node.rank, # grp.subgroup_order
            node.img,
            node.x, # grp.diagramx[0] if aut else (grp.diagramx[2] if grp.normal else grp.diagramx[1])
            [node.x, node.x, node.x, node.x], # grp.diagram_aut_x if aut else grp.diagram_x
        ]
        for node in layers[0]
    ]
    if len(ll) == 0:
        display_opts["w"] = display_opts["h"] = 0
        return [], [], 0
    ranks = [node[4] for node in ll]
    rank_ctr = Counter(ranks)
    ranks = sorted(rank_ctr)
    # We would normally make rank_lookup a dictionary, but we're passing it to the horrible language known as javascript
    # The format is for compatibility with subgroup lattices
    rank_lookup = [[r, r, 0] for r in ranks]
    max_width = max(rank_ctr.values())
    display_opts["w"] = min(100 * max_width, 20000)
    display_opts["h"] = 160 * len(ranks)

    return [ll, layers[1]], rank_lookup, len(ranks)

class AbvarFq_isoclass():
    """
    Class for an isogeny class of abelian varieties over a finite field
    """
    name = "isogeny"
    def __init__(self, dbdata):
        if "size" not in dbdata:
            dbdata["size"] = None
        if "zfv_index" not in dbdata:
            dbdata["zfv_is_bass"] = None
            dbdata["zfv_is_maximal"] = None
            dbdata["zfv_index"] = None
            dbdata["zfv_index_factorization"] = None
            dbdata["zfv_plus_index"] = None
            dbdata["zfv_plus_index_factorization"] = None
            dbdata["zfv_plus_norm"] = None
        if "jacobian_count" not in dbdata:
            dbdata["jacobian_count"] = None
        self.__dict__.update(dbdata)
        self.make_class()

    @classmethod
    def by_label(cls, label):
        """
        Searches for a specific isogeny class in the database by label.
        """
        try:
            data = db.av_fq_isog.lookup(label)
            return cls(data)
        except (AttributeError, TypeError):
            raise ValueError("Label not found in database")

    def make_class(self):
        self.decompositioninfo = decomposition_display(list(zip(self.simple_distinct, self.simple_multiplicities)))
        self.basechangeinfo = self.basechange_display()
        self.formatted_polynomial = list_to_factored_poly_otherorder(self.polynomial, galois=False, vari="x")
        if self.is_simple and QQ['x'](self.polynomial).is_irreducible():
            self.expanded_polynomial = ''
        else:
            self.expanded_polynomial = latex(QQ[['x']](self.polynomial))
        if self.zfv_index_factorization is not None:
            self.zfv_index_factorization_latex = latex(Factorization(self.zfv_index_factorization))
        if self.zfv_plus_index_factorization is not None:
            self.zfv_plus_index_factorization_latex = latex(Factorization(self.zfv_plus_index_factorization))


    @property
    def p(self):
        q = Integer(self.q)
        p, _ = q.is_prime_power(get_data=True)
        return p

    @property
    def r(self):
        q = Integer(self.q)
        _, r = q.is_prime_power(get_data=True)
        return r

    @property
    def polygon_slopes(self):
        # Remove the multiset indicators
        return [s[:-1] for s in self.slopes]

    @property
    def polynomial(self):
        return self.poly

    def field(self, q=None):
        if q is None:
            p = self.p
            r = self.r
        else:
            p, r = Integer(q).is_prime_power(get_data=True)
        if r == 1:
            return r"\F_{%s}" % p
        else:
            return r"\F_{%s^{%s}}" % (p, r)

    def nf(self):
        if self.is_simple:
            return self.number_fields[0]
        else:
            return None

    def newton_plot(self):
        S = [QQ(s) for s in self.polygon_slopes]
        C = Counter(S)
        pts = [(0, 0)]
        x = y = 0
        for s in sorted(C):
            c = C[s]
            x += c
            y += c * s
            pts.append((x, y))
        L = Graphics()
        L += line([(0, 0), (0, y + 0.2)], color="grey")
        for i in range(1, y + 1):
            L += line([(0, i), (0.06, i)], color="grey")
        for i in range(1, C[0]):
            L += line([(i, 0), (i, 0.06)], color="grey")
        for i in range(len(pts) - 1):
            P = pts[i]
            Q = pts[i + 1]
            for x in range(P[0], Q[0] + 1):
                L += line(
                    [(x, P[1]), (x, P[1] + (x - P[0]) * (Q[1] - P[1]) / (Q[0] - P[0]))],
                    color="grey",
                )
            for y in range(P[1], Q[1]):
                L += line(
                    [(P[0] + (y - P[1]) * (Q[0] - P[0]) / (Q[1] - P[1]), y), (Q[0], y)],
                    color="grey",
                )
        L += line(pts, thickness=2)
        L.axes(False)
        L.set_aspect_ratio(1)
        return encode_plot(L, pad=0, pad_inches=0, bbox_inches="tight")

    def circle_plot(self):
        pts = []
        pi = RR.pi()
        for angle in self.angles:
            angle = RR(angle) * pi
            c = angle.cos()
            s = angle.sin()
            if abs(s) < 0.00000001:
                pts.append((c, s))
            else:
                pts.extend([(c, s), (c, -s)])
        P = circle((0, 0), 1, color="black", thickness=2.5)
        P[0].set_zorder(-1)
        P += points(pts, size=300, rgbcolor="darkblue")
        P.axes(False)
        P.set_aspect_ratio(1)
        return encode_plot(P, pad=0, pad_inches=None, transparent=True, axes_pad=0.04)

    @lazy_attribute
    def weak_equivalence_classes(self):
        return list(db.av_fq_weak_equivalences.search({"isog_label": self.label}))

    @lazy_attribute
    def endring_poset(self):
        # The poset of endomorphism rings for abelian varieties in this isogeny class
        # For ordinary isogeny classes, these are precisely the sub-orders of the maximal order that contain the Frobenius order
        class LatNode:
            def __init__(self, label):
                self.label = label
                self.index = ZZ(label.split(".")[0])
                self.tex = tex[label]
                self.img = texlabels[self.tex]
                self.rank = sum(e for (p,e) in self.index.factor())
                self.x = xcoord[label]
        parents = {}
        pic_size = {}
        num_wes = Counter()
        num_ind = Counter()
        xcoord = {}
        for rec in self.weak_equivalence_classes:
            R = rec['multiplicator_ring']
            N = ZZ(R.split(".")[0])
            num_wes[R] += 1
            num_ind[N] += 1
            if rec['is_invertible']:
                parents[R] = rec['minimal_overorders']
                pic_size[R] = rec['pic_size']
                xcoord[R] = rec['diagramx']
        if not pic_size:
            return [], [] # no weak equivalence class data for this isogeny class
        tex = {}
        texlabels = set()
        for R, npic in pic_size.items():
            N, i = R.split(".")
            N = ZZ(N)
            if N == 1:
                factored_index = "1"
            else:
                factored_index = r"\cdot".join((f"{p}^{{{e}}}" if e > 1 else f"{p}") for (p, e) in N.factor())
            istr = f"_{{{i}}}" if num_ind[N] > 1 else ""
            we_pic = f"{num_wes[R]}\cdot{pic_size[R]}" if num_wes[R] > 1 else f"{pic_size[R]}"
            tex[R] = "[%s]^{%s}%s" % (factored_index, we_pic, istr)
            texlabels.add(tex[R])
        texlabels = {rec["label"]: rec["image"] for rec in db.av_fq_teximages.search({"label": {"$in": list(texlabels)}})}
        nodes = [LatNode(lab) for lab in pic_size]
        edges = []
        if nodes:
            maxrank = max(node.rank for node in nodes)
            for node in nodes:
                node.rank = maxrank - node.rank
                edges.extend([[node.label, lab] for lab in parents[node.label]])
        return nodes, edges


    @lazy_attribute
    def diagram_js(self):
        display_opts = {}
        graph, rank_lookup, num_layers = diagram_js(self.endring_poset, display_opts)
        return {
            'string': f'var [sdiagram,graph] = make_sdiagram("endring_diagram", "{self.label}", {graph}, {rank_lookup}, {num_layers});',
            'display_opts': display_opts
        }



    def endringinfo(self, endring):
        for elt in self.weak_equivalence_classes:
            if elt['multiplicator_ring'] == endring and elt['is_invertible']:
                rec = elt
                break
        else:
            assert false

        num_we = sum(1 for elt in self.weak_equivalence_classes if elt['multiplicator_ring'] == endring)

        R = FreeAlgebra(ZZ, ["F", "V"])
        F, V = R.gens()
        index = int(endring.split(".")[0])
        pows = [V**i for i in reversed(range(0, self.g))] + [F**i for i in range(1, self.g + 1)]
        def to_R(num):
            assert len(num) == len(pows)
            return sum(c*p for c, p in zip(num, pows))

        # Ring display
        names = ["R"]
        if index == 1:
            names.append(r"\mathbb{Z}[F, V]")
        if rec["is_Zconductor_sum"]:
            names.append(r"\mathbb{Z} + \mathfrak{f}_R")
        elif rec["is_ZFVconductor_sum"]:
            names.append(r"\mathbb{Z}[F, V] + \mathfrak{f}_R")
        gen = rec["generator_over_ZFV"]
        if gen and gen[1] != [0]*4:
            d, num = gen
            num = to_R(num)
            gens = ["F", "V"]
            if num not in ZZ:
                s = latex(num)
                if d != 1:
                    s = r"\frac{1}{%s}(%s)" % (d, s)
                gens.append(s)
            names.append(fr"\mathbb{{Z}}{','.join(gens)}]")
        names = "=".join(names)

        # conductor
        if index == 1:
            conductor = r"\mathbb{Z}[F, V]"
        else:
            M, d, num = rec["conductor"]
            conductor = latex(to_R(num))
            if d != 1:
                conductor = r"\frac{1}{%s}(%s)" % (d, conductor)
            conductor = fr"\langle {M},{conductor}\rangle"
        if rec["pic_invs"] == []:
            pic_url = url_for("abstract.by_label", label="1.1")
            pic = "C_1"
        else:
            pic_url = url_for("abstract.by_abelian_label", label="ab/" + "_".join(str(c) for c in rec["pic_invs"]))
            pic = r"\times ".join(f"C_{{{c}}}" for c in rec["pic_invs"])
        if rec["cohen_macaulay_type"] == 1:
            cm_type = "$1$ (%s)" % display_knowl('ag.gorenstein', 'Gorenstein')
        else:
            cm_type = "$%s$" % rec["cohen_macaulay_type"]

        ans = "\n".join([
            f'Information on the endomorphism ring ${names}$<br>',
            "<table>",
            f"<tr><td>{display_knowl('av.endomorphism_ring_index', 'Index')}:</td><td>${index}$</td></tr>",
            fr"<tr><td>{display_knowl('av.endomorphism_ring_conductor', 'Conductor')} $\mathfrak{{f}}_R$:</td><td>${conductor}$</td></tr>",
            f"<tr><td>{display_knowl('av.fq.picard_group', 'Picard group')}</td><td><a href='{pic_url}'>${pic}$</td></tr>",
            f"<tr><td>{display_knowl('ag.cohen_macaulay_type', 'Cohen-Macaulay type')}</td><td>{cm_type}</td></tr>",
            f"<tr><td>Num. {display_knowl('av.fq.weak_equivalence_class', 'weak equivalence classes')}</td><td>${num_we}$</td></tr>",
            "</table>"
        ])
        # Might also want to add rational point structure for varieties in this class, link to search page for polarized abvars...
        return ans

    def _make_jacpol_property(self):
        ans = []
        if self.has_principal_polarization == 1:
            ans.append((None, "Principally polarizable"))
        elif self.has_principal_polarization == -1:
            ans.append((None, "Not principally polarizable"))
        if self.has_jacobian == 1:
            ans.append((None, "Contains a Jacobian"))
        elif self.has_jacobian == -1:
            ans.append((None, "Does not contain a Jacobian"))
        return ans

    def properties(self):
        props = [
            ("Label", self.label),
            (None, '<img src="%s" width="200" height="150"/>' % self.circle_plot()),
            ("Base field", "$%s$" % (self.field(self.q))),
            ("Dimension", "$%s$" % (self.g)),
            ("$p$-rank", "$%s$" % (self.p_rank)),
            # ('Weil polynomial', '$%s$'%(self.formatted_polynomial)),
            ("Ordinary", "yes" if self.is_ordinary() else "no"),
            ("Supersingular", "yes" if self.is_supersingular() else "no"),
            ("Simple", "yes" if self.is_simple else "no"),
            ("Geometrically simple", "yes" if self.is_geometrically_simple else "no"),
            ("Primitive", "yes" if self.is_primitive else "no"),
        ]
        if self.has_principal_polarization != 0:
            props += [("Principally polarizable", "yes" if self.has_principal_polarization == 1 else "no")]
        if self.has_jacobian != 0:
            props += [("Contains a Jacobian", "yes" if self.has_jacobian == 1 else "no")]
        return props

    # at some point we were going to display the weil_numbers instead of the frobenius angles
    # this is not covered by the tests
    # def weil_numbers(self):
    #    q = self.q
    #    ans = ""
    #    for angle in self.angles:
    #        if ans != "":
    #            ans += ", "
    #        ans += '\sqrt{' +str(q) + '}' + '\exp(\pm i \pi {0}\ldots)'.format(angle)
    # ans += "\sqrt{" +str(q) + "}" + "\exp(-i \pi {0}\ldots)".format(angle)
    #    return ans

    def friends(self):
        friends = []
        if self.g <= 3:
            if self.p < 10:
                dispcols = "1-10"
            elif self.p < 50:
                dispcols = "1-50"
            else:
                dispcols = f"1-10,{self.p}"
            # When over a non-prime field, we need to
            poly = coeff_to_poly(self.poly, "T")
            if self.r > 1:
                poly = poly.subs(poly.parent().gen()**self.r)
            poly = str(poly).replace(" ", "").replace("**","%5E").replace("*","").replace("+", "%2B")
            friends.append(("L-functions", url_for("l_functions.rational") + f"?search_type=Euler&motivic_weight=1&degree={2*self.g*self.r}&n={dispcols}&euler_constraints=F{self.p}%3D{poly}"))
        return friends

    def frob_angles(self):
        ans = ""
        eps = 0.00000001
        for angle in self.angles:
            angstr = display_float(angle, 12, 'round')
            if ans != "":
                ans += ", "
            if abs(angle) > eps and abs(angle - 1) > eps:
                angle = r"$\pm" + angstr + "$"
            else:
                angle = "$" + angstr + "$"
            ans += angle
        return ans

    def is_ordinary(self):
        return self.p_rank == self.g

    def is_supersingular(self):
        return all(slope == "1/2" for slope in self.polygon_slopes)

    def display_slopes(self):
        return "[" + ", ".join(self.polygon_slopes) + "]"

    def length_A_counts(self):
        return len(self.abvar_counts)

    def length_C_counts(self):
        return len(self.curve_counts)

    def display_number_field(self):
        if self.is_simple:
            if self.nf():
                return nf_display_knowl(self.nf(), field_pretty(self.nf()))
            else:
                return "The number field of this isogeny class is not in the database."
        else:
            return "The class is not simple"

    def display_galois_group(self):
        if not hasattr(self, "galois_groups") or not self.galois_groups[0]:
            # the number field was not found in the database
            return "The Galois group of this isogeny class is not in the database."
        else:
            return transitive_group_display_knowl(self.galois_groups[0])

    def decomposition_display_search(self):
        if self.is_simple:
            return "simple"
        ans = ""
        for simp, e in zip(self.simple_distinct, self.simple_multiplicities):
            url = url_for("abvarfq.by_label", label=simp)
            if ans != "":
                ans += "$\\times$ "
            if e == 1:
                ans += '<a href="{1}">{0}</a>'.format(simp, url)
                ans += " "
            else:
                ans += '<a href="{1}">{0}</a>'.format(simp, url) + "<sup> {0} </sup> ".format(e)
        return '<span>' + ans + '</span>'

    def alg_clo_field(self):
        if self.r == 1:
            return r"\overline{\F}_{%s}" % (self.p)
        else:
            return r"\overline{\F}_{%s^{%s}}" % (self.p, self.r)

    def ext_field(self, s):
        n = s * self.r
        if n == 1:
            return r"\F_{%s}" % (self.p)
        else:
            return r"\F_{%s^{%s}}" % (self.p, n)

    @cached_method
    def endo_extensions(self):
        return list(db.av_fq_endalg_factors.search({"base_label": self.label}))

    def relevant_degs(self):
        return integer_divisors(Integer(self.geometric_extension_degree))[1:-1]

    def endo_extension_by_deg(self, degree):
        return [
            [factor["extension_label"], factor["multiplicity"]]
            for factor in self.endo_extensions()
            if factor["extension_degree"] == degree
        ]

    def display_endo_info(self, degree, do_describe=True):
        # When degree > 1 we find the factorization by looking at the extension database
        if degree > 1:
            factors = self.endo_extension_by_deg(degree)
            if not factors:
                return "The data at degree %s is missing." % degree, do_describe
            ans = "The base change of $A$ to ${0}$ is ".format(self.ext_field(degree))
        else:
            factors = list(zip(self.simple_distinct,
                               self.simple_multiplicities))
            if self.is_simple:
                ans = "The endomorphism algebra of this simple isogeny class is "
            else:
                ans = "The isogeny class factors as "
        dec_display = decomposition_display(factors)
        if dec_display == "simple":
            end_alg = describe_end_algebra(self.p, factors[0][0])
            if end_alg is None:
                return no_endo_data(), do_describe
            if degree > 1:
                ans += "the simple isogeny class "
                ans += av_display_knowl(factors[0][0])
                ans += " and its endomorphism algebra is "
            ans += end_alg[1]
        elif len(factors) == 1:
            end_alg = describe_end_algebra(self.p, factors[0][0])
            if end_alg is None:
                return no_endo_data(), do_describe
            ans += dec_display + " and its endomorphism algebra is "
            ans += matrix_display(factors[0], end_alg)
        else:
            ans += dec_display
            if do_describe:
                ans += " and its endomorphism algebra is a direct product of the endomorphism algebras for each isotypic factor"
                do_describe = False
            ans += ". The endomorphism algebra for each factor is: \n"
            ans += non_simple_loop(self.p, factors)
        return ans, do_describe

    def all_endo_info_display(self):
        do_describe = False
        ans = "<p> All geometric endomorphisms are defined over ${0}$.</p> \n ".format(self.ext_field(self.geometric_extension_degree))
        base_endo_info, do_describe = self.display_endo_info(1)
        ans += g2_table(self.field(), base_endo_info, True)
        if self.geometric_extension_degree != 1:
            geometric_endo_info, do_describe = self.display_endo_info(self.geometric_extension_degree, do_describe)
            ans += g2_table(self.alg_clo_field(), geometric_endo_info, True)
        if self.relevant_degs():
            ans += "\n <b>Remainder of endomorphism lattice by field</b>\n"
            ans += "<ul>\n"
            for deg in self.relevant_degs():
                ans += "<li>"
                new_endo_info, do_describe = self.display_endo_info(deg, do_describe)
                ans += g2_table(self.ext_field(deg), new_endo_info, False)
                ans += "</li>\n"
            ans += "</ul>\n"
        return ans

    def basechange_display(self):
        if self.is_primitive:
            return "primitive"
        else:
            models = self.primitive_models
            ans = '<table class = "ntdata">\n'
            ans += "<tr><td>Subfield</td><td>Primitive Model</td></tr>\n"
            for model in models:
                ans += '  <tr><td class="center">${0}$</td><td>'.format(self.field(model.split(".")[1]))
                ans += av_display_knowl(model) + " "
                ans += "</td></tr>\n"
            ans += "</table>\n"
            return ans

    def twist_display(self, show_all):
        if not self.twists:
            return "<p>This isogeny class has no twists.</p>"
        if show_all:
            ans = "<p> Below is a list of all twists of this isogeny class.</p>"
        else:
            ans = "<p> Below are some of the twists of this isogeny class.</p>"
        ans += '<table class = "ntdata">\n'
        ans += "<thead><tr><th>Twist</th><th>Extension degree</th><th>Common base change</th></tr></thead><tbody>\n"
        i = 0
        for twist in self.twists:
            if twist[2] <= 3 or show_all or i < 3:
                if self.q ** twist[2] <= maxq(self.g, self.p):
                    bc = av_display_knowl(twist[1])
                else:
                    bc = "(not in LMFDB)"
                ans += "<tr><td>%s</td><td style='center'>$%s$</td><td>%s</td></tr>\n" % (av_display_knowl(twist[0]), str(twist[2]), bc)
                i += 1
        ans += "</tbody></table>\n"
        return ans

    def curve_display(self):
        def show_curve(cv):
            cv = cv.replace("*", "")
            if "=" not in cv:
                cv = cv + "=0"
            return "  <li>$%s$</li>\n" % cv
        if hasattr(self, "curves") and self.curves:
            s = "\n<ul>\n"
            cutoff = 20 if len(self.curves) > 30 else len(self.curves)
            for cv in self.curves[:cutoff]:
                s += show_curve(cv)
            if cutoff < len(self.curves):
                s += '  <li id="curve_shower">and <a href="#" onclick="show_more_curves(); return false;">%s more</a></li>\n</ul>\n<ul id="more_curves" style="display: none;">\n' % (len(self.curves) - cutoff)
                for cv in self.curves[cutoff:]:
                    s += show_curve(cv)
            s += "</ul>\n"
            return s
        else:
            return ""




    header_polarized_varieties = [
        ('label', 'av.fq.lmfdb_label', 'Label'),
        ('degree', 'av.polarization_degree', 'Degree'),
        ('aut_group', 'av.aut_group', 'Automorphism Group'),
        #('geom_aut_group', 'av.geom_aut_group', 'Geometric automorphism group'),
        ('endomorphism_ring', 'av.endomorphism_ring', 'Endomorphism ring'),
        ('kernel', 'av.polarization_kernel', 'Kernel'),
    ]

    @lazy_attribute
    def polarized_abelian_varieties(self):
        cols = [elt for elt, _ ,_ in self.header_polarized_varieties]
        return list(db.av_fq_pol.search({"isog_label": self.label}, cols))

    def display_header_polarizations(self):
        ths = "\n".join(
            f'<th class="sticky-head dark">{display_knowl(kwl, title=title)}</th>' for _, kwl, title in self.header_polarized_varieties)

        return f'<thead><tr>\n{ths}\n</tr></thead>'


    def display_rows_polarizations(self, query=None):
        polarized_columns_display = {
        'aut_group': lambda x : abstract_group_display_knowl(x['aut_group']),
        'degree': lambda x : web_latex(x['degree']),
        'endomorphism_ring': lambda x : x['endomorphism_ring'],
        # 'geom_aut_group' : lambda x: abstract_group_display_knowl(x['geom_aut_group']),
        'isom_label' : lambda x : x['isom_label'],
        'kernel' : lambda x : x['kernel'],
        'label' : lambda x : x['label'],
        }
        res = ""
        #FIXME filter by query
        for i,elt in enumerate(self.polarized_abelian_varieties):
            shade = 'dark' if i%2 == 0 else 'light'
            res += f'<tr class="{shade}">\n' + "\n".join([f"<td>{polarized_columns_display[col](elt)}</td>" for col, _, _ in self.header_polarized_varieties]) + "</tr>\n"
        return f'<tbody>\n{res}</tbody>'

    def display_polarizations(self, query=None):
        return rf"""
        <table class="ntdata">
          {self.display_header_polarizations()}
          {self.display_rows_polarizations()}
        </table>
"""




@app.context_processor
def ctx_decomposition():
    return {"av_data": av_data}

def describe_end_algebra(p, extension_label):
    # This should eventually be done with a join, but okay for now
    factor_data = db.av_fq_endalg_data.lookup(extension_label)
    if factor_data is None:
        return None
    center = factor_data["center"]
    divalg_dim = factor_data["divalg_dim"]
    places = factor_data["places"]
    brauer_invariants = factor_data["brauer_invariants"]
    ans = ["", ""]
    if center == "1.1.1.1" and divalg_dim == 4:
        ans[0] = "B"
        ans[1] = r"the quaternion algebra over {0} ramified at ${1}$ and $\infty$.".format(nf_display_knowl(center, field_pretty(center)), p)
    elif int(center.split(".")[1]) > 0:
        ans[0] = "B"
        if divalg_dim == 4:
            ans[1] = "the quaternion algebra"
        else:
            ans[1] = "the division algebra of dimension " + str(divalg_dim)
        ans[1] += " over {0} ramified at both real infinite places.".format(nf_display_knowl(center, field_pretty(center)))
    elif divalg_dim == 1:
        ans[0] = "K"
        ans[1] = nf_display_knowl(center, field_pretty(center)) + "."
    else:
        ans[0] = "B"
        if divalg_dim == 4:
            ans[1] = "the quaternion algebra"
        else:
            ans[1] = "the division algebra of dimension " + str(divalg_dim)
        ans[1] += " over {0} with the following ramification data at primes above ${1}$, and unramified at all archimedean places:".format(nf_display_knowl(center, field_pretty(center)), p)
        ans[1] += '</td></tr><tr><td><table class = "ntdata"><tr><td>$v$</td>'
        for prime in places:
            ans[1] += '<td class="center"> {0} </td>'.format(primeideal_display(p, prime))
        ans[1] += r"</tr><tr><td>$\operatorname{inv}_v$</td>"
        for inv in brauer_invariants:
            ans[1] += '<td class="center">${0}$</td>'.format(inv)
        ans[1] += "</tr></table>\n"
        center_poly = db.nf_fields.lookup(center, 'coeffs')
        center_poly = latex.latex(ZZ["x"](center_poly))
        ans[1] += r"where $\pi$ is a root of ${0}$.".format(center_poly)
        ans[1] += "\n"
    return ans

def primeideal_display(p, prime_ideal):
    ans = "($ {0} $".format(p)
    if prime_ideal == ["0"]:
        ans += ")"
        return ans
    else:
        ans += "," + web_latex(coeff_to_poly(prime_ideal, "pi")) + ")"
        return ans

def decomposition_display(factors):
    if len(factors) == 1 and factors[0][1] == 1:
        return "simple"
    factor_str = ""
    for factor in factors:
        if factor_str != "":
            factor_str += " $\\times$ "
        factor_str += av_display_knowl(factor[0])
        if factor[1] > 1:
            factor_str += "<sup> {0} </sup>".format(factor[1])
    return factor_str

def no_endo_data():
    return "The endomorphism data for this class is not currently in the database."

def g2_table(field, entry, is_bold):
    if is_bold:
        ans = "<b>Endomorphism algebra over ${0}$</b>\n".format(field)
    else:
        ans = "Endomorphism algebra over ${0}$\n".format(field)
    ans += '<table class="g2" style="margin-top: 5px;margin-bottom: 5px;">\n<tr><td>{0}</td></tr>\n</table>\n'.format(entry)
    return ans

def matrix_display(factor, end_alg):
    if end_alg[0] == "K" and end_alg[1] != factor[0] + ".":
        ans = r"$\mathrm{{M}}_{{{0}}}(${1}$)$".format(factor[1], end_alg[1][:-1])
    else:
        ans = r"$\mathrm{{M}}_{{{0}}}({1})$, where ${1}$ is {2}".format(factor[1], end_alg[0], end_alg[1])
    return ans

def non_simple_loop(p, factors):
    ans = '<ul style="margin-top: 5px;margin-bottom: 8px;">\n'
    for factor in factors:
        ans += "<li>"
        ans += av_display_knowl(factor[0])
        if factor[1] > 1:
            ans += "<sup> {0} </sup>".format(factor[1])
        ans += " : "
        end_alg = describe_end_algebra(p, factor[0])
        if end_alg is None:
            ans += no_endo_data()
        elif factor[1] == 1:
            ans += end_alg[1]
        else:
            ans += matrix_display(factor, end_alg)
        ans += "</li>\n"
    ans += "</ul>\n"
    return ans
