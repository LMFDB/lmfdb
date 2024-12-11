#-*- coding: utf-8 -*-

from sage.all import euler_phi, lazy_attribute, point, line, polygon, frac, floor, lcm, cartesian_product, ZZ, QQ, PolynomialRing, OrderedPartitions, srange, prime_range, prime_pi, next_prime, previous_prime, gcd
from lmfdb import db
from lmfdb.utils import encode_plot, unparse_range, totaler, proportioners
from lmfdb.galois_groups.transitive_group import knowl_cache, transitive_group_display_knowl
from lmfdb.local_fields import local_fields_page
from flask import url_for

from collections import defaultdict, Counter
import itertools
import re
FAMILY_RE = re.compile(r'\d+\.\d+\.\d+\.\d+[a-z]+(\d+\.\d+-\d+\.\d+[a-z]+)?')

def str_to_QQlist(s):
    if s == "[]":
        return []
    return [QQ(x) for x in s[1:-1].split(", ")]

class pAdicSlopeFamily:
    def __init__(self, label=None, base=None, slopes=[], heights=[], rams=[], field_cache=None):
        data_cols = ["base", "rams", "base_aut", "p", "f", "f0", "f_absolute", "e", "e0", "e_absolute", "n", "n0", "n_absolute", "c", "c0", "c_absolute", "field_count", "packet_count", "ambiguity", "mass_display", "mass_stored", "mass_missing", "all_stored"]
        if label is not None:
            assert not base and not slopes and not heights and not rams
            data = db.lf_families.lookup(label)
            if data:
                self.__dict__.update(data)
                for col in ["visible", "slopes", "rams", "heights", "scaled_rams", "scaled_heights"]:
                    setattr(self, col, str_to_QQlist(getattr(self, col)))
                self.p, self.e = ZZ(self.p), ZZ(self.e)
                self.artin_slopes = self.visible
                base, rams, p, w = self.base, self.rams, self.p, self.w
            else:
                raise NotImplementedError
            self.label = label
        else:
            raise NotImplementedError
        self.base = base
        # For now, these slopes are Serre-Swan slopes, not Artin-Fontaine slopes
        assert p.is_prime()
        self.pw = p**w
        _, self.etame = self.e.val_unit(p)
        # We support tamely ramified fields by specifying a tame base and empty slopes/rams/heights
        # slopes/rams -> heights -> rams/slopes
        #if rams:
        #    heights = [sum(p**(k-j) * rams[j] for j in range(k+1)) for k in range(w)]
        #if slopes:
        #    heights = [] # have to reset since lists created in arguments persist across function calls
        #    h = 0
        #    phipk = p - 1
        #    for s in slopes:
        #        h += phipk * s
        #        heights.append(h)
        #        phipk *= p
        #if w and not rams:
        #    rams = [heights[0]] + [heights[k] - p*heights[k-1] for k in range(1,w)]
        #if w and not slopes:
        #    slopes = [heights[0] / (p-1)] + [(heights[k] - heights[k-1]) / euler_phi(p**(k+1)) for k in range(1,w)]
        #self.slopes = slopes
        #data = db.lf_families.lookup(self.label, data_cols)
        #if data:
        #    for col in data_cols:
        #        setattr(self, col, data[col])
        #else:
        #    self.field_count = self.packet_count = self.poly_count = 0
        #    if "." in self.short_base:
        #        data = db.lf_fields.lookup(self.base, ["aut", "f", "e", "n"])
        #        self.base_aut = data["aut"]
        #        self.f = data["f"]
        #        self.e0 = data["e"]
        #        self.e = self.pw * self.e0
        #        self.n0 = data["n"]
        #        self.n = self.f * self.e
        #    else:
        #        self.base_aut = self.f = self.e0 = self.n0 = 1
        #        self.n = self.e = self.pw
        #self.visible = self.artin_slopes = [(s + 1) / self.e0 for s in slopes]
        #self.heights = heights
        #self.rams = rams

    @lazy_attribute
    def scaled_heights(self):
        return [h / (self.etame * self.p**i) for (i, h) in enumerate(self.heights, 1)]

    @lazy_attribute
    def scaled_rams(self):
        return [r / (self.etame * self.p**i) for (i, r) in enumerate(self.rams, 1)]

    @lazy_attribute
    def bands(self):
        return [((0, 1+h), (self.e, h), (0, 1+s), (self.e, s)) for (h, s) in zip(self.scaled_heights, self.slopes)]

    @lazy_attribute
    def black(self):
        return [(0, 1), (self.e, 0)]

    @lazy_attribute
    def virtual_green(self):
        p, e, w = self.p, self.e, self.w
        last_slope = {}
        for i, s in enumerate(self.slopes, 1):
            last_slope[s] = i
        ans = []
        for i, (h, s) in enumerate(zip(self.scaled_heights, self.slopes), 1):
            u = e*frac(h)
            v = 1 + floor(h)
            if last_slope[s] == i:
                if (e*frac(h)).valuation(p) == w - i:
                    code = 1
                else:
                    code = 0
            else:
                code = -1
            ans.append((u, v, code))
        return ans

    @lazy_attribute
    def green(self):
        return [(u, v, bool(code)) for (u, v, code) in self.virtual_green if code >= 0]

    @lazy_attribute
    def solid_green(self):
        return [(u, v) for (u, v, solid) in self.green if solid]

    def _set_redblue(self):
        self.blue = []
        self.red = []
        p, e, w = self.p, self.e, self.w
        for i, (s, (u, v, code)) in enumerate(zip(self.slopes, self.virtual_green), 1):
            if u.denominator() == 1 and code == -1:
                self.blue.append((u, v, True))
            u = floor(u + 1)
            #print("Starting", i, s, u, v, code, e, w)
            while v <= 1 + s - u/e:
                #print("While", u, v, 1 + s - u/e, u.valuation(p), w-i)
                if u == e:
                    u = ZZ(0)
                    v += 1
                if v == 1 + s - u/e:
                    self.red.append((u, v, False))
                elif u.valuation(p) == (w - i):
                    self.blue.append((u, v, True))
                u += 1
        self.blue = sorted(set(self.blue))
        self.red = sorted(set(self.red))

    @lazy_attribute
    def blue(self):
        self._set_redblue()
        return self.blue

    @lazy_attribute
    def red(self):
        self._set_redblue()
        return self.red

    @lazy_attribute
    def link(self):
        from flask import url_for
        return f'<a href="{url_for(".family_page", label=self.label)}">{self.label}</a>'

    @lazy_attribute
    def picture(self):
        P = point(self.black, color="black", size=20)
        for A, B, C, D in self.bands:
            P += polygon([A,B,D,C], fill=True, rgbcolor=(0.9, 0.9, 0.9), zorder=-3)
            P += line([A, B], color="black", zorder=-1)
            P += line([C, D], color="black", zorder=-1)
        for (A0, B0, C0, D0), (A1, B1, C1, D1) in zip(self.bands[:-1], self.bands[1:]):
            if A1 < C0:
                P += polygon([A1, B1, D0, C0], fill=True, rgbcolor=(0.8, 0.8, 0.8), zorder=-2)
        for color, marker in [("green", "s"), ("red", "D"), ("blue", "o")]:
            pts = getattr(self, color)
            for (u, v, solid) in pts:
                if solid:
                    P += point((u, v), markeredgecolor=color, color=color, size=20, marker=marker, zorder=1)
                else:
                    P += point((u, v), markeredgecolor=color, color="white", size=20, marker=marker, zorder=1)
        if len(self.visible) > 0:
            aspect = 0.75 * self.e / (1 + self.slopes[-1])
        else:
            aspect = 1
        P.set_aspect_ratio(aspect)
        #P._set_extra_kwds(dict(xmin=0, xmax=self.e, ymin=0, ymax=self.slopes[-1] + 1, ticks_integer=True))
        #return P
        return encode_plot(P, pad=0, pad_inches=0, bbox_inches="tight")

    @lazy_attribute
    def ramification_polygon_plot(self):
        from .main import plot_ramification_polygon
        p = self.p
        L = [(self.n, 0)]
        if self.f != 1:
            L.append((self.e, 0))
        #L = [(self.e, 0)]
        tame_shift = self.e - self.pw
        if tame_shift:
            L.append((self.pw, tame_shift))
        cur = (self.pw, tame_shift)
        for r, nextr in zip(self.rams, self.rams[1:] + [None]):
            x = cur[0] // p
            y = cur[1] + x * (p - 1) * (r + 1)
            cur = (x, y)
            if r != nextr:
                L.append(cur)
        L.reverse()
        return plot_ramification_polygon(L, p)

    @lazy_attribute
    def polynomial(self):
        p, f = self.p, self.f
        pts = ([("a", u, v) for (u, v) in self.solid_green] +
               [("b", u, v) for (u, v, solid) in self.blue] +
               [("c", u, v) for (u, v, solid) in self.red])
        names = [f"{c}{self.e*(v-1)+u}" for (c, u, v) in pts]
        if gcd(p**f - 1, self.etame) > 1:
            names.append("d")
        if self.e0 > 1:
            names.append("pi")
        R = PolynomialRing(ZZ, names)
        if self.f == 1:
            S = PolynomialRing(R, "x")
        else:
            S = PolynomialRing(R, "nu")
        if self.e == 1:
            return S.gen()
        if "d" in names:
            d = R.gen(names.index("d"))
        else:
            d = 1
        x = S.gen()
        if self.e0 > 1:
            pi = R.gens()[-1]
        else:
            pi = p
        poly = x**self.e + d*pi
        for i, (c, u, v) in enumerate(pts):
            poly += R.gen(i) * pi**v * x**u
        return poly

    @lazy_attribute
    def gamma(self):
        if self.f_absolute == 1:
            return len(self.red)
        e = self.e
        gamma = 0
        for (u, v, _) in self.red:
            s = v + u/e - 1
            cnt = self.slopes.count(s)
            gamma += gcd(cnt, self.f_absolute)
        return gamma

    @lazy_attribute
    def base_link(self):
        from .main import pretty_link
        return pretty_link(self.base, self.p, self.n0, self.rf0)

    def __iter__(self):
        # TODO: This needs to be fixed when base != Qp
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
        fields = list(db.lf_fields.search(
            {"family": self.label},
            ["label", "coeffs", "galT", "galois_label", "galois_degree", "slopes", "ind_of_insep", "associated_inertia", "t", "u", "aut", "hidden"]))
        cache = knowl_cache([rec["galois_label"] for rec in fields])
        return fields, cache

    @lazy_attribute
    def galois_groups(self):
        fields, cache = self.fields
        opts = sorted(Counter((rec["galT"], rec["galois_label"]) for rec in fields).items())
        def show_gal(label, cnt):
            kwl = transitive_group_display_knowl(label, cache=cache)
            if len(opts) == 1:
                return kwl
            url = url_for(".family_page", label=self.label, gal=label)
            return f'{kwl} (<a href="{url}">show {cnt}</a>)'
        return ", ".join(show_gal(label, cnt) for ((t, label), cnt) in opts)

    @lazy_attribute
    def hidden_slopes(self):
        # TODO: Update this to use hidden column from lf_fields
        fields, cache = self.fields
        full_slopes = [Counter(QQ(s) for s in rec["slopes"][1:-1].split(",")) if rec["slopes"] != "[]" else Counter() for rec in fields]
        visible = Counter(self.artin_slopes)
        hidden = sorted(Counter(tuple(sorted((full - visible).elements())) for full in full_slopes).items())
        def show_hidden(x, cnt):
            disp = str(x).replace(" ","")
            full = str(sorted((Counter(x) + visible).elements())).replace(" ","")
            if len(hidden) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, slopes=full, slopes_quantifier="exactly")
            return f'${disp}$ (<a href="{url}">show {cnt}</a>)'
        return ", ".join(show_hidden(list(x), cnt) for (x,cnt) in hidden)

    @lazy_attribute
    def indices_of_insep(self):
        fields, cache = self.fields
        ii = sorted(Counter(tuple(rec["ind_of_insep"]) for rec in fields).items())
        def show_ii(x, cnt):
            disp = str(x).replace(" ","")
            if len(ii) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, ind_of_insep=disp, insep_quantifier="exactly")
            return f'${disp}$ (<a href="{url}">show {cnt}</a>)'
        return ", ".join(show_ii(list(x), cnt) for (x,cnt) in ii)

    @lazy_attribute
    def associated_inertia(self):
        fields, cache = self.fields
        ai = sorted(Counter(tuple(rec["associated_inertia"]) for rec in fields).items())
        def show_ai(x, cnt):
            disp = str(x).replace(" ","")
            if len(ai) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, associated_inertia=disp)
            return f'${disp}$ (<a href="{url}">show {cnt}</a>)'
        return ", ".join(show_ai(list(x), cnt) for (x,cnt) in ai)

    @lazy_attribute
    def gal_slope_tables(self):
        from .main import LFStats
        stats = LFStats()
        fields, cache = self.fields
        gps = defaultdict(set)
        slopes = defaultdict(set)
        for rec in fields:
            gps[rec["galois_degree"]].add(rec["galois_label"])
            slopes[rec["galois_degree"]].add(rec["slopes"])
        dyns = []
        def add_grid(Ns, rowcount, colcount):
            if len(Ns) == 1:
                Nconstraint = list(Ns)[0]
            else:
                Nconstraint = {"$gte": min(Ns), "$lte": max(Ns)}
            constraint = {
                'family': self.label,
                'galois_degree': Nconstraint,
            }
            attr = {
                'cols': ['slopes', 'galois_label'],
                'constraint': constraint,
                'totaler': totaler(row_counts=(colcount > 1), col_counts=(rowcount > 1), row_proportions=False, col_proportions=False)
            }
            dyns.append(stats.prep(attr))

        cur_rows = set()
        cur_cols = set()
        max_rows = 8
        max_cols = 8
        curN = set()
        Ns = sorted(gps)
        for N in Ns:
            rowcount = len(cur_rows)
            colcount = len(cur_cols)
            cur_rows = cur_rows.union(slopes[N])
            cur_cols = cur_cols.union(gps[N])
            if curN and (len(cur_cols) > max_cols or len(cur_rows) > max_rows):
                add_grid(curN, rowcount, colcount)
                cur_rows = set()
                cur_cols = set()
                curN = set()
            if N == Ns[-1]:
                add_grid(curN.union(set([N])), len(cur_rows), len(cur_cols))
            curN.add(N)
        return dyns
