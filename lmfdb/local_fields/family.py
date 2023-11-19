#-*- coding: utf-8 -*-

from sage.all import euler_phi, lazy_attribute, point, line, frac, floor, lcm, cartesian_product, ZZ, PolynomialRing, OrderedPartitions, srange
from lmfdb import db
from lmfdb.utils import encode_plot
from lmfdb.galois_groups.transitive_group import knowl_cache, transitive_group_display_knowl
from lmfdb.local_fields import local_fields_page

import re
FAMILY_RE = re.compile(r'(\d+)\.(\d+)\.(\d+(?:_\d+)*)')

class pAdicSlopeFamily:
    def __init__(self, p, u=1, t=1, slopes=[], heights=[], rams=[], count_cache=None):
        # For now, these slopes are Serre-Swan slopes, not Artin-Fontaine slopes
        assert u==1 and t==1
        assert p.is_prime()
        w = max(len(L) for L in [slopes, heights, rams])
        # For now, we don't support tamely ramified fields; if this changes, also need to update the "if not rams" and "if not slopes" below
        assert w > 0
        assert u == t == 1 # various things below need to change to support non-wild extensions
        # slopes/rams -> heights -> rams/slopes
        if rams:
            heights = [sum(p**(k-j) * rams[j] for j in range(k+1)) for k in range(w)]
        if slopes:
            heights = [] # have to reset since lists created in arguments persist across function calls
            h = 0
            phipk = p - 1
            for s in slopes:
                h += phipk * s
                heights.append(h)
                phipk *= p
        if not rams:
            rams = [heights[0]] + [heights[k] - p*heights[k-1] for k in range(1,w)]
        if not slopes:
            slopes = [heights[0] / (p-1)] + [(heights[k] - heights[k-1]) / euler_phi(p**(k+1)) for k in range(1,w)]
        self.slopes = slopes
        self.artin_slopes = [s + 1 for s in slopes]
        self.heights = heights
        scaled_heights = [h / p**i for (i, h) in enumerate(heights, 1)]
        self.rams = rams
        scaled_rams = [r / p for r in rams]
        self.n = self.e = n = p**w
        self.p = p
        self.f = self.u = u
        self.t = t
        self.c = heights[-1] + n - 1
        self.bands = [((0, 1+h), (n, h), (0, 1+s), (n, s)) for (h, s) in zip(scaled_heights, slopes)]
        self.black = [(0, 1), (n, 0)]
        self.green = [(n*frac(h), 1 + floor(h), (n*frac(h)).valuation(p) == (w - i)) for (i, h) in enumerate(scaled_heights, 1)]
        self.blue = []
        self.red = []
        for i, (s, (u, v, solid)) in enumerate(zip(slopes, self.green), 1):
            u += 1
            while v <= 1 + s - u/n:
                if u == n:
                    u = ZZ(0)
                    v += 1
                if v == 1 + s - u/n:
                    self.red.append((u, v, False))
                elif u.valuation(p) == (w - i):
                    self.blue.append((u, v, True))
                u += 1
        self.count_cache = count_cache

    @lazy_attribute
    def label(self):
        den = lcm(s.denominator() for s in self.slopes)
        nums = "_".join(str(den*n) for n in self.slopes)
        return f"{self.p}.{den}.{nums}"

    @lazy_attribute
    def link(self):
        from flask import url_for
        return f'<a href="{url_for(".family_page", label=self.label)}">{self.label}</a>'

    @lazy_attribute
    def picture(self):
        P = point(self.black, color="black", size=20)
        for (A, B, C, D) in self.bands:
            P += line([A, B], color="black")
            P += line([C, D], color="black")
        for color in ["green", "red", "blue"]:
            pts = getattr(self, color)
            for (u, v, solid) in pts:
                P += point((u, v), color=color, size=20)
                if not solid:
                    P += point((u, v), color="white", size=15)
        P.set_aspect_ratio(1)
        #P._set_extra_kwds(dict(xmin=0, xmax=self.n, ymin=0, ymax=self.slopes[-1] + 1, ticks_integer=True))
        #return P
        return encode_plot(P, pad=0, pad_inches=0, bbox_inches="tight")

    @lazy_attribute
    def polynomial(self):
        pts = ([("a", u, v) for (u, v, solid) in self.green] +
               [("b", u, v) for (u, v, solid) in self.blue] +
               [("c", u, v) for (u, v, solid) in self.red])
        names = [f"{c}{self.n*(v-1)+u}" for (c, u, v) in pts]
        R = PolynomialRing(ZZ, names)
        S = PolynomialRing(R, "x")
        x = S.gen()
        p = self.p
        poly = x**(self.n) + p
        for i, (c, u, v) in enumerate(pts):
            poly += R.gen(i) * p**v * x**u
        return poly

    @lazy_attribute
    def poly_count(self):
        p, alpha, beta, gamma = self.p, len(self.green), len(self.blue), len(self.red)
        # TODO: This needs to be updated if we ever allow f > 1
        return (p-1)**alpha * p**(beta + gamma)

    @lazy_attribute
    def base(self):
        return fr"\Q_{{{self.p}}}"

    def __iter__(self):
        generic = self.polynomial
        R = generic.base_ring()
        Zx = PolynomialRing(ZZ, "x")
        names = R.variable_names()
        p = self.p
        opts = {"a": [ZZ(a) for a in range(1, p)],
                "b": [ZZ(b) for b in range(p)],
                "c": [ZZ(c) for c in range(p)]}
        for vec in cartesian_product([opts[name[0]] for name in names]):
            yield Zx(generic.subs(**dict(zip(names, vec))))

    @lazy_attribute
    def fields(self):
        # TODO: update to allow for tame extensions
        from lmfdb.local_fields.main import show_slope_content, url_for_label
        Zx = PolynomialRing(ZZ, "x")
        recs = list(db.lf_fields.search(
            {"p": self.p, "visible": str(self.artin_slopes), "f": 1, "e": self.n},
            ["label", "coeffs", "galois_label", "slopes", "ind_of_insep", "associated_inertia", "t", "u"]))
        cache = knowl_cache([rec["galois_label"] for rec in recs])
        return [
            (f'<a href="{url_for_label(rec["label"])}">{rec["label"]}</a>',
             Zx(rec["coeffs"])._latex_(),
             transitive_group_display_knowl(rec["galois_label"], cache=cache),
             show_slope_content(rec["slopes"], rec["t"], rec["u"]),
             rec["ind_of_insep"],
             rec["associated_inertia"])
            for rec in recs]

    @lazy_attribute
    def field_count(self):
        if self.count_cache is not None:
            return self.count_cache[str(self.artin_slopes)]
        return db.lf_fields.count({"p": self.p, "visible": str(self.artin_slopes), "f": 1, "e": self.n})

    @classmethod
    def families(cls, p, w, count_cache=None):
        def R(e, rho):
            den = sum(p**i for i in range(rho))
            nums = [n for n in range(1, p*e*den) if n % p != 0]
            if rho == 1:
                nums.append(p*e*den)
            return [n / den for n in nums]
        for mvec in reversed(OrderedPartitions(w)):
            mtup = tuple(mvec)
            Mvec = [0]
            for m in mvec[:-1]:
                Mvec.append(Mvec[-1] + m)
            Rs = [R(p**M, m) for m, M in zip(mvec, Mvec)]
            for rvec in cartesian_product(Rs):
                if all(a < b for (a,b) in zip(rvec[:-1], rvec[1:])):
                    rmvec = []
                    for r, m in zip(rvec, mvec):
                        rmvec.extend([r] * m)
                    yield cls(p, rams=rmvec, count_cache=count_cache)

