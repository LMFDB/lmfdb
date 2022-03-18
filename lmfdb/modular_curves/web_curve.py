# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute, prod, euler_phi
from lmfdb.utils import WebObj, integer_prime_divisors
from lmfdb import db
from lmfdb.classical_modular_forms.main import url_for_label as url_for_mf_label

def get_bread(tail=[]):
    base = [("Modular curves", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def showexp(c):
    if c == 1:
        return ""
    else:
        return f"$^{{{c}}}$"

class WebModCurve(WebObj):
    table = db.gps_gl2zhat_test

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
            ("Level", str(self.level)),
            ("Index", str(self.index)),
            ("Genus", str(self.genus)),
        ]
        if self.rank != -1:
            props.append(("Rank", str(self.rank)))
        props.extend([("Cusps", str(self.cusps)),
                      (r"$\Q$-cusps", str(self.rational_cusps))])
        return props

    @lazy_attribute
    def bread(self):
        tail = []
        A = ["level", "index", "genus"]
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
        #if self.name:
        #    return f"Modular curve {self.name}"
        #else:
        return f"Modular curve {self.label}"

    @lazy_attribute
    def formatted_dims(self):
        C = Counter(self.dims)
        return "$" + ",".join(f"{d}{showexp(c)}" for (d, c) in sorted(C.items())) + "$"

    @lazy_attribute
    def formatted_newforms(self):
        C = Counter(self.newforms)
        # Make sure that the Counter doesn't break the ordering
        return ",".join(f'<a href="{url_for_mf_label(label)}">{label}</a>{showexp(c)}' for (label, c) in C.items())

    @lazy_attribute
    def obstruction_primes(self):
        return ",".join(str(p) for p in self.obstructions if p != 0)

    def cyclic_isogeny_field_degree(self):
        return min(r[1] for r in self.isogeny_orbits if r[0] == self.level)

    def cyclic_torsion_field_degree(self):
        return min(r[1] for r in self.orbits if r[0] == self.level)

    def full_torsion_field_degree(self):
        N = self.level
        P = integer_prime_divisors(N)
        GL2size = euler_phi(N) * N * (N // prod(P))**2 * prod(p**2 - 1 for p in P)
        return GL2size // self.index
