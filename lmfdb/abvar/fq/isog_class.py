
"""
TODO
- add geometric_number_fields, geometric_galois_groups
- add search on max twist degree?
- has geometric supersingular factor (has a degree 1 factor geometrically)
- search on discriminant over the center (absolute norm down to Q)
- Use the polredabs polynomial to give the places.  It's a bit weird to have Q(sqrt(-1)) represented using the polynomial x^2 - 1481250*x + 95367431640625
"""

from flask import url_for
from collections import defaultdict, Counter

from lmfdb.utils import encode_plot, display_float
from lmfdb.logger import make_logger

from lmfdb import db
from lmfdb.app import app

from sage.all import Factorization, FreeAlgebra
from sage.rings.all import Integer, QQ, RR, ZZ
from sage.plot.all import line, points, circle, polygon, Graphics
from sage.misc.latex import latex
from sage.misc.cachefunc import cached_method
from sage.misc.lazy_attribute import lazy_attribute

from lmfdb.groups.abstract.web_groups import abstract_group_display_knowl, abelian_group_display_knowl
from lmfdb.utils import list_to_factored_poly_otherorder, coeff_to_poly, web_latex, integer_divisors, teXify_pol, display_knowl
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



def show_singular_support(n):
    if n == 0:
        return r"$\varnothing$"
    elif not n:
        return "not computed"
    return r"$\{" + ",".join(fr"\mathfrak{{P}}_{{ {i} }}" for (i, b) in enumerate(ZZ(n).bits(), 1) if b) + r"\}$"


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

    select_line = rf"""
            Click on an {display_knowl('ag.endomorphism_ring', 'endomorphism ring')},
            with the {display_knowl('av.fq.endomorphism_ring_notation', 'notation') }
            $[\mathrm{{index}}]_{{i}}^{{\# \mathrm{{weak}} \cdot \# \mathrm{{Pic}}}}$,
            in the diagram to see information about it.
"""

    def __init__(self, dbdata):
        for col in ["size", "zfv_is_bass", "zfv_is_maximal", "zfv_index", "zfv_index_factorization", "zfv_plus_index", "zfv_plus_index_factorization", "zfv_plus_norm", "hyp_count", "jacobian_count", "all_polarized_product", "cohen_macaulay_max", "endomorphism_ring_count", "weak_equivalence_count", "zfv_singular_count", "group_structure_count", "zfv_pic_size", "principal_polarization_count", "singular_primes"]:
            if col not in dbdata:
                dbdata[col] = None
        self.__dict__.update(dbdata)

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

    @lazy_attribute
    def decompositionraw(self):
        return list(zip(self.simple_distinct, self.simple_multiplicities))

    @lazy_attribute
    def decompositioninfo(self):
        return decomposition_display(self.decompositionraw)

    @lazy_attribute
    def basechangeinfo(self):
        return self.basechange_display()

    @lazy_attribute
    def formatted_polynomial(self):
        return list_to_factored_poly_otherorder(self.polynomial, galois=False, vari="x")

    @lazy_attribute
    def expanded_polynomial(self):
        if self.is_simple and QQ['x'](self.polynomial).is_irreducible():
            return ""
        else:
            return latex(QQ[['x']](self.polynomial))

    @lazy_attribute
    def zfv_index_factorization_latex(self):
        return latex(Factorization(self.zfv_index_factorization))

    @lazy_attribute
    def zfv_plus_index_factorization_latex(self):
        return latex(Factorization(self.zfv_plus_index_factorization))

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
    def pretty_slopes(self):
        return "[" + ",".join(latex(QQ(s)) for s in self.polygon_slopes) + "]"

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
        xmax = len(S)
        ymax = ZZ(len(S) / 2)
        L += polygon(pts + [(0, ymax)], alpha=0.1)
        for i in range(xmax + 1):
            L += line([(i, 0), (i, ymax)], color="grey", thickness=0.5)
        for j in range(ymax + 1):
            L += line([(0, j), (xmax, j)], color="grey", thickness=0.5)
        L += line(pts, thickness=2)
        for v in pts:
            L += circle(v, 0.06, fill=True)
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

    def filtered_mrings(self, query):
        query["is_invertible"] = True
        query["isog_label"] = self.label
        if len(query) == 2:
            return set(self.endring_data)
        return set(db.av_fq_weak_equivalences.search(query, "multiplicator_ring"))

    @lazy_attribute
    def endring_data(self):
        inv = {}
        ninv = defaultdict(list)
        for rec in self.weak_equivalence_classes:
            mring = rec["multiplicator_ring"]
            if rec["is_invertible"]:
                inv[mring] = rec
            else:
                ninv[mring].append(rec)
        return {mring: [inv[mring]] + ninv[mring] for mring in inv}

    @cached_method(key=lambda self, query: str(query))
    def endring_poset(self, query={}):
        # The poset of endomorphism rings for abelian varieties in this isogeny class
        # For ordinary isogeny classes, these are precisely the sub-orders of the maximal order that contain the Frobenius order
        included_in_query = self.filtered_mrings(query)
        class LatNode:
            def __init__(self, label):
                self.label = label
                self.index = ZZ(label.split(".")[0])
                if label in included_in_query:
                    self.tex = tex[label]
                else:
                    self.tex = r"\cdot"
                if self.tex in texlabels:
                    self.img = texlabels[self.tex]
                else:
                    self.img = texlabels["?"]
                self.rank = sum(e for (p,e) in self.index.factor())
                self.x = xcoord[label]
        parents = {}
        pic_size = {}
        num_wes = Counter()
        num_ind = Counter()
        xcoord = {}
        for R, wes in self.endring_data.items():
            N = ZZ(R.split(".")[0])
            num_wes[R] = len(wes)
            num_ind[N] += 1
            parents[R] = wes[0]['minimal_overorders']
            pic_size[R] = wes[0]['pic_size']
            xcoord[R] = wes[0]['diagramx']
        if not pic_size:
            return [], [] # no weak equivalence class data for this isogeny class
        tex = {}
        texlabels = set(["?", r"\cdot"])
        for R, npic in pic_size.items():
            N, i = R.split(".")
            N = ZZ(N)
            if N == 1:
                factored_index = "1"
            else:
                factored_index = r"\cdot".join((f"{p}^{{{e}}}" if e > 1 else f"{p}") for (p, e) in N.factor())
            istr = f"_{{{i}}}" if num_ind[N] > 1 else ""
            we_pic = rf"{num_wes[R]}\cdot{pic_size[R]}" if num_wes[R] > 1 else f"{pic_size[R]}"
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


    def diagram_js(self, query):
        display_opts = {}
        graph, rank_lookup, num_layers = diagram_js(self.endring_poset(query), display_opts)
        return {
            'string': f'var [sdiagram,graph] = make_sdiagram("subdiagram", "{self.label}", {graph}, {rank_lookup}, {num_layers});',
            'display_opts': display_opts
        }



    @lazy_attribute
    def endring_select_line(self):
        return self.select_line

    @cached_method
    def endring_disp(self, endring):
        we = self.endring_data[endring]
        max_index = max(L[0]["index"] for L in self.endring_data.values())
        disp = {}
        rec = we[0]

        R = FreeAlgebra(ZZ, ["F", "V"])
        F, V = R.gens()
        pows = [V**i for i in reversed(range(0, self.g))] + [F**i for i in range(1, self.g + 1)]
        def to_R(num):
            assert len(num) == len(pows)
            return sum(c*p for c, p in zip(num, pows))

        # Conductor display
        if rec["conductor"]:
            # conductor
            M, d, num = rec["conductor"]
            num = to_R(num)
            if num != 0:
                conductor = latex(num)
                if d != 1:
                    conductor = r"\frac{1}{%s}(%s)" % (d, conductor)
                conductor = fr"\langle {M},{conductor}\rangle_{{\mathcal{{O}}_{{\mathbb{{Q}}(F)}}}}"
            else:
                conductor = r"\mathcal{O}_{\mathbb{Q}[F]}"
                if M != 1:
                    conductor = f"{M} {conductor}"
        else:
            conductor = "not computed"

        # Ring display
        short_names = []
        long_names = []
        if rec["index"] == 1:
            short_names.append(conductor)
            long_names.append(conductor)
        elif rec.get("is_Zconductor_sum") and rec["index"] != max_index: # Don't write for Z[F,V] itself
            short_names.append(r"\mathbb{Z} + \mathfrak{f}_R")
            if rec["conductor"]:
                long_names.append(r"\mathbb{Z} + " + conductor)
        elif rec.get("is_ZFVconductor_sum") and rec["index"] != max_index: # Don't write for Z[F,V] itself
            short_names.append(r"\mathbb{Z}[F, V] + \mathfrak{f}_R")
            if rec["conductor"]:
                long_names.append(r"\mathbb{Z}[F, V] + " + conductor)
        gen = rec.get("generator_over_ZFV")
        if gen:
            d, num = gen
            num = to_R(num)
            gens = ["F", "V"]
            if num != 0:
                s = latex(num)
                if d != 1:
                    s = r"\frac{1}{%s}(%s)" % (d, s)
                gens.append(s)
            gen_name = fr"\mathbb{{Z}}[{','.join(gens)}]"
            short_names.append(gen_name)
            long_names.append(gen_name)

        if rec["conductor"]:
            conductor = f"${conductor}$"

        pic_size = rec["pic_size"]
        if rec["pic_invs"] is not None:
            pic_disp = abelian_group_display_knowl(rec['pic_invs'])
        elif rec["pic_size"] is not None:
            pic_disp = f"Abelian group of order {pic_size}"
        else:
            pic_disp = "not computed"

        av_structure = defaultdict(Counter)
        for w in we:
            av_structure[1][tuple(w["rational_invariants"])] += pic_size
            for n in range(2, 11):
                av_structure[n][tuple(w["higher_invariants"][n-2])] += pic_size
        for n in range(1, 11):
            if len(av_structure[n]) == 1:
                disp[f"av_structure{n}"] = abelian_group_display_knowl(next(iter(av_structure[n])))
            else:
                gps = sorted((-cnt, invs) for (invs, cnt) in av_structure[n].items())
                disp[f"av_structure{n}"] = ",".join("%s ($%s$)" % (abelian_group_display_knowl(invs), -m) for (m, invs) in gps)

        dimensions = Counter()
        for w in we:
            dimensions[tuple(w["dimensions"])] += pic_size
        if len(dimensions) == 1:
            disp["dimensions"] = f"${list(next(iter(dimensions)))}$"
        else:
            dimensions = sorted((-cnt, dims) for (dims, cnt) in dimensions.items())
            disp["dimensions"] = ",".join("$[%s]$ ($%s$)" % (",".join(str(c) for c in dims), -m) for (m, dims) in dimensions)

        disp["short_names"] = short_names
        disp["long_names"] = long_names
        disp["index"] = int(endring.split(".")[0])
        disp["conductor"] = conductor
        disp["pic"] = pic_disp
        disp["av_count"] = len(we) * pic_size
        return disp

    @lazy_attribute
    def _group_structures(self):
        av_structure = defaultdict(Counter)
        for we in self.endring_data.values():
            pic_size = we[0]["pic_size"]
            for w in we:
                av_structure[1][tuple(w["rational_invariants"])] += pic_size
                for n in range(2, 6):
                    av_structure[n][tuple(w["higher_invariants"][n-2])] += pic_size
        return av_structure

    @lazy_attribute
    def group_structures(self):
        N = self.most_group_structures
        av_structure = self._group_structures
        disp = [[] for _ in range(N)]
        for n in range(1, 6):
            if len(av_structure[n]) == 1:
                disp[0].append(abelian_group_display_knowl(next(iter(av_structure[n]))))
                nextj = 1
            else:
                gps = sorted((-cnt, invs) for (invs, cnt) in av_structure[n].items())
                for j, (m, invs) in enumerate(gps):
                    disp[j].append("%s ($%s$)" % (abelian_group_display_knowl(invs), -m))
                nextj = len(gps)
            for j in range(nextj, N):
                disp[j].append("")
        return disp

    @lazy_attribute
    def most_group_structures(self):
        return max(len(opts) for opts in self._group_structures.values())

    def endringinfo(self, endring):
        rec = self.endring_data[endring][0]
        disp = self.endring_disp(endring)

        num_we = len(self.endring_data[endring])
        names = "=".join(["R"] + disp["short_names"])

        if rec["cohen_macaulay_type"] is None:
            cm_type = "not computed"
        else:
            cm_type = "$%s$" % rec["cohen_macaulay_type"]

        ans = [
            f'Information on the {display_knowl("ag.endomorphism_ring", "endomorphism ring")} ${names}$<br>',
            "<table>",
            f"<tr><td>{display_knowl('av.fq.lmfdb_label', 'Label')}:</td><td>{'.'.join(rec['label'].split('.')[3:])}</td></tr>",
            fr"<tr><td>{display_knowl('av.fq.index_of_order', 'Index')} $[\mathcal{{O}}_{{\mathbb{{Q}}[F]}}:R]$:</td><td>${disp['index']}$</td></tr>",
            fr"<tr><td>{display_knowl('av.endomorphism_ring_conductor', 'Conductor')} $\mathfrak{{f}}_R$:</td><td>{disp['conductor']}</td></tr>",
            f"<tr><td>{display_knowl('ag.cohen_macaulay_type', 'Cohen-Macaulay type')}:</td><td>{cm_type}</td></tr>",
            f"<tr><td>{display_knowl('av.fq.singular_primes', 'Singular support')}:</td><td>${show_singular_support(rec['singular_support'])}$</td></tr>",
            f"<tr><td>{display_knowl('ag.fq.point_counts', 'Group structure')}:</td><td>{disp['av_structure1']}</td></tr>",
            f"<tr><td>{display_knowl('av.fq.picard_of_order', 'Picard group')}:</td><td>{disp['pic']}</td></tr>",
            fr"<tr><td>$\# \{{${display_knowl('av.fq.weak_equivalence_class', 'weak equivalence classes')}$\}}$:</td><td>${num_we}$</td></tr>",
            "</table>"
        ]
        # Might also want to add rational point structure for varieties in this class, link to search page for polarized abvars...
        return "\n".join(ans)

    @lazy_attribute
    def singular_primes_disp(self):
        disp = [",".join(teXify_pol(f) for f in P.split(",")) for P in self.singular_primes]
        return [fr"\langle {P} \rangle" for P in disp]

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
            ("Supersingular", "yes" if self.is_supersingular else "no"),
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
            poly = str(poly).replace(" ", "").replace("**", "%5E").replace("*", "").replace("+", "%2B")
            friends.append(("L-functions", url_for("l_functions.rational") + f"?search_type=Euler&motivic_weight=1&degree={2 * self.g * self.r}&n={dispcols}&euler_constraints=F{self.p}%3D{poly}"))
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

    @property
    def is_supersingular(self):
        return all(slope == "1/2" for slope in self.polygon_slopes)

    def is_almost_ordinary(self):
        return self.newton_elevation == 1

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

    def galois_groups_pretty(self):
        # Used in search result pages
        return ", ".join(transitive_group_display_knowl(gal, cache=self.gal_cache) for gal in self.galois_groups)

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

    def display_generator_explanation(self):
        return getattr(self, "curves", None) and any('a' in curve for curve in self.curves)

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
            cv = teXify_pol(cv)
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
        ('degree', 'av.polarization', 'Degree'),
        ('aut_group', 'ag.aut_group', 'Automorphism Group'),
        #('geom_aut_group', 'av.geom_aut_group', 'Geometric automorphism group'),
        ('endomorphism_ring', 'ag.endomorphism_ring', 'Endomorphism ring'),
        ('kernel', 'av.polarization', 'Kernel'),
    ]

    @lazy_attribute
    def polarized_abelian_varieties(self):
        cols = [elt for elt, _ ,_ in self.header_polarized_varieties]
        return list(db.av_fq_pol.search({"isog_label": self.label}, cols, sort=['degree']))

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
        'kernel' : lambda x : abelian_group_display_knowl(x['kernel']),
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
    @lazy_attribute
    def number_principal_polarizations(self):
        if self.polarized_abelian_varieties:
            return sum(1 for elt in self.polarized_abelian_varieties if elt['degree'] == 1)
        else:
            return None


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
        center_poly = latex(ZZ["x"](center_poly))
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
