#-*- coding: utf-8 -*-

from sage.all import euler_phi, lazy_attribute, point, line, polygon, frac, floor, lcm, cartesian_product, ZZ, QQ, PolynomialRing, OrderedPartitions, srange, prime_range, prime_pi, next_prime, previous_prime, gcd, text, Graphics
from lmfdb import db
from lmfdb.utils import encode_plot, unparse_range, totaler, proportioners
from lmfdb.galois_groups.transitive_group import knowl_cache, transitive_group_display_knowl
from lmfdb.local_fields import local_fields_page
from flask import url_for

from collections import defaultdict, Counter
import itertools
import re
FAMILY_RE = re.compile(r'\d+\.\d+\.\d+\.\d+[a-z]+(\d+\.\d+-\d+\.\d+\.\d+[a-z]+)?')

def str_to_QQlist(s):
    if s == "[]":
        return []
    return [QQ(x) for x in s[1:-1].split(", ")]

class pAdicSlopeFamily:
    def __init__(self, label=None, base=None, slopes=[], means=[], tilts=[], field_cache=None):
        data_cols = ["base", "tilts", "scaled_tilts", "types", "base_aut", "p", "f", "f0", "f_absolute", "e", "e0", "e_absolute", "n", "n0", "n_absolute", "c", "c0", "c_absolute", "field_count", "packet_count", "ambiguity", "mass_display", "mass_stored", "mass_found", "all_stored"]
        if label is not None:
            assert not base and not slopes and not means and not tilts
            data = db.lf_families.lookup(label)
            if data:
                self.__dict__.update(data)
                for col in ["visible", "slopes", "tilts", "means", "scaled_tilts", "types"]:
                    setattr(self, col, str_to_QQlist(getattr(self, col)))
                self.p, self.e = ZZ(self.p), ZZ(self.e)
                self.artin_slopes = self.visible
                base, tilts, p, w = self.base, self.tilts, self.p, self.w
            else:
                raise NotImplementedError
            self.label = label
        else:
            raise NotImplementedError
        #self.base = base
        # For now, these slopes are Serre-Swan slopes, not Artin-Fontaine slopes
        assert p.is_prime()
        self.pw = p**w
        _, self.etame = self.e.val_unit(p)
    @lazy_attribute
    def scaled_tilts(self):
        return [r / (self.etame * self.p**i) for (i, r) in enumerate(self.tilts, 1)]

    @lazy_attribute
    def dots(self):
        p, e, w = self.p, self.e, self.w
        # We include a large dot at the origin exactly when there is a tame part
        dots = [("d", 0, 0, self.etame > 1)]
        sigma = ZZ(1)
        # It's convenient to add 0 at the beginning; this transforms our indexing into 1-based and helps with cases below the first band
        means = [0] + self.means
        slopes = [0] + self.slopes
        types = [0] + self.types
        maxslope = slopes[-1]
        slopes.append(maxslope+1) # convenient since the last band is the final one in its sequence
        while True:
            j, i = sigma.quo_rem(self.e)
            height = j + i / e
            if height > maxslope:
                break
            sigma += 1
            if i == 0 or i.valuation(p) > w:
                index = 0
            else:
                index = w - i.valuation(p)
            if height < means[index]:
                # invisible Z-point
                continue
            if height in means:
                band = means.index(height)
                if types[band] != self.e0 and slopes[band] < slopes[band+1]:
                    # A-point: green square
                    dots.append(("a", i, j, True))
                    continue
            if height >= slopes[index]:
                # C-point: red diamond
                dots.append(("c", i, j, height in self.slopes))
            else:
                # B-point: blue circle
                dots.append(("b", i, j, True))
        return dots

    @lazy_attribute
    def link(self):
        from flask import url_for
        return f'<a href="{url_for(".family_page", label=self.label)}">{self.label}</a>'

    @lazy_attribute
    def picture(self):
        P = Graphics()
        # We want to draw a green horizontal line at each mean, a black at each slope (except when they overlap, in which case it should be dashed), and a grey rectangle between, with shading increased based on overlaps.
        if self.w > 0:
            maxslope = self.slopes[-1]
            # Draw boundaries
            P += line([(0, maxslope), (0,0), (self.e, 0), (self.e, maxslope)], rgbcolor=(0.2, 0.2, 0.2), zorder=-1, thickness=1)

            slopeset = set(self.slopes)
            meanset = set(self.means)
            ticks = sorted(slopeset.union(meanset))
            rectangles = {(a,b): 0 for (a,b) in zip(ticks[:-1], ticks[1:])}
            rkeys = sorted(rectangles)
            hscale = self.e / 12
            #for a,b in rkeys:
                #
            mindiff = min((b-a) for (a,b) in rkeys)
            aspect = max(0.6 * (self.e + 3*hscale) / (1 + maxslope), self.e/(32*mindiff))
            ticklook = {a: a for a in ticks} # adjust values below when too close
            if mindiff < 0.1:
                pairdiff = min(max(c-b, b-a) for (a,b,c) in zip(ticks[:-2], ticks[1:-1], ticks[2:]))
                if pairdiff >= 0.25:
                    # We can just spread out pairs of ticks from their center
                    for a,b in rkeys:
                        if b - a < 0.1:
                            ticklook[a] = a - 1/30
                            ticklook[b] = b + 1/30
                    # We decreased
                    mindiff += 1/10
                else:
                    pass # Should do something here
                    # We move if there's enough space
                    #for i, (a,b,c) in enumerate(zip(ticks[:-2], ticks[1:-1], ticks[2:])):
                    #    la, lb, lc = ticklook[a], ticklook[b], ticklook[c]
                    #    if lb - la < 0.1:
                    #        # Want to adjust a downward
                    #        if la > a or (i > 0 and a - ticklook[ticks[i-1]] < 0.15:
                    #            # We've already moved a up, or it's pretty close to the tick below
                    #            # So we set la to the average of the term below and the term above.
                    #            ticklook[a] = (ticklook[ticks[i-1]] + b) / 2
                    #        elif a - ticks[-1] >= 0.15:
                    #            # We can move it down, but we need to be careful not to move it down too much
                    #            ticklook[a] = (
                mindiff = min((ticklook[b]-ticklook[a]) for (a,b) in rkeys)
                aspect = max(0.6 * (self.e + 3*hscale) / (1 + maxslope), self.e/(32*mindiff))
            # We determine the colors of the bands, then print them
            for m, s in zip(self.means, self.slopes):
                # Don't worry about doing this in any fancy way, since there won't be many rectangles in practice
                for (a,b) in rkeys:
                    if a >= m and b <= s:
                        rectangles[a,b] += 1
                    elif a >= s:
                        break
            for (a,b), cnt in rectangles.items():
                col = 1 - 0.1*cnt
                P += polygon([(0, a), (self.e, a), (self.e, b), (0, b)], fill=True, rgbcolor=(col,col,col), zorder=-4)
            # Horizontal green and black lines
            for y in ticks:
                if y in slopeset and y in meanset:
                    # green and black dashed line
                    ndashes = 11
                    scale = self.e / ndashes
                    for x in range(1, ndashes, 2):
                        P += line([(x*scale, y), ((x+1)*scale, y)], color="green", zorder=-2, thickness=2)
                    color = "black" # Behind the green dashes
                elif y in slopeset:
                    color = "black"
                else:
                    color = "green"
                # Mean and slope labels
                P += line([(0, y), (self.e, y)], color=color, zorder=-3, thickness=2)
                P += text(f"${float(y):.3f}$", (-hscale, ticklook[y]), color=color)
                P += text(f"${self.e*y}$", (-2*hscale, ticklook[y]), color=color)
            # The spiral
            for y in srange(maxslope):
                y1 = min(y+1, maxslope)
                x1 = (y1 - y) * self.e
                P += line([(0, y), (x1, y1)], color="black", zorder=-1, thickness=1)
            # x-axis Labels
            vscale = maxslope / 100
            for u in range(self.e+1):
                P += text(f"${u}$", (u, -vscale), vertical_alignment="top", color="black", zorder=-2)
                P += text(f"${u}$", (u, maxslope+vscale), vertical_alignment="bottom", color="black", zorder=-2)
            # Right hand lines for arithmetic bands
            for (m, s, t) in zip(self.means, self.slopes, self.types):
                if t == self.e0:
                    P += line([(self.e, m), (self.e, s)], color="black", zorder=-2, thickness=2)
            # Tilt labels
            seen = set()
            for i, (s, t) in enumerate(zip(self.slopes, self.tilts)):
                if s not in seen:
                    P += text(f"${t}$", (self.e + hscale/2, s), color="blue")
                seen.add(s)
        else:
            aspect = 1
        P.set_aspect_ratio(aspect)
        colmark = {"a": ("green", "s"), "b": ("blue", "o"), "c": ("red", "D"), "d": ("olive", "p")}
        for code, i, j, big in self.dots:
            # (i,j) gives the term for pi^j * x^i.  We transition to the coordinates for the picture
            v = j + i / self.e
            size = 20 if big else 10
            color, marker = colmark[code]
            mcolor = color
            if not big:
                color = "white"
            P += point((i, v), markeredgecolor=mcolor, color=color, size=size, marker=marker, zorder=1)
        P.axes(False)
        return encode_plot(P, pad=0, pad_inches=0, bbox_inches="tight", dpi=300)

    @lazy_attribute
    def ramification_polygon_plot(self):
        from .main import plot_ramification_polygon
        p = self.p
        L = [(self.n, 0)]
        if self.f != 1:
            L.append((self.e, 0))
        tame_shift = self.e - self.pw
        if tame_shift:
            L.append((self.pw, tame_shift))
        cur = (self.pw, tame_shift)
        for r, nextr in zip(self.tilts, self.tilts[1:] + [None]):
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
        pts = [(c, i, j) for (c, i, j, big) in self.dots if big]
        names = [f"{c}{self.e*j+i}" for (c, i, j) in pts]
        if gcd(p**f - 1, self.etame) > 1:
            names.append("d")
        if self.e0 > 1:
            names.append("pi")
        R = PolynomialRing(ZZ, names)
        S = PolynomialRing(R, "x")
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
            poly += R.gen(i) * pi**(v+1) * x**u
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
    def oldbase(self):
        # Temporary until we update subfield to use new labels
        return db.lf_fields.lucky({"new_label":self.base}, "label")

    @lazy_attribute
    def fields(self):
        fields = list(db.lf_fields.search(
            {"family": self.label_absolute},
            ["label", "coeffs", "galT", "galois_label", "galois_degree", "slopes", "ind_of_insep", "associated_inertia", "t", "u", "aut", "hidden", "subfield", "jump_set"]))
        if self.n0 > 1:
            fields = [rec for rec in fields if self.oldbase in rec["subfield"]]
        glabels = list(set(rec["galois_label"] for rec in fields if rec.get("galois_label")))
        if glabels:
            cache = knowl_cache(glabels)
        else:
            cache = {}
        return fields, cache

    @lazy_attribute
    def all_hidden_data_available(self):
        if self.mass_found < 1:
            return False
        for rec in self.fields:
            if not all(rec.get(col) for col in ["galT", "galois_label"]):
                return False
        return True

    @lazy_attribute
    def galois_groups(self):
        fields, cache = self.fields
        opts = sorted(Counter((rec["galT"], rec["galois_label"]) for rec in fields if "galT" in rec and "galois_label" in rec).items())
        if not opts:
            return "No Galois groups in this family have been computed"
        def show_gal(label, cnt):
            kwl = transitive_group_display_knowl(label, cache=cache)
            if len(opts) == 1:
                return kwl
            url = url_for(".family_page", label=self.label, gal=label)
            return f'{kwl} (<a href="{url}">show {cnt}</a>)'
        s = ", ".join(show_gal(label, cnt) for ((t, label), cnt) in opts)
        if not self.all_hidden_data_available:
            s += " (incomplete)"
        return s

    @lazy_attribute
    def hidden_slopes(self):
        # TODO: Update this to use hidden column from lf_fields
        fields, cache = self.fields
        full_slopes = [Counter(QQ(s) for s in rec["slopes"][1:-1].split(",")) if rec["slopes"] != "[]" else Counter() for rec in fields if "slopes" in rec]
        visible = Counter(self.artin_slopes)
        hidden = sorted(Counter(tuple(sorted((full - visible).elements())) for full in full_slopes).items())
        if not hidden:
            return "No hidden slopes in this family have been computed"
        def show_hidden(x, cnt):
            disp = str(x).replace(" ","")
            full = str(sorted((Counter(x) + visible).elements())).replace(" ","")
            if len(hidden) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, slopes=full, slopes_quantifier="exactly")
            return f'${disp}$ (<a href="{url}">show {cnt}</a>)'
        s = ", ".join(show_hidden(list(x), cnt) for (x,cnt) in hidden)
        if not self.all_hidden_data_available:
            s += " (incomplete)"
        return s

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
    def jump_set(self):
        fields, cache = self.fields
        js = sorted(Counter(tuple(rec["jump_set"]) for rec in fields if "jump_set" in rec).items())
        def show_js(x, cnt):
            disp = str(x).replace(" ","")
            if len(js) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, jump_set=disp)
            return f'${disp}$ (<a href="{url}">show {cnt}</a>)'
        s = ", ".join(show_js(list(x), cnt) for (x,cnt) in js)
        if any("jump_set" not in rec for rec in fields):
            s += " (incomplete)"
        return s

    @lazy_attribute
    def gal_slope_tables(self):
        from .main import LFStats
        stats = LFStats()
        fields, cache = self.fields
        gps = defaultdict(set)
        slopes = defaultdict(set)
        for rec in fields:
            if "galois_degree" in rec and "galois_label" in rec and "slopes" in rec:
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
