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
FAMILY_RE = re.compile(r'(\d+(?:\.\d+\.\d+\.\d+)?)-(?:(\d+)\.(\d+(?:_\d+)*))?')

class pAdicSlopeFamily:
    def __init__(self, tame, slopes=[], heights=[], rams=[], count_cache=None):
        self.tame = tame
        if "." in tame:
            p = ZZ(tame.split(".")[0])
            rec = db.lf_fields.lookup(tame, ["e", "f"])
            self.e, self.f = rec["e"], rec["f"]
        else:
            p = ZZ(tame)
            self.e = self.f = 1
        # For now, these slopes are Serre-Swan slopes, not Artin-Fontaine slopes
        assert p.is_prime()
        self.w = w = max(len(L) for L in [slopes, heights, rams])
        # We support tamely ramified fields by specifying a tame base and empty slopes/rams/heights
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
        if w and not rams:
            rams = [heights[0]] + [heights[k] - p*heights[k-1] for k in range(1,w)]
        if w and not slopes:
            slopes = [heights[0] / (p-1)] + [(heights[k] - heights[k-1]) / euler_phi(p**(k+1)) for k in range(1,w)]
        self.slopes = slopes
        self.visible = self.artin_slopes = [s + 1 for s in slopes]
        self.heights = heights
        self.rams = rams
        self.n = self.e = n = p**w
        self.p = p
        self.c = heights[-1] + n - 1 # TODO: This is now wrong!
        self.count_cache = count_cache

    @lazy_attribute
    def scaled_heights(self):
        p = self.p
        return [h / p**i for (i, h) in enumerate(self.heights, 1)]

    @lazy_attribute
    def bands(self):
        return [((0, 1+h), (self.n, h), (0, 1+s), (self.n, s)) for (h, s) in zip(self.scaled_heights, self.slopes)]

    @lazy_attribute
    def black(self):
        return [(0, 1), (self.n, 0)]

    @lazy_attribute
    def virtual_green(self):
        p, n, w = self.p, self.n, self.w
        last_slope = {}
        for i, s in enumerate(self.slopes, 1):
            last_slope[s] = i
        ans = []
        for i, (h, s) in enumerate(zip(self.scaled_heights, self.slopes), 1):
            u = n*frac(h)
            v = 1 + floor(h)
            if last_slope[s] == i:
                if (n*frac(h)).valuation(p) == w - i:
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
        p, n, w = self.p, self.n, self.w
        for i, (s, (u, v, code)) in enumerate(zip(self.slopes, self.virtual_green), 1):
            if u.denominator() == 1 and code == -1:
                self.blue.append((u, v, True))
            u = floor(u + 1)
            #print("Starting", i, s, u, v, code, n, w)
            while v <= 1 + s - u/n:
                #print("While", u, v, 1 + s - u/n, u.valuation(p), w-i)
                if u == n:
                    u = ZZ(0)
                    v += 1
                if v == 1 + s - u/n:
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
    def label(self):
        den = lcm(s.denominator() for s in self.slopes)
        nums = "_".join(str(den*n) for n in self.slopes)
        return f"{self.tame}-{den}.{nums}"

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
        if len(self.visible) > 1:
            aspect = 0.75 * self.n / self.visible[-1]
        else:
            aspect = 1
        P.set_aspect_ratio(aspect)
        #P._set_extra_kwds(dict(xmin=0, xmax=self.n, ymin=0, ymax=self.slopes[-1] + 1, ticks_integer=True))
        #return P
        return encode_plot(P, pad=0, pad_inches=0, bbox_inches="tight")

    @lazy_attribute
    def polynomial(self):
        pts = ([("a", u, v) for (u, v) in self.solid_green] +
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
    def gamma(self):
        if self.f == 1:
            return len(self.red)
        n = self.n
        gamma = 0
        for (u, v, _) in self.red:
            s = v + u/n - 1
            cnt = self.slopes.count(s)
            gamma += gcd(cnt, self.f)
        return gamma

    @lazy_attribute
    def poly_count(self):
        p, f, alpha, beta, gamma = self.p, self.f, len(self.solid_green), len(self.blue), self.gamma
        q = p**f
        return (q-1)**alpha * q**beta * p**gamma

    @lazy_attribute
    def mass(self):
        fields, cache = self.fields
        return sum(ZZ(1) / rec["aut"] for rec in fields)

    @lazy_attribute
    def base(self):
        if "." in self.tame:
            url = url_for(".by_label", label=self.tame)
            return f'<a href="{url}">{self.tame}</a>'
        url = url_for(".by_label", label=f"{self.p}.1.0.1")
        return fr'<a href="{url}">$\Q_{{{self.p}}}$</a>'

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
    def field_count(self):
        if self.count_cache is not None:
            return self.count_cache[str(self.artin_slopes)]
        return db.lf_fields.count({"family": self.label})

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
        print("gps", gps)
        print("slopes", slopes)
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
        for N in sorted(gps):
            rowcount = len(cur_rows)
            colcount = len(cur_cols)
            cur_rows = cur_rows.union(slopes[N])
            cur_cols = cur_cols.union(gps[N])
            if curN and (len(cur_cols) > max_cols or len(cur_rows) > max_rows):
                add_grid(curN, rowcount, colcount)
                cur_rows = set()
                cur_cols = set()
                curN = set()
            curN.add(N)
        rowcount = len(cur_rows.union(slopes[N]))
        colcount = len(cur_cols.union(gps[N]))
        add_grid(curN, rowcount, colcount)
        return dyns

    def satisfies(self, query):
        if "$or" in query:
            raise ValueError("Multiple ranges not supported")
        D = query.get("c")
        if isinstance(D, dict):
            if "$gte" in D and D["$gte"] > self.c:
                return False
            if "$lte" in D and D["$lte"] < self.c:
                return False
        elif D is not None and D != self.c:
            return False
        # TODO: add tests for visible
        return True

    @classmethod
    def _sortkey(cls, sort):
        # We don't support pairs (col, -1) yet.
        assert all(isinstance(x, str) for x in sort)
        def key(family):
            return tuple(getattr(family, x) for x in sort)
        return key

    @classmethod
    def resort(cls, p, it, query, ctr, sort=None, limit=None, offset=None, wrap=True, count_cache=None):
        test = not all(key in ["p", "n"] for key in query)
        if sort is None:
            for rmvec in it:
                if test or wrap:
                    family = cls(str(p), rams=rmvec, count_cache=count_cache)
                if (test and family.satisfies(query)) or not test:
                    if (offset is None or ctr[0] >= offset) and (limit is None or ctr[0] < limit):
                        yield (family if wrap else rmvec)
                    ctr[0] += 1
                    if limit is not None and ctr[0] >= limit:
                        break
        else:
            families = [cls(str(p), rams=rmvec, count_cache=count_cache) for rmvec in it]
            if test:
                families = [family for family in families if family.satisfies(query)]
            families.sort(key=cls._sortkey(sort))
            for family in families:
                if (offset is None or ctr[0] >= offset) and (limit is None or ctr[0] < limit):
                    yield (family if wrap else family.rams)
                ctr[0] += 1
                if limit is not None and ctr[0] >= limit:
                    break

    @classmethod
    def families(cls, query, count=False, random=False, limit=None, offset=None, sort=None, info=None, one_per=None, count_cache=None):
        orig_limit = limit
        limit = 1000
        pmin, pmax = unparse_range(query.get("p"), "p")
        if pmin is None:
            pmin = ZZ(2)
        else:
            pmin = next_prime(pmin - 1)
        if pmax is not None:
            pmax = previous_prime(pmax + 1)
        nmin, nmax = unparse_range(query.get("n"), "degree")
        if nmin is None or nmin <= pmin:
            nmin = pmin
        else:
            nmin = ZZ(nmin)
        if nmax is not None and pmax is not None and pmax > nmax:
            pmax = previous_prime(nmax + 1)
            nmax = ZZ(nmax)

        if count:
            # We don't want to limit iteration with limit, offset or sort
            limit = offset = sort = None

        def pw_ram_iterator(p, w):
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
                        yield rmvec
        def full_iterator():
            ctr = [0] # We use a list so that it can be modified inside resort
            if pmax is None:
                n = nmin
                while True:
                    p, w = n.is_prime_power(get_data=True)
                    if w > 0 and p >= pmin:
                        yield from cls.resort(p, pw_ram_iterator(p, w), query, ctr, sort=sort, limit=limit, offset=offset, count_cache=count_cache)
                    #if limit is not None and ctr[0] >= limit:
                    #    break
                    n += 1
                    if nmax is not None and n > nmax:
                        break
            else:
                nextq = set(prime_range(pmin, pmax + 1))
                while True:
                    q = min(nextq)
                    if nmax is not None and q > nmax:
                        break
                    p, w = q.is_prime_power(get_data=True)
                    if q >= nmin:
                        yield from cls.resort(p, pw_ram_iterator(p, w), query, ctr, sort=sort, limit=limit, offset=offset, count_cache=count_cache)
                    #if limit is not None and ctr[0] >= limit:
                    #    break
                    nextq.remove(q)
                    nextq.add(p * q)

        if random:
            if pmax is not None and pmin > pmax or prime_pi(pmin-1) == prime_pi(pmax):
                return # No primes in range
            if nmax is None:
                # We first choose p, then n
                if pmax is None:
                    # Choose a prime index and find the corresponding prime
                    poffset = ZZ.random_element()
                    while poffset < 0:
                        poffset = ZZ.random_element()
                    if pmin is not None:
                        poffset += prime_pi(pmin - 1)
                    p = nth_prime(poffset + 1) # 1-indexed
                else:
                    # Choose a random prime in the given range
                    p = random_prime(pmax+1, proof=False, lbound=pmin)

                # Now we choose an exponent w, large enough to satisfy nmin if relevant
                if nmin <= p:
                    wmin = 1
                else:
                    wmin = (nmin - 1).exact_log(p) + 1
                w = wmin + ZZ.random_element()
                while w < wmin:
                    w = wmin + ZZ.random_element()
                n = p**w
            else:
                # We choose uniformly on valid n
                if nmin > nmax:
                    return
                if pmax is None:
                    # We sample from the n-range until we find valid power
                    # We first ensure that there is at least one valid prime power in the given range
                    # (otherwise we might loop forever below)
                    def has_prime_power(a, b, p0):
                        """
                        Return True if there is a prime power q with a <= q <= b and q a power of p >= p0
                        """
                        k = 1
                        while True:
                            if p0**k > b:
                                return False
                            aa, exact = a.nth_root(k, truncate_mode=1)
                            if not exact:
                                aa += 1
                            bb, exact = b.nth_root(k, truncate_mode=1)
                            if prime_pi(bb) > prime_pi(aa - 1):
                                # There is a prime in the kth root range, and the p0**k > b test
                                # guarantees that there is one that is big enough.
                                return True
                            k += 1
                    if not has_prime_power(nmin, nmax, pmin):
                        return

                    # Now we know there are valid outputs, so we choose randomly until we find one
                    while True:
                        n = ZZ.random_element(nmin, nmax + 1)
                        p, w = n.is_prime_power(get_data=True)
                        if w > 0 and p >= pmin:
                            break
                else:
                    # We construct the set of valid prime_powers in the n-range and choose one
                    valid = []
                    for p in prime_range(pmin, pmax + 1):
                        for w in range((nmin - 1).exact_log(p) + 1, nmax.exact_log(p) + 1):
                            valid.append((p, w))
                    p, w = choice(valid)

            if all(key in ["p", "n"] for key in query):
                # We can short-circuit actually constructing the families
                # It would be nice to know the length of this list ahead of time in order to save memory
                rmvec = choice(list(pw_ram_iterator(p, w)))
                return pAdicSlopeFamily(str(p), rams=rmvec, count_cache=count_cache).label
            else:
                valid = []
                for rmvec in pw_ram_iterator(p, w):
                    family = pAdicSlopeFamily(str(p), rams=rmvec, count_cache=count_cache)
                    if family.satisfies(query):
                        valid.append(family.label)
                return choice(valid)

        if count:
            if nmax is None:
                return r"$\infty$"
            return len(list(full_iterator()))

        full = full_iterator()
        first1000 = list(itertools.islice(full, 1000))
        print("LENNNN", len(first1000))

        if info is not None:
            info["query"] = dict(query)
            info["count"] = orig_limit
            info["start"] = offset
            info["number"] = offset + len(first1000)
            info["exact_count"] = (len(first1000) < 1000)

        if limit is None or orig_limit > 1000:
            return itertools.chain(first1000, full)
        else:
            return first1000[:orig_limit]


