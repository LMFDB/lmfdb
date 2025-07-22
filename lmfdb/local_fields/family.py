#-*- coding: utf-8 -*-

from sage.all import lazy_attribute, point, line, polygon, cartesian_product, ZZ, QQ, PolynomialRing, srange, gcd, text, Graphics, latex
from lmfdb import db
from lmfdb.utils import encode_plot, totaler
from lmfdb.galois_groups.transitive_group import knowl_cache, transitive_group_display_knowl
from flask import url_for

from collections import defaultdict, Counter
import re
FAMILY_RE = re.compile(r'\d+\.\d+\.\d+\.\d+[a-z]+(\d+\.\d+-\d+\.\d+\.\d+[a-z]+)?')

def str_to_QQlist(s):
    if s == "[]":
        return []
    return [QQ(x) for x in s[1:-1].split(", ")]

def latex_content(s):
    # Input should be a content string, [s1, s2, ..., sm]^t_u.  This converts the s_i (which might be rational numbers) to their latex form
    if s is None or s == "":
        return "not computed"
    elif s == []:
        return r'$[\ ]$'
    elif isinstance(s, list):
        return '$[' + ','.join(latex(x) for x in s) + ']$'
    else:
        return '$' + re.sub(r"(\d+)/(\d+)", r"\\frac{\1}{\2}", s).replace("[]", r"[\ ]") + '$'

def content_unformatter(s):
    # Convert latex back to plain string
    s = s.replace('$','')
    return re.sub(r"\\frac\{(\d+)\}\{(\d+)\}", r"\1/\2", s)

