# -*- coding: utf-8 -*-

from flask import url_for

from sage.all import lazy_attribute, Integers, GL, Sp, GF, Matrix, QQ, prime_range, factor
from lmfdb.number_fields.web_number_field import formatfield
from lmfdb.utils import WebObj, web_latex, display_knowl, web_latex_factored_integer
from lmfdb import db
from lmfdb.genus2_curves.main import url_for_curve_label as url_for_g2c_label
from lmfdb.classical_modular_forms.main import url_for_label as url_for_mf_label
from lmfdb.number_fields.number_field import field_pretty

def _codomain(algebraic_group, dimension, base_ring_order, base_ring_is_field):
    if base_ring_is_field:
        return fr"\{algebraic_group}_{dimension}(\F_{base_ring_order})"
    else:
        return fr"\{algebraic_group}_{dimension}(\Z/\Z_{base_ring_order})"

def codomain(algebraic_group, dimension, base_ring_order, base_ring_is_field):
    return "$" + _codomain(algebraic_group, dimension, base_ring_order, base_ring_is_field) + "$"

def image_pretty(image_label, is_surjective, algebraic_group, dimension, base_ring_order, base_ring_is_field, codomain=True):
    s = _codomain(algebraic_group, dimension, base_ring_order, base_ring_is_field)
    if is_surjective:
        return "$" + s + "$"
    t = t = display_knowl('gl2.subgroup_data', title=image_label, kwargs={'label':image_label}) if dimension == 2 else image_label
    return t + r" $< " + s + "$" if codomain else t

def rep_pretty(algebraic_group, dimension, base_ring_order, base_ring_is_field):
    return r"$\rho\colon\Gal_\Q\to" + _codomain(algebraic_group, dimension, base_ring_order, base_ring_is_field) + "$"

def get_bread(tail=[]):
    base = [(r"Mod-$\ell$ Galois representations", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def my_field_pretty(nflabel):
    # We use Q(i) to make coordinates shorter
    if nflabel == "2.0.4.1":
        return r"\(\Q(i)\)"
    return field_pretty(nflabel)

def showexp(c, wrap=True):
    if c == 1:
        return ""
    elif wrap:
        return f"$^{{{c}}}$"
    else:
        return f"^{{{c}}}"

def modlgal_link(label):
    return '<a href="%s">%s</a>'%(url_for(".by_label",label=label),label)

def bool_string(b):
    return "yes" if b else "no"

class WebModLGalRep(WebObj):
    table = db.modlgal_reps

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
            ("Dimension", str(self.dimension)),
            ("Codomain", str(self.codomain)),
            ("Conductor", str(self.conductor)),
            ("Top slope", self.top_slope_rational),
            ("Image index", str(self.image_index)),
            ("Image order", str(self.image_order)),
        ]
        return props

    @lazy_attribute
    def friends(self):
        from lmfdb.modl_galois_representations.main import url_for_modlgal_label
        friends = []
        if not hasattr(self, "related_objects"):
            self.related_objects = []
        for r in self.related_objects:
            if r[0] == "Dirichlet":
                c = r[1].split(".")
                friends.append(("Dirichlet character " + r[1], url_for("characters.render_Dirichletwebpage",modulus=c[0],number=c[1])))
            elif r[0] == "ECQ":
                friends.append(("Elliptic curve " + r[1], url_for("ec.by_ec_label", label=r[1])))
            elif r[0] == "MF":
                friends.append(("Modular form " + r[1], url_for_mf_label(r[1])))
            elif r[0] == "G2C":
                friends.append(("Genus 2 curve " + r[1], url_for_g2c_label(r[1])))
        if self.dimension > 1 and hasattr(self, "determinant_label"):
            friends.append(("Determinant " + self.determinant_label, url_for_modlgal_label(label=self.determinant_label)))
        return friends

    @lazy_attribute
    def bread(self):
        tail = []
        A = ["base_ring_characteristic", "dimension", "conductor"]
        D = {}
        for a in A:
            D[a] = getattr(self, a)
            tail.append(
                (str(D[a]), url_for(".index_Q", **D))
            )
        tail.append((self.label, " "))
        return get_bread(tail)

    @lazy_attribute
    def title(self):
        return f"Mod-{self.base_ring_characteristic} Galois representation {self.label}"

    @lazy_attribute
    def factored_conductor(self):
        return web_latex_factored_integer(self.conductor)

    @lazy_attribute
    def codomain(self):
        return codomain(self.algebraic_group, self.dimension, self.base_ring_order, self.base_ring_is_field)

    @lazy_attribute
    def image_pretty(self):
        return image_pretty(self.image_label, self.is_surjective, self.algebraic_group, self.dimension, self.base_ring_order, self.base_ring_is_field, codomain=False)

    @lazy_attribute
    def rep_pretty(self):
        return rep_pretty(self.algebraic_group, self.dimension, self.base_ring_order, self.base_ring_is_field)

    @lazy_attribute
    def kernel_sibling(self):
        return formatfield(self.kernel_polynomial)

    @lazy_attribute
    def projective_kernel_sibling(self):
        return formatfield(self.projective_kernel_polynomial)

    @lazy_attribute
    def frobenius_generators(self):
        if not self.generating_primes:
            return None
        return ",".join([r"\mathrm{Frob}_{%s}"%(p) for p in self.generating_primes])

    @lazy_attribute
    def frobenius_matrices_pretty(self):
        L = []
        F = GF(self.base_ring_order) if self.base_ring_is_field else Integers(self.base_ring_order)
        R = GL(self.dimension,F) if self.algebraic_group == "GL" else Sp(self.dimension,F)
        n = self.dimension
        ps = [p for p in prime_range(100) if (self.conductor*self.base_ring_characteristic) % p != 0]
        frobs = self.frobenius_matrices
        try:
            for i in range(len(ps)):
                m = Matrix(F,n,frobs[i])
                M = R(frobs[i])
                if self.generating_primes and ps[i] in self.generating_primes:
                    L.append([r"\mathbf{%s}"%(ps[i]),m.trace(),M.order(),web_latex(factor(m.charpoly())),web_latex(m)])
                else:
                    L.append([ps[i],m.trace(),M.order(),web_latex(factor(m.charpoly())),web_latex(m)])
        except ValueError:
            print(f"Error occurred while attempting to parse frobenius_matrices for {self.label}")
            print(self.frobenius_matrices)
            return []
        return L

    @lazy_attribute
    def dual_algebra_pretty(self):
        A = self.dual_pair_of_algebras
        if not A:
            return None
        n = sum([len(a)-1 for a in A[0]])
        data = { "A": r" $\times$ ".join([formatfield(f) for f in A[0]]),
                 "B": r" $\times$ ".join([formatfield(f) for f in A[1]]),
                 "Phi": r"\frac{1}{%s} "%(str(A[2][0])) + web_latex(Matrix(QQ,n,A[2][1]),enclose=False)
               }
        return data

    @lazy_attribute
    def downloads(self):
        self.downloads = [
            (
                "Code to Magma",
                url_for(".modlgal_magma_download", label=self.label),
            ),
            (
                "Code to SageMath",
                url_for(".modlgal_sage_download", label=self.label),
            ),
            (
                "All data to text",
                url_for(".modlgal_text_download", label=self.label),
            ),
            (
                'Underlying data',
                url_for(".modlgal_data", label=self.label),
            )

        ]
        #self.downloads.append(("Underlying data", url_for(".belyi_data", label=self.label)))
        return self.downloads