class pAdicSlopeFamily:
    def __init__(self, label=None, base=None, slopes=[], means=[], rams=[], field_cache=None):
        if label is not None:
            assert not base and not slopes and not means and not rams
            data = db.lf_families.lookup(label)
            if data:
                self.__dict__.update(data)
                for col in ["visible", "slopes", "rams", "means", "tiny_rams", "small_rams"]:
                    setattr(self, col, str_to_QQlist(getattr(self, col)))
                self.p, self.e = ZZ(self.p), ZZ(self.e)
                self.artin_slopes = self.visible
                base, rams, p, w = self.base, self.rams, self.p, self.w
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
    def scaled_rams(self):
        return [r / (self.etame * self.p**i) for (i, r) in enumerate(self.rams, 1)]

    @lazy_attribute
    def dots(self):
        p, e, f, w = self.p, self.e, self.f, self.w
        # We include a large dot at the origin exactly when there is a tame part
        dots = [("d", 0, 0, gcd(p**f - 1, self.etame) > 1)]
        sigma = ZZ(1)
        # It's convenient to add 0 at the beginning; this transforms our indexing into 1-based and helps with cases below the first band
        means = [0] + self.means
        slopes = [0] + self.slopes
        small_rams = [0] + self.small_rams
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
                if small_rams[band] != self.e0 and slopes[band] < slopes[band+1]:
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
        return f'<a href="{url_for(".family_page", label=self.label)}">{self.label}</a>'

    def _spread_ticks(self, ticks):
        ticklook0 = {a: a for a in ticks} # adjust values below when too close
        if len(ticks) <= 1:
            return ticklook0
        scale = ticks[-1] / 20
        cscale = 2*scale
        mindiff = min((b-a) for (a,b) in zip(ticks[:-1], ticks[1:]))
        if mindiff < scale:
            by_mindiff = {}
            for cscale in [2.0*scale, 1.5*scale, 1.0*scale, 0.8*scale, 0.6*scale, 0.4*scale, 0.2*scale]:
                # Try different scales for building clusters
                ticklook = dict(ticklook0)
                # Group into clusters
                clusters = [[ticks[0]]]
                for tick in ticks[1:]:
                    if tick - clusters[-1][-1] < cscale:
                        clusters[-1].append(tick)
                    else:
                        clusters.append([tick])
                # Spread from the center in each cluster, staying away from midpoint between cluster centers
                centers = [sum(C) / len(C) for C in clusters]
                if len(clusters) > 1:
                    maxspread = [(centers[1] - centers[0]) / 2]
                    for i in range(1, len(clusters) - 1):
                        maxspread.append(min(centers[i] - centers[i-1], centers[i+1] - centers[i]) / 2)
                    maxspread.append((centers[-1] - centers[-2]) / 2)
                    # Can't actually use the full maxspread, since that would lead to different clusters combining
                    maxspread = [m - cscale/4 for m in maxspread]
                    spread = [0 if len(C) == 1 else min(cscale/2, 2 * m / (len(C) - 1)) for (m,C) in zip(maxspread, clusters)]
                    for s, c, C in zip(spread, centers, clusters):
                        n = float(len(C))
                        for i, a in enumerate(C):
                            delta = (i - (n - 1)/2) * s
                            if delta > 0:
                                ticklook[a] = max(c + delta, a)
                            else:
                                ticklook[a] = min(c + delta, a)
                adjusted = sorted(ticklook.values())
                mindiff = min((b-a) for (a,b) in zip(adjusted[:-1], adjusted[1:]))
                by_mindiff[mindiff] = ticklook
            ticklook0 = by_mindiff[max(by_mindiff)]
        return ticklook0

    @lazy_attribute
    def spread_ticks(self):
        slopeset = set(self.slopes)
        meanset = set(self.means)
        ticks = sorted(slopeset.union(meanset))
        ticklook = self._spread_ticks(ticks)
        # We determine the overlaps of the bands
        rectangles = {(a,b): 0 for (a,b) in zip(ticks[:-1], ticks[1:])}
        rkeys = sorted(rectangles)
        for m, s in zip(self.means, self.slopes):
            # Don't worry about doing this in any fancy way, since there won't be many rectangles in practice
            for (a,b) in rkeys:
                if a >= m and b <= s:
                    rectangles[a,b] += 1
                elif a >= s:
                    break
        return ticklook, ticks, slopeset, meanset, rectangles

    @lazy_attribute
    def spread_rams(self):
        # Analogue of spread_ticks for x-axis of Herbrand plot
        return self._spread_ticks(sorted(set(self.rams)))

    @lazy_attribute
    def picture(self):
        P = Graphics()
        # We want to draw a green horizontal line at each mean, a black at each slope (except when they overlap, in which case it should be dashed), and a grey rectangle between, with shading increased based on overlaps.
        maxslope = self.slopes[-1]
        # Draw boundaries
        P += line([(0, maxslope), (0,0), (self.e, 0), (self.e, maxslope)], rgbcolor=(0.2, 0.2, 0.2), zorder=-1, thickness=1)
        ticklook, ticks, slopeset, meanset, rectangles = self.spread_ticks
        hscale = self.e / 18
        mindiff = min((ticklook[b]-ticklook[a]) for (a,b) in rectangles)
        aspect = min(8, max(0.6 * (self.e + 3*hscale) / (1 + maxslope), self.e/(32*mindiff)))

        # Print the bands
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
            P += text(f"${self.e*y}$", (-2*hscale, ticklook[y]), color=color, horizontal_alignment="right")
        # The spiral
        for y in srange(maxslope):
            y1 = min(y+1, maxslope)
            x1 = (y1 - y) * self.e
            P += line([(0, y), (x1, y1)], color="black", zorder=-1, thickness=1)
        # x-axis Labels
        vscale = maxslope / 100
        tickskip = (self.e+1)//24 + 1
        for u in range(0,self.e+1,tickskip):
            P += text(f"${u}$", (u, -vscale), vertical_alignment="top", color="black", zorder=-2)
            P += text(f"${u}$", (u, maxslope+vscale), vertical_alignment="bottom", color="black", zorder=-2)
        # Right hand lines for arithmetic bands
        for (m, s, t) in zip(self.means, self.slopes, self.small_rams):
            if t == self.e0:
                P += line([(self.e, m), (self.e, s)], color="black", zorder=-2, thickness=2)
        # Ram labels
        seen = set()
        for i, (s, t) in enumerate(zip(self.slopes, self.rams)):
            if s not in seen:
                P += text(f"${t}$", (self.e + hscale/2, s), color="blue", horizontal_alignment="left")
            seen.add(s)
        P.set_aspect_ratio(aspect)
        colmark = {"a": ("green", "s"), "b": ("blue", "o"), "c": ("red", "D"), "d": ("olive", "p")}
        for code, i, j, big in self.dots:
            # (i,j) gives the term for pi^j * x^i.  We transition to the coordinates for the picture
            v = j + i / self.e
            size = 20
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
        #L = [(self.n, self.n - self.e)]
        #if self.f != 1:
        #    L.append((self.e, 0))
        L = [(self.e, 0)]
        if self.e != self.pw:
            L.append((self.pw, 0))
        cur = (self.pw, 0)
        for r, nextr in zip(self.rams, self.rams[1:] + [None]):
            x = cur[0] // p
            y = cur[1] + x * (p - 1) * r
            cur = (x, y)
            if r != nextr:
                L.append(cur)
        L.reverse()
        return plot_ramification_polygon(L, p)

    @lazy_attribute
    def herbrand_function_plot(self):
        # Fix duplicates
        ticklook, ticks, slopeset, meanset, rectangles = self.spread_ticks
        ramlook = self.spread_rams
        mindiff = min((ticklook[b]-ticklook[a]) for (a,b) in rectangles)
        maxram, maxslope, maxmean = self.rams[-1], self.slopes[-1], self.means[-1]
        if maxram < 2:
            maxx = maxram * 1.5
        else:
            maxx = maxram + 1
        maxy = (maxslope - maxmean)/maxram * maxx + maxmean
        tickx = float(maxx/160)
        axistop = max(maxy, maxslope + 2*tickx)
        ticky = maxy / 100
        hscale = maxx / 18
        aspect = min(8, max(0.6 * (maxx + 3*hscale) / axistop, maxx/(32*mindiff)))
        #w = self.w
        #inds = [i for i in range(w) if i==w-1 or self.slopes[i] != self.slopes[i+1]]
        pts = list(zip(self.rams, self.slopes)) #[(self.rams[i],self.slopes[i]) for i in inds]
        P = line([(-2*tickx,0), (maxx,0)], color="black", thickness=1) + line([(0,0),(0,axistop)], color="black", thickness=1)
        P += line([(0,0)] + pts + [(maxx, maxy)], color="black", thickness=2)
        P += point(pts, color="black", size=20)
        # Mean and slope labels
        for y in ticks:
            if y in slopeset:
                color = "black"
            else:
                color = "green"
            P += text(f"${float(y):.3f}$", (-hscale, ticklook[y]), color=color)
            P += text(f"${self.e*y}$", (-2*hscale, ticklook[y]), color=color, horizontal_alignment="right")
        for m, r, s in zip(self.means, self.rams, self.slopes): #i in inds:
            #m, r, s = self.means[i], self.rams[i], self.slopes[i]
            P += line([(0, m), (r, s)], color="green", linestyle="--", thickness=1)
            P += text(f"${str(r)}$", (ramlook[r], -ticky), color="blue", vertical_alignment="top")
            P += line([(0, s), (tickx, s)], color="black")
            P += line([(r, 0), (r, ticky)], color="black")
        P.set_aspect_ratio(aspect)
        P.axes(False)
        return encode_plot(P, pad=0, pad_inches=0, bbox_inches="tight", dpi=300)

    @lazy_attribute
    def polynomial(self):
        pts = [(c, i, j) for (c, i, j, big) in self.dots if big]
        names = [f"{c}{self.e*j+i}" for (c, i, j) in pts]
        if self.e0 > 1:
            names.append("pi")
        R = PolynomialRing(ZZ, names)
        S = PolynomialRing(R, "x")
        if self.e == 1:
            return S.gen()
        x = S.gen()
        if self.e0 > 1:
            pi = R.gens()[-1]
        else:
            pi = self.p
        poly = x**self.e
        for i, (c, u, v) in enumerate(pts):
            poly += R.gen(i) * pi**(v+1) * x**u
        if not self.dots[0][3]:
            # No pi*d_0 term, so need to add just pi
            poly += pi
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
        return db.lf_fields.lucky({"new_label":self.base}, "old_label")

    @lazy_attribute
    def fields(self):
        fields = list(db.lf_fields.search(
            {"family": self.label_absolute},
            ["label", "coeffs", "gal", "galois_label", "galois_degree", "slopes", "ind_of_insep", "associated_inertia", "t", "u", "aut", "hidden", "subfield", "jump_set"]))
        if self.n0 > 1:
            fields = [rec for rec in fields if self.base in rec["subfield"] or self.oldbase in rec["subfield"]]
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
        fields, cache = self.fields
        for rec in fields:
            if not all(rec.get(col) for col in ["gal", "galois_label", "hidden"]):
                return False
        return True

    @lazy_attribute
    def some_hidden_data_available(self):
        """
        Whether there is some field in this family where the Galois group and hidden slopes are both known.
        """
        if self.mass_found == 0:
            return False
        fields, cache = self.fields
        for rec in fields:
            if all(rec.get(col) for col in ["gal", "galois_label", "hidden"]):
                return True
        return False

    @lazy_attribute
    def galois_groups(self):
        fields, cache = self.fields
        opts = sorted(Counter((rec["gal"], rec["galois_label"]) for rec in fields if "gal" in rec and "galois_label" in rec).items())
        if not opts:
            return "No Galois groups in this family have been computed"

        def show_gal(label, cnt):
            kwl = transitive_group_display_knowl(label, cache=cache)
            if len(opts) == 1:
                return kwl
            url = url_for(".family_page", label=self.label, gal=label)
            return f'{kwl} (<a href="{url}#fields">show {cnt}</a>)'
        s = ", ".join(show_gal(label, cnt) for ((t, label), cnt) in opts)
        if not self.all_hidden_data_available:
            s += " (incomplete)"
        return s

    @lazy_attribute
    def means_display(self):
        return latex_content(self.means).replace("[", r"\langle").replace("]", r"\rangle")

    @lazy_attribute
    def rams_display(self):
        return latex_content(self.rams).replace("[", "(").replace("]", ")")

    @lazy_attribute
    def hidden_slopes(self):
        fields, cache = self.fields
        hidden = Counter(rec["hidden"] for rec in fields if "hidden" in rec)
        if not hidden:
            return "No hidden slopes in this family have been computed"

        def show_hidden(x, cnt):
            disp = latex_content(x)
            if len(hidden) == 1:
                return disp
            url = url_for(".family_page", label=self.label, hidden=x)
            return f'{disp} (<a href="{url}#fields">show {cnt}</a>)'
        s = ", ".join(show_hidden(x, cnt) for (x, cnt) in hidden.items())
        if not self.all_hidden_data_available:
            s += " (incomplete)"
        return s

    @lazy_attribute
    def indices_of_insep(self):
        fields, cache = self.fields
        ii = sorted(Counter(tuple(rec["ind_of_insep"]) for rec in fields).items())

        def show_ii(x, cnt):
            disp = str(x).replace(" ","").replace("[]", r"[\ ]")
            if len(ii) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, ind_of_insep=disp, insep_quantifier="exactly")
            return f'${disp}$ (<a href="{url}#fields">show {cnt}</a>)'
        return ", ".join(show_ii(list(x), cnt) for (x,cnt) in ii)

    @lazy_attribute
    def associated_inertia(self):
        fields, cache = self.fields
        ai = sorted(Counter(tuple(rec["associated_inertia"]) for rec in fields).items())

        def show_ai(x, cnt):
            disp = str(x).replace(" ","").replace("[]", r"[\ ]")
            if len(ai) == 1:
                return f"${disp}$"
            url = url_for(".family_page", label=self.label, associated_inertia=disp)
            return f'${disp}$ (<a href="{url}#fields">show {cnt}</a>)'
        return ", ".join(show_ai(list(x), cnt) for (x,cnt) in ai)

    @lazy_attribute
    def jump_set(self):
        fields, cache = self.fields
        js = sorted(Counter(tuple(rec["jump_set"]) for rec in fields if "jump_set" in rec).items())

        def show_js(x, cnt):
            if not x:
                srch = "[]"
                disp = "undefined"
            else:
                srch = str(x).replace(" ","")
                disp = f"${srch}$"
            if len(js) == 1:
                return disp
            url = url_for(".family_page", label=self.label, jump_set=srch)
            return f'{disp} (<a href="{url}#fields">show {cnt}</a>)'
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
            if rec.get("galois_degree") is not None and rec.get("galois_label") is not None and rec.get("slopes") is not None:
                gps[rec["galois_degree"]].add(rec["galois_label"])
                slopes[rec["galois_degree"]].add(rec["slopes"])
        Ns = sorted(gps)
        dyns = []
        for N in Ns:
            attr = {
                'cols': ['hidden', 'galois_label'],
                'constraint': {'family': self.label, 'galois_degree': N},
                'totaler': totaler(row_counts=(len(gps[N]) > 1), col_counts=(len(slopes[N]) > 1), row_proportions=False, col_proportions=False),
                'col_title': f'Galois groups of order {N}' if len(Ns) > 1 else 'Galois groups',
            }
            dyns.append((N, stats.prep(attr)))
        return dyns
