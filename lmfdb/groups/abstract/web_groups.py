import re
# import timeout_decorator
import os
import yaml
from lmfdb import db
from flask import url_for
from urllib.parse import quote_plus

from sage.all import (
    Permutations,
    Permutation,
    PermutationGroup,
    SymmetricGroup,
    ZZ,
    GF,
    Zmod,
    factor,
    matrix,
    latex,
    lazy_attribute,
    prod,
    lcm,
    is_prime,
    cartesian_product_iterator,
    exists,
)
from sage.libs.gap.libgap import libgap
from sage.libs.gap.element import GapElement
from sage.misc.cachefunc import cached_function, cached_method
from sage.databases.cremona import class_to_int, cremona_letter_code
from collections import Counter, defaultdict
from lmfdb.utils import (
    display_knowl,
    to_ordinal,
    web_latex,
    letters2num,
    WebObj,
    pos_int_and_factor,
    raw_typeset,
)
from .circles import find_packing


nc = "not computed"

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")
perm_re = re.compile(r"^\(\d+(,\d+)*\)(,?\(\d+(,\d+)*\))*$")

def label_sortkey(label):
    L = []
    for piece in label.split("."):
        for i, x in enumerate(re.split(r"(\D+)", piece)):
            if x:
                if i % 2:
                    x = letters2num(x)
                else:
                    x = int(x)
                L.append(x)
    return L

def is_atomic(s):
    return not any(sym in s for sym in [".", ":", r"\times", r"\rtimes", r"\wr"])

def sub_paren(s):
    return s if is_atomic(s) else "(%s)" % s

def group_names_pretty(label):
    # Avoid using this function if you have the tex_name available without a database lookup
    if isinstance(label, str):
        if label.startswith("ab/"):
            preinvs = label[3:].split(".")
            invs = []
            for pe in preinvs:
                if "_" in pe:
                    p, e = pe.split("_")
                    invs.extend([ZZ(p)] * int(e))
                else:
                    invs.append(ZZ(pe))
            return abelian_gp_display(invs)
        pretty = db.gps_groups.lookup(label, "tex_name")
    else:
        pretty = label.tex_name
    if pretty:
        return pretty
    else:
        return label

def group_pretty_image(label):
    # Avoid using this function if you have the tex_name available without a database lookup
    pretty = group_names_pretty(label)
    img = db.gps_images.lookup(pretty, "image")
    if img:
        return str(img)
    # fallback which should always be in the database
    img = db.gps_images.lookup("?", "image")
    if img:
        return str(img)
    # we should not get here

def create_gens_list(genslist):
    # For Magma
    gens_list = [f"G.{i}" for i in genslist]
    return str(gens_list).replace("'", "")

def create_gap_assignment(genslist):
    # For GAP
    return " ".join(f"{var_name(j)} := G.{i};" for j, i in enumerate(genslist))

def create_magma_assignment(G):
    used = [u - 1 for u in sorted(G.gens_used)]
    rel_ords = [ZZ(p) for p in G.PCG.FamilyPcgs().RelativeOrders()]
    ngens = len(used)
    names = []
    for j, i in enumerate(used):
        if j == ngens - 1:
            icap = len(rel_ords)
        else:
            icap = used[j+1]
        power = 1
        v = var_name(j)
        for i0 in range(i, icap):
            if power == 1:
                names.append(v)
            else:
                names.append(f"{v}{power}")
            power *= rel_ords[i0]
    return str(names).replace("'", '"')

def split_matrix_list(longList,d):
    # for code snippets, turns d^2 list into d lists of length d for Gap matrices
    return [longList[i:i+d] for i in range(0,d**2,d)]

def split_matrix_list_ZN(longList,d, Znfld):
    longList = [f"ZmodnZObj({x},{Znfld})" for x in longList]
    return str([longList[i:i+d] for i in range(0,d**2,d)]).replace("'", "")


def split_matrix_list_Fp(longList,d,e):
    return [longList[i:i+d]*e for i in range(0,d**2,d)]


def split_matrix_list_Fq(longList,d, Fqfld):
# for gap definition of Fq
    longList = [f"0*Z({Fqfld})" if x == -1 else f"Z({Fqfld})^{x}" for x in longList]  #-1 distinguishes 0 from z^0
    return str([longList[i:i+d] for i in range(0,d**2,d)]).replace("'", "")


def split_matrix_Fq_add_al(longList,d):
# for magma definition of Fq
    longList = [0 if x == -1 else 1 if x == 0 else f"al^{x}" for x in longList]
    return str([longList[i:i+d] for i in range(0,d**2,d)]).replace("'", "")


# Functions below are for conjugacy class searches
def gp_label_to_cc_data(gp):
    gp_ord, gp_counter = gp.split(".")
    gp_order = int(gp_ord)
    if re.fullmatch(r'\d+',gp_counter):
        return gp_order, int(gp_counter)
    return gp_order, class_to_int(gp_counter) + 1


# mimics magma IsInSmallGroupDatabase
def in_small_gp_db(order):
    if order == 1024:
        return False
    if order <= 2000 or order in {2187, 6561, 3125, 2401}:
        return True
    f = factor(order)
    if all(f[i][1] == 1 and f[i][0] < 1073741824 for i in range(len(f))):
        return True
    if len(f) == 2:
        pairs, n = exists((i for i in {0,1}), lambda i: f[i][1] == 1)
        if pairs:
            p = f[1-n]
            if ( p[1] <= 2 or p[0] == 2 and p[1] <= 8
                  or p[0] == 3 and p[1] <= 6
                  or p[0] == 5 and p[1] <= 5
                  or p[0] == 7 and p[1] <= 4 ):
                return True
    if len(f) <= 3 and sum([p[1] for p in f]) == 4:
        return True
    if len(f) == 1 and f[0][1] <= 7:
        return True
    return False


def cc_data_to_gp_label(order,counter):
    if in_small_gp_db(order):
        return str(order) + '.' + str(counter)
    return str(order) + '.' + cremona_letter_code(counter-1)


@cached_function(key=lambda label,name,pretty,ambient,aut,profiledata,cache: (label,name,pretty,ambient,aut,profiledata))
def abstract_group_display_knowl(label, name=None, pretty=True, ambient=None, aut=False, profiledata=None, cache={}):
    # If you have the group in hand, set the name using gp.tex_name since that will avoid a database call
    if name and '?' in name:
        name = None
    if not name:
        if pretty:
            if label in cache and "tex_name" in cache[label]:
                name = cache[label]["tex_name"]
            else:
                name = db.gps_groups.lookup(label, "tex_name")
            if name is None:
                if label is None:
                    name = '?'
                else:
                    name = f"Group {label}"
            else:
                name = f"${name}$"
        else:
            name = f"Group {label}"
    if ambient is None:
        args = label
    else:
        if profiledata is not None:
            # We use $ as a separator since it won't be in latex strings
            profiledata = '%24'.join(quote_plus(str(c)) for c in profiledata)
        args = f"{label}%7C{ambient}%7C{aut}%7C{profiledata}"
    return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={args}&func=group_data">{name}</a>'

def primary_to_smith(invs):
    if not invs:
        return []
    by_p = defaultdict(list)
    for q in invs:
        p, _ = q.is_prime_power(get_data=True)
        by_p[p].append(q)
    M = max(len(qs) for qs in by_p.values())
    for p, qs in by_p.items():
        by_p[p] = [1] * (M - len(qs)) + qs
    return [prod(qs) for qs in zip(*by_p.values())]

def abelian_gp_display(invs):
    if len(invs) == 0:
        return "C_1"
    return r" \times ".join(
        ("C_{%s}^{%s}" % (q, e) if e > 1 else "C_{%s}" % q)
        for (q, e) in Counter(invs).items()
    )

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
    return s.count("?"), len(s), v

def var_name(i):
    if i < 26:
        return chr(97 + i)  # a-z
    elif i < 52:
        return chr(39 + i)  # A-Z
    elif i < 76:
        return chr(893 + i)  # greek lower case
    else:
        raise RuntimeError("too many variables in presentation")

def abelian_get_elementary(snf):
    plist = ZZ(snf[0]).prime_factors()
    if len(snf) == 1:  # cyclic group, all primes are good
        return prod(plist)
    possiblep = ZZ(snf[1]).prime_factors()
    if len(possiblep) > 1:
        return 1
    return possiblep[0]


def compress_perm(perms, cutoff=150, sides=70):
    if len(perms) < cutoff or sides >= cutoff:
        return r'$\langle' + perms + r'\rangle$'
    short_perm = r'$\langle' + perms[:sides]
    while perms[sides] != ")":  # will always have ")" as long as sides < cutoff (see above)
        short_perm = short_perm + perms[sides]
        sides += 1
    short_perm = short_perm + r') \!\cdots\! \rangle$'
    return short_perm


def compress_pres(pres, cutoff=150, sides=70):
    if len(pres) < cutoff:
        return f"${pres}$"
    short_pres = '${' + pres[:sides]
    while pres[sides] != "=" and sides < len(pres)-1:
        short_pres = short_pres + pres[sides]
        sides += 1
    if sides < len(pres)-1:  # finished because of "="
        short_pres = short_pres + r'= \!\cdots\! \rangle}$'
        return short_pres
    else:  # just return whole thing if needed to go to end and ran out of "="
        return f"${pres}$"


class WebAbstractGroup(WebObj):
    table = db.gps_groups

    def __init__(self, label, data=None):
        self.source = "db" # can be overridden below by either GAP or LiveAbelian
        if isinstance(data, WebAbstractGroup):
            # This happens if we're using the _minmax_data in tex_name
            self.G = data.G
            label = data.label
            data = data._data
        elif isinstance(data, GapElement) and label == "?":
            # We're recursing, so we need to check whether we're small enough that we landed in the database
            self.G = G = data
            n = G.Order()
            if n.IdGroupsAvailable():
                n, i = libgap.IdGroup(G)
                label = f"{n}.{i}"
                dbdata = self.table.lookup(label)
                if dbdata is not None:
                    data = dbdata
                else:
                    self.source = "GAP"
        elif isinstance(data, LiveAbelianGroup):
            self._data = data.snf
            data = data.snf
            self.source = "LiveAbelian"
        WebObj.__init__(self, label, data)
        if self._data is None:
            # Check if the label is for an order supported by GAP's SmallGroup
            from .main import abstract_group_label_regex
            m = abstract_group_label_regex.fullmatch(label)
            if m is not None and m.group(2) is not None and m.group(2).isdigit():
                n = ZZ(m.group(1))
                i = ZZ(m.group(2))
                if libgap.SmallGroupsAvailable(n):
                    maxi = libgap.NrSmallGroups(n)
                    if 0 < i <= maxi:
                        self._data = (n, i)
                        self.source = "GAP"
                else:   # issue with 3^8 being in Magma but not GAP db
                    self._data = (n, i)
                    self.source = "Missing"
        if isinstance(self._data, list):  # live abelian group
            self.snf = primary_to_smith(self._data)  # existence is a marker that we were here
            self.G = LiveAbelianGroup(self.snf)
            # a few properties are easier to shortcut than to do through LiveAbelianGroup
            self.elementary = abelian_get_elementary(self.snf)
            self.hyperelementary = self.elementary
            self.Zgroup = len(self.snf) == 1
            self.Agroup = True
            self.source = "LiveAbelian"

    # We support some basic information for groups not in the database using GAP
    def live(self):
        return self._data is not None and not isinstance(self._data, dict)

    @lazy_attribute
    def G(self):
        if self.live():
            # We current support several kinds of live groups:
            #  giving a small group id as a tuple (among orders not in the LMFDB database)
            #  giving a list of (primary) abelian invariants
            #  giving a set of generating permutations
            #  giving a GAP group (for recursion)
            if isinstance(self._data, tuple):
                n, i = self._data
                return libgap.SmallGroup(n, i)
            elif isinstance(self._data, list):
                return libgap.AbelianGroup(primary_to_smith(self._data))
            elif isinstance(self._data, str):
                s = self._data.replace(" ", "")
                if perm_re.fullmatch(s):
                    # a list of permutations
                    gens = [f"({g})" for g in s[1:-1].split("),(")]
                    G = PermutationGroup([Permutation(g) for g in gens])
                    return G._libgap_()
            elif isinstance(self._data, GapElement):
                return self._data
        # Reconstruct the group from the stored data
        if self.order == 1 or self.element_repr_type == "PC":  # trvial
            return self.PCG
        else:
            if self.element_repr_type == "Lie":   #need to take first entry of Lie type
                gens = [self.decode(g) for g in self.representations[self.element_repr_type][0]["gens"]]
            else:
                gens = [self.decode(g) for g in self.representations[self.element_repr_type]["gens"]]
            return libgap.Group(gens)

    def G_gens(self):
        # Generators for the gap group G
        G = self.G
        rep_type = self.element_repr_type
        repn = self.representations[rep_type]
        if self.order == 1:
            gens = []
        elif rep_type == "PC":
            gens = G.GeneratorsOfGroup()
            gens = [gens[z-1] for z in repn['gens']]
        elif rep_type == "Perm":
            n = repn["d"]
            gens = [SymmetricGroup(n)(Permutations(n).unrank(z)) for z in repn["gens"]]
        elif rep_type == "Lie":
            # problems here
            # projective groups need to be accounted for
            gens = [self.decode(g) for g in repn[0]["gens"]]
        elif rep_type in ['GLZ', 'GLFp','GLZN','GLZq','GLFq']:
            gens = [self.decode(g) for g in repn["gens"]]
        return gens

    @lazy_attribute
    def PCG(self):
        if self.order == 1:
            return libgap.TrivialGroup()
        elif "PC" in self.representations:
            return libgap.PcGroupCode(self.pc_code, self.order)
        G = self.G
        if G.IsPcGroup():
            return G
        return G.IsomorphismPcGroup().Image()

    # The following are used for live groups to emulate database groups
    # by computing relevant quantities in GAP
    @lazy_attribute
    def order(self):
        return ZZ(self.G.Order())
    @lazy_attribute
    def exponent(self):
        if self.G:
            return ZZ(self.G.Exponent())
        return None

    @lazy_attribute
    def cyclic(self):
        return bool(self.G.IsCyclic())
    @lazy_attribute
    def abelian(self):
        return bool(self.G.IsAbelian())
    @lazy_attribute
    def nilpotent(self):
        return bool(self.G.IsNilpotent())
    @lazy_attribute
    def supersolvable(self):
        return bool(self.G.IsSupersolvable())
    @lazy_attribute
    def monomial(self):
        return bool(self.G.IsMonomial())
    @lazy_attribute
    def solvable(self):
        return bool(self.G.IsSolvable())
    @lazy_attribute
    def metabelian(self):
        return bool(self.G.DerivedSubgroup().IsAbelian())
    @lazy_attribute
    def almost_simple(self):
        return bool(self.G.IsAlmostSimpleGroup())
    @lazy_attribute
    def simple(self):
        return bool(self.G.IsSimple())
    @lazy_attribute
    def perfect(self):
        return bool(self.G.IsPerfect())
    @lazy_attribute
    def quasisimple(self):
        return not self.solvable and self.perfect and (self.G / self.G.Center()).IsSimple()

    @lazy_attribute
    def nilpotency_class(self):
        if self.nilpotent:
            return ZZ(self.G.NilpotencyClassOfGroup())
        return ZZ(-1)

    @lazy_attribute
    def derived_length(self):
        if not self.solvable:
            return ZZ(0)
        return ZZ(self.G.DerivedLength())

    @lazy_attribute
    def Sylows(self):
        if self.solvable:
            return list(self.G.SylowSystem())
        else:
            return [self.G.SylowSubgroup(p) for p in self.order.prime_factors()]

    @lazy_attribute
    def SylowComplements(self):
        return list(self.G.ComplementSystem())

    @lazy_attribute
    def Zgroup(self):
        return all(P.IsCyclic() for P in self.Sylows)
    @lazy_attribute
    def Agroup(self):
        return all(P.IsAbelian() for P in self.Sylows)

    @lazy_attribute
    def metacyclic(self):
        # for now, we don't try to determine whether G is metacyclic
        return None

    @lazy_attribute
    def rational(self):
        # We don't want to compute the character table
        return None

    @lazy_attribute
    def transitive_degree(self):
        if isinstance(self.G, LiveAbelianGroup):
            return self.order
        return None # "not computed"

    @lazy_attribute
    def pgroup(self):
        if self.order == 1:
            return 1
        F = self.order.factor()
        if len(F) == 1:
            return F[0][0]
        return ZZ(0)

    @lazy_attribute
    def elementary(self):
        ans = 1
        if self.solvable and self.order > 1:
            for p, P, H in zip(self.order.prime_factors(), self.Sylows, self.SylowComplements):
                if self.G.IsNormal(P) and self.G.IsNormal(H) and H.IsCyclic():
                    ans *= p
        return ans

    @lazy_attribute
    def hyperelementary(self):
        ans = 1
        if self.solvable and self.order > 1:
            for p, P, H in zip(self.order.prime_factors(), self.Sylows, self.SylowComplements):
                if self.G.IsNormal(H) and H.IsCyclic():
                    ans *= p
        return ans

    @lazy_attribute
    def order_stats(self):
        order_stats = defaultdict(ZZ)
        if self.abelian:
            primary = defaultdict(lambda: defaultdict(int))
            for q in self.primary_abelian_invariants:
                p, e = q.is_prime_power(get_data=True)
                primary[p][e] += 1
            comps = []
            for p, part in primary.items():
                trunccnt = defaultdict(ZZ)  # log of (product of q, truncated at p^e)
                M = max(part)
                for e, k in part.items():
                    for i in range(1, M + 1):
                        trunccnt[i] += k * min(i, e)
                comps.append([(1, 1)] + [(p**i, p**trunccnt[i] - p**trunccnt[i - 1]) for i in range(1, M + 1)])
            for tup in cartesian_product_iterator(comps):
                order = prod(pair[0] for pair in tup)
                cnt = prod(pair[1] for pair in tup)
                order_stats[order] = cnt
        else:
            for c in self.conjugacy_classes:
                order_stats[c.order] += c.size
        return sorted(order_stats.items())

    # @timeout_decorator.timeout(3, use_signals=False)
    def _aut_group_data(self):
        if self.abelian:
            # See https://www.msri.org/people/members/chillar/files/autabeliangrps.pdf
            invs = self.primary_abelian_invariants
            by_p = defaultdict(Counter)
            for q in invs:
                p, e = q.is_prime_power(get_data=True)
                by_p[p][e] += 1
            aut_order = 1
            for p, E in by_p.items():
                c = 0
                d = 0
                n = sum(E.values())
                for e in sorted(E):
                    m = E[e]
                    d += m
                    for i in range(1, m + 1):
                        aut_order *= p**d - p**(d - i)
                    aut_order *= p**(((e - 1) * (n - c) + e * (n - d)) * m)
                    c += m
            if aut_order < 2**32 and libgap(aut_order).IdGroupsAvailable():
                A = self.G.AutomorphismGroup()
                if A:
                    aid = int(A.IdGroup()[1])
                else:
                    aid = 0
            else:
                aid = 0
            return aut_order, aid, aut_order, aid
        A = self.G.AutomorphismGroup()
        aut_order = A.Order()
        if aut_order.IdGroupsAvailable():
            aid = A.IdGroup()[1]
        else:
            aid = 0
        Z_order = self.G.Center().Order()
        out_order = aut_order * Z_order / self.G.Order()
        if out_order.IdGroupsAvailable():
            I = A / A.InnerAutomorphismsAutomorphismGroup()
            oid = I.IdGroup()[1]
        else:
            oid = 0
        return int(aut_order), int(aid), int(out_order), int(oid)

    def _set_aut_data(self):
        aut_order, aid, out_order, oid = self._aut_group_data()
        self.aut_order = ZZ(aut_order)
        if aid == 0:
            # try a bit harder for cyclic groups
            if self.cyclic:
                invs = []
                for p, e in self.order.factor():
                    if p == 2:
                        if e == 2:
                            invs.append("2")
                        elif e > 2:
                            invs.extend(["2", f"{p**(e-2)}"])
                    else:
                        invs.append(f"{p**(e-1)*(p-1)}")
                self.aut_group = "ab/" + ".".join(invs)
            else:
                self.aut_group = None
        else:
            self.aut_group = f"{aut_order}.{aid}"
        self.outer_order = ZZ(out_order)
        if oid == 0:
            self.outer_group = None
        else:
            self.outer_group = f"{out_order}.{oid}"

    @lazy_attribute
    def aut_order(self):
        self._set_aut_data()
        return self.aut_order

    @lazy_attribute
    def outer_order(self):
        self._set_aut_data()
        return self.outer_order

    @lazy_attribute
    def aut_group(self):
        self._set_aut_data()
        return self.aut_group

    @lazy_attribute
    def outer_group(self):
        self._set_aut_data()
        return self.outer_group

    @lazy_attribute
    def number_conjugacy_classes(self):
        if self.abelian:
            return self.order
        return len(self.conjugacy_classes)

    @lazy_attribute
    def cc_known(self):
#        if self.representations.get("Lie") and self.representations["Lie"][0]["family"][0] == "P" and self.order < 2000:
#            return False   # problem with PGL, PSL, etc.
        return db.gps_conj_classes.exists({'group_order': self.order, 'group_counter': self.counter})

    @lazy_attribute
    def element_repr_type(self):
        if isinstance(self._data, (tuple, list)) and self.solvable:
            return "PC"
        return "Perm"

    @lazy_attribute
    def rank(self):
        if self.pgroup > 1:
            return ZZ(self.G.RankPGroup())
        if isinstance(self.G, LiveAbelianGroup):
            return len(self.snf)
        return None

    @lazy_attribute
    def primary_abelian_invariants(self):
        return sorted((ZZ(q) for q in self.G.AbelianInvariants()),
                      key=lambda x: list(x.factor()))

    @lazy_attribute
    def smith_abelian_invariants(self):
        if self.source == "LiveAbelian":
            return primary_to_smith(self.G.AbelianInvariants())
        return primary_to_smith(self.primary_abelian_invariants)

    @lazy_attribute
    def tex_name(self):
        if self.abelian:
            return abelian_gp_display(self.smith_abelian_invariants)
        G = self.G
        n = self.order
        A = None
        if self.solvable and not self.pgroup:
            # Look for a normal Hall subgroup
            halls = {ZZ(P.Order()): P for P in G.HallSystem()}
            ords = [(m, n // m, G.IsNormal(halls[n // m]))
                    for m in halls if 1 < m < n and G.IsNormal(halls[m])]
            ords.sort(key=lambda trip: (not trip[2], trip[0] + trip[1], trip[0]))
            if ords:
                m, c, norm = ords[0]
                A = halls[m]
                B = halls[c]
                symb = r"\times" if norm else r"\rtimes"
        if A is None:
            # We run through several characteristic subgroups of G
            subdata = self._subgroup_data
            poss = []
            to_try = [k for k in ["G'", "Z", r"\Phi"] if 1 < subdata[k].order < n]
            #if not to_try:
            # Put in latex code from sage here
                # this can only occur for perfect groups
            #    if self.simple:
                    #to_try = [k for k in subdata if k.startswith("M")]
            #        pass
            #    else:
            #        to_try = [k for k in subdata if k.startswith("m")]
            for i, name in enumerate(to_try):
                H = subdata[name]
                m = H.order
                if m == 1 or m == n:
                    continue
                Q = subdata[f"G/{name}"]
                if H.solvable:
                    Cs = G.ComplementClassesRepresentatives(H.G)
                else:
                    Cs = []
                if Cs:
                    poss.append((m, n // m, True, bool(G.IsNormal(Cs[0])), i, H, Q))
                else:
                    poss.append((m, n // m, False, False, i, H, Q))
            poss.sort(key=lambda tup: (not tup[2], not tup[3], tup[0] + tup[1], tup[0], tup[4]))
            if poss:
                A = poss[0][-2]
                B = poss[0][-1]
                if poss[0][3]:
                    symb = r"\times"
                elif poss[0][2]:
                    symb = r"\rtimes"
                else:
                    symb = "."
        if A is not None:
            A = WebAbstractGroup('?', data=A)
            B = WebAbstractGroup('?', data=B)
            if A.tex_name == " " or B.tex_name == " ":
                return " "
            A = A.tex_name if is_atomic(A.tex_name) else f"({A.tex_name})"
            B = B.tex_name if is_atomic(B.tex_name) else f"({B.tex_name})"
            return f"{A} {symb} {B}"
        return " "

    @lazy_attribute
    def _subgroup_data(self):
        G = self.G
        Z = G.Center()
        D = G.DerivedSubgroup()
        Phi = G.FrattiniSubgroup()
        F = G.FittingSubgroup()
        R = G.RadicalGroup()
        S = G.Socle()
        if isinstance(self._data, list):
            GZ = G.Zquotient()
            GD = G.Dquotient()
            GPhi = G.Phiquotient()
            GF = G.Fquotient()
            GR = G.Rquotient()
            GS = G.Squotient()
        else:
            GZ = G / Z
            GD = G / D
            GPhi = G / Phi
            GF = G / F
            GR = G / R
            GS = G / S
        label_for = {}
        label_rev = defaultdict(list)
        gapH = {"Z": Z,
                "G/Z": GZ,
                "G'": D,
                "G/G'": GD,
                r"\Phi": Phi,
                r"G/\Phi": GPhi,
                r"\operatorname{Fit}": F,
                r"G/\operatorname{Fit}": GF,
                "R": R,
                "G/R": GR,
                "S": S,
                "G/S": GS}
        if not self.pgroup:
            for p, P in zip(self.order.prime_factors(), self.Sylows):
                gapH[f"P_{{{p}}}"] = P
        if not self.abelian:
            for i, M in enumerate(G.ConjugacyClassesMaximalSubgroups()):
                gapH[f"M_{{{i+1}}}"] = M.Representative()
                if G.IsNormal(M.Representative()):
                    gapH[f"G/M_{{{i+1}}}"] = G / M.Representative()
            for i, M in enumerate(G.MinimalNormalSubgroups()):
                gapH[f"m_{{{i+1}}}"] = M
                gapH[f"G/m_{{{i+1}}}"] = G / M
        for name, H in gapH.items():
            if H.Order().IdGroupsAvailable() and H.Order() < 10**9:
                label = f"{H.Order()}.{H.IdGroup()[1]}"
                label_for[name] = label
                label_rev[label].append(name)
        subdata = {}
        for rec in db.gps_groups.search({"label": {"$in": list(label_for.values())}}, ["label", "tex_name", "order"]):
            for name in label_rev[rec["label"]]:
                subdata[name] = WebAbstractGroup(rec["label"], data=rec)
                subdata[name].G = gapH[name]
        for name, H in gapH.items():
            if name not in subdata:
                label = label_for.get(name, "")
                subdata[name] = WebAbstractGroup(label, data=H)
        return subdata

    def show_special_subgroups_live(self):
        kwls = {"Z": display_knowl('group.center', 'Center'),
                "G'": display_knowl('group.commutator_subgroup', 'Commutator'),
                r"\Phi": display_knowl('group.frattini_subgroup', 'Frattini'),
                r"\operatorname{Fit}": display_knowl('group.fitting_subgroup', 'Fitting'),
                "R": display_knowl('group.radical', 'Radical'),
                "S": display_knowl('group.socle', 'Socle')}
        subdata = self._subgroup_data

        def show(sname, name=None):
            if name is None:
                name = sname
            H = subdata[name]
            if H.order == self.order:
                disp = self.label if self.tex_name == " " else f'${self.tex_name}$'
            elif H.order == 1:
                url = url_for(".by_label", label="1.1")
                disp = '$C_1$'
                disp = f'<a href="{url}">{disp}</a>'
            elif H.label:
                url = url_for(".by_label", label=H.label)
                disp = H.label if H.tex_name == " " else f'${H.tex_name}$'
                disp = f'<a href="{url}">{disp}</a>'
            elif H.abelian:
                invs = H.smith_abelian_invariants
                ab_label = ".".join(f"{q}_{e}" for q, e in Counter(invs).items())
                url = url_for(".by_abelian_label", label=ab_label)
                disp = f'<a href="{url}">${abelian_gp_display(invs)}$</a>'
            elif H.tex_name != " ":
                disp = f"${H.tex_name}$"
            else:
                disp = f"Group of order ${latex(H.order.factor())}$"
            return fr'${sname} \simeq$ {disp}'
        ans = [(kwl, show(sname), show(f"G/{sname}"), None) for sname, kwl in kwls.items()]
        if not self.pgroup:
            for p in self.order.prime_factors():
                ans.append((f"{p}-{display_knowl('group.sylow_subgroup', 'Sylow subgroup')}",
                            show(f"P_{{{p}}}"),
                            None,
                            None))
        if not self.abelian:
            for typ, ov in [("M", display_knowl("group.maximal_subgroup", "Maximal subgroups")), ("m", display_knowl("group.maximal_quotient", "Maximal quotients"))]:
                by_disp = defaultdict(Counter)
                name_lookup = defaultdict(dict)
                for name, M in subdata.items():
                    if not name.startswith(typ):
                        continue
                    Q = subdata.get(f"G/{name}")
                    if Q is None:
                        key = (ZZ(self.G.Index(self.G.Normalizer(M.G))), M.label, M.tex_name, None, None)
                    else:
                        key = (1, M.label, M.tex_name, Q.label, Q.tex_name)
                    order = self.order // M.order if typ == "M" else M.order
                    by_disp[order][key] += 1
                    if key not in name_lookup[order]:
                        name_lookup[order][key] = name
                for order, D in sorted(by_disp.items()):
                    for i, (key, cc_cnt) in enumerate(sorted(D.items())):
                        sub_cnt, Mlabel, Mtex, Qlabel, Qtex = key
                        name = name_lookup[order][key]
                        if len(D) == 1:
                            subscr = order
                        else:
                            subscr = f"{order},{i+1}"
                        dispname = f"{typ}_{{{subscr}}}"
                        Q = show(f"G/{dispname}", f"G/{name}") if f"G/{name}" in subdata else None
                        if sub_cnt > 1:
                            if cc_cnt > 1:
                                extra = f"{cc_cnt} conjugacy classes, each containing {sub_cnt} subgroups"
                            else:
                                extra = f"{sub_cnt} subgroups in one conjugacy class"
                        else:
                            if cc_cnt > 1:
                                extra = f"{cc_cnt} normal subgroups"
                            else:
                                extra = None
                        ans.append((
                            ov,
                            show(dispname, name),
                            Q,
                            extra))
                        ov = None
        return ans

    def properties(self):
        nilp_str = "yes" if self.nilpotent else "no"
        solv_str = "yes" if self.solvable else "no"
        props = [
            ("Label", self.label),
            ("Order", web_latex(factor(self.order))),
            ("Exponent", web_latex(factor(self.exponent))),
        ]
        if self.number_conjugacy_classes is not None and self.number_conjugacy_classes <= 2000:
            props.append((None, f'<a href="{url_for("abstract.picture", label=self.label)}">{self.image()}</a>'))
        if self.abelian:
            props.append(("Abelian", "yes"))
            if self.simple:
                props.append(("Simple", "yes"))
            try:
                props.append((r"$\card{\operatorname{Aut}(G)}$", web_latex(factor(self.aut_order))))
            except AssertionError:  # timed out
                pass
        else:
            if self.simple:
                props.append(("Simple", "yes"))
            else:
                props.extend([("Nilpotent", nilp_str),
                              ("Solvable", solv_str)])
            props.extend([
                (r"$\card{G^{\mathrm{ab}}}$", web_latex(self.Gab_order_factor()))])
            if self.has_subgroups or self.live():
                cent_order_factored = self.cent_order_factor()
            else:
                cent_order_factored = 0
            if cent_order_factored:
                props.extend([(r"$\card{Z(G)}$",web_latex(cent_order_factored) if cent_order_factored else nc)])
            elif self.center_label:
                props.extend([(r"$\card{Z(G)}$", self.center_label.split(".")[0])])
            else:
                props.extend([(r"$\card{Z(G)}$", "not computed")])

            if self.aut_order is None:
                props.extend([(r"$\card{\mathrm{Aut}(G)}$", "not computed")])
            else:
                try:
                    props.extend([
                        (r"$\card{\mathrm{Aut}(G)}$", web_latex(factor(self.aut_order)))
                    ])
                except AssertionError:  # timed out
                    pass

            if self.outer_order is None:
                props.extend([(r"$\card{\mathrm{Out}(G)}$", "not computed")])
            else:
                try:
                    props.extend([
                        (r"$\card{\mathrm{Out}(G)}$", web_latex(factor(self.outer_order)))
                    ])
                except AssertionError:  # timed out
                    pass

        if not self.live():
            if self.permutation_degree is None:
                props.extend([("Perm deg.", "not computed")])
            else:
                props.extend([("Perm deg.", f"${self.permutation_degree}$")])

        if self.transitive_degree is None:
            props.extend([("Trans deg.", "not computed")])
        else:
            props.extend([("Trans deg.", f"${self.transitive_degree}$")])
        props.append(
            ("Rank", f"${self.rank}$" if self.rank else "not computed"))
        return props

    @lazy_attribute
    def has_subgroups(self):
        if self.live():
            return False
        return self.all_subgroups_known is not None

# below fails to show subgroups when there are some
#       if self.all_subgroups_known: # Not None and equals True
#            return True
#        return False

    @lazy_attribute
    def subgp_paragraph(self):
        charcolor = display_knowl('group.characteristic_subgroup', "Characteristic") + r' subgroups are shown in <span class="chargp">this color</span>.'
        normalcolor = display_knowl('group.subgroup.normal', "Normal") + r' (but not characteristic) subgroups are shown in <span class="normgp">this color</span>.'
        if self.number_subgroups is None:
            if self.number_normal_subgroups is None:
                return " "
            elif self.number_characteristic_subgroups is None:
                return """There are <a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label, normal='yes')) + """ "> """ + str(self.number_normal_subgroups) + " normal</a> subgroups.  <p>"+normalcolor
            else:
                ret_str = """ There are  <a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label, normal='yes')) + """ "> """ + str(self.number_normal_subgroups) + """ normal subgroups</a>"""
                if self.number_characteristic_subgroups < self.number_normal_subgroups:
                    ret_str = ret_str + """ (<a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label, characteristic='yes')) + """ ">""" + str(self.number_characteristic_subgroups) + " characteristic</a>).<p>"+charcolor+"  "+normalcolor
                else:
                    ret_str = ret_str + ", and all normal subgroups are characteristic.<p>"+charcolor
                return ret_str
        elif self.number_normal_subgroups < self.number_subgroups:
            ret_str = "There are " + str(self.number_subgroups) + """ subgroups in <a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label)) + """ "> """ + str(self.number_subgroup_classes) + """ conjugacy classes</a>, <a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label, normal='yes')) + """ "> """ + str(self.number_normal_subgroups) + """ normal</a>"""
        else:
            ret_str = """ There are  <a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label)) + """ "> """ + str(self.number_subgroups) + """ subgroups</a>, all normal"""
        if self.number_characteristic_subgroups < self.number_normal_subgroups:
            ret_str = ret_str + """ (<a href=" """ + str(url_for('.index', search_type='Subgroups', ambient=self.label, characteristic='yes')) + """ ">""" + str(self.number_characteristic_subgroups) + """ characteristic</a>).<p>"""+charcolor+" "+normalcolor
        else:
            ret_str = ret_str + ", and all normal subgroups are characteristic. <p>"+charcolor
        return ret_str

    @lazy_attribute
    def subgroups(self):
        if not self.has_subgroups:
            return None
        subs = {
            subdata["short_label"]: WebAbstractSubgroup(subdata["label"], subdata)
            for subdata in db.gps_subgroups.search({"ambient": self.label})
        }
        if self.subgroup_inclusions_known:
            self.add_layers(subs)
        return subs

    def add_layers(self, subs):
        topord = max(sub.subgroup_order for sub in subs.values())
        top = [z for z in subs.values() if z.subgroup_order == topord][0]
        top.layer = 0
        seen = set()
        layer = [top]
        added_something = True  # prevent data error from causing infinite loop
        while len(seen) < len(subs) and added_something:
            new_layer = []
            added_something = False
            for H in layer:
                if H.contains is not None:
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
                if ser_re.fullmatch(spec_lab):
                    # ser.append((H.subgroup, spec_lab)) # returning right thing?
                    ser.append((H.short_label, spec_lab))

        def sort_ser(p):
            return int(((p[1]).split(sp))[1])

        return [el[0] for el in sorted(ser, key=sort_ser)]

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
        return self.number_subgroup_classes is not None and self.number_subgroup_classes < 100

    @staticmethod
    def _finalize_profile(by_order):
        def sort_key(x):
            # Python 3 won't compare None with strings
            return sum(([c is None, c] for c in x), [])
        for order, subs in by_order.items():
            by_order[order] = sorted(((cnt,) + k for (k, cnt) in subs.items()), key=sort_key, reverse=True)
        return sorted(by_order.items(), key=lambda z: -z[0]) # largest order first

    @lazy_attribute
    def subgroup_profile(self):
        if self.has_subgroups:
            by_order = defaultdict(Counter)
            for s in self.subgroups.values():
                by_order[s.subgroup_order][s.subgroup, s.subgroup_hash, s.subgroup_tex] += s.conjugacy_class_count
            return self._finalize_profile(by_order)

    @lazy_attribute
    def subgroup_autprofile(self):
        if self.has_subgroups and (self.all_subgroups_known or self.complements_known or self.outer_equivalence):
            seen = set()
            by_order = defaultdict(Counter)
            for s in self.subgroups.values():
                if s.aut_label not in seen:
                    by_order[s.subgroup_order][s.subgroup, s.subgroup_hash, s.subgroup_tex] += 1
                    seen.add(s.aut_label)
            return self._finalize_profile(by_order)

    @lazy_attribute
    def normal_profile(self):
        if self.has_subgroups:
            by_order = defaultdict(Counter)
            for s in self.subgroups.values():
                if s.normal:
                    by_order[s.subgroup_order][s.subgroup, s.subgroup_hash, s.subgroup_tex, s.quotient, s.quotient_hash, s.quotient_tex, s.quotient_order] += s.conjugacy_class_count
            if self.normal_counts is not None:
                for d, cnt in zip(self.order.divisors(), self.normal_counts):
                    if cnt and cnt > sum(by_order[d].values()):
                        by_order[d][None, None, None, None, None, None, self.order // d] = cnt - sum(by_order[d].values())
            return self._finalize_profile(by_order)

    @lazy_attribute
    def normal_autprofile(self):
        if self.has_subgroups and (self.all_subgroups_known or self.complements_known or self.outer_equivalence):
            seen = set()
            by_order = defaultdict(Counter)
            for s in self.subgroups.values():
                if s.normal and s.aut_label not in seen:
                    by_order[s.subgroup_order][s.subgroup, s.subgroup_hash, s.subgroup_tex, s.quotient, s.quotient_hash, s.quotient_tex,s.quotient_order] += 1
                    seen.add(s.aut_label)
            return self._finalize_profile(by_order)

    def _display_profile(self, profile, aut):
        def display_profile_line(order, subs):
            l = []
            sep = ", "
            for tup in subs:
                cnt, label, tex = tup[0], tup[1], tup[3]
                if tex is None:
                    tex = "?"
                tup = list(tup[1:])
                if len(tup) == 6:
                    sep = ", &nbsp;&nbsp;"
                if label is None:
                    tup[0] = f"{order}.?"
                # TODO: Deal with the orders where all we know is a count from normal_counts
                if len(tup) > 3:
                    if tup[5] is None:
                        ord_str = "unidentified group of order " + str(tup[6])
                    else:
                        if tup[3] and '?' in tup[5]:
                            ord_str = tup[3]
                        else:
                            ord_str = rf'${tup[5]}$'
                l.append(
                    abstract_group_display_knowl(label, name=f"${tex}$", ambient=self.label, aut=bool(aut), profiledata=tuple(tup))
                    + ("" if len(tup) == 3 else " (%s)" % (ord_str))
                    + (" x " + str(cnt) if cnt > 1 else "")
                )
            return sep.join(l)

        if profile is not None:
            return [(order, display_profile_line(order, subs)) for (order, subs) in profile]

    @cached_method
    def _normal_summary(self):
        if self.normal_index_bound is not None and self.normal_index_bound != 0:
            return f"All normal subgroups of index up to {self.normal_index_bound} or order up to {self.normal_order_bound} are shown. <br>"
        return ""

    @lazy_attribute
    def subgroup_order_bound(self):
        if self.subgroup_index_bound == 0:
            return 1
        return self.order // self.subgroup_index_bound

    @cached_method
    def _subgroup_summary(self, in_profile):
        if self.subgroup_index_bound != 0:
            if self.normal_index_bound is None or self.normal_index_bound == 0:
                return f"All subgroup of index up to {self.subgroup_index_bound} (order at least {self.subgroup_order_bound}) are shown, as well as all normal subgroups of any index. <br>"
            elif self.normal_order_bound != 0:
                return f"All subgroup of index up to {self.subgroup_index_bound} (order at least {self.subgroup_order_bound}) are shown, as well as normal subgroups of index up to {self.normal_index_bound} or of order up to {self.normal_order_bound}. <br>"
            else:
                return f"All subgroup of index up to {self.subgroup_index_bound} (order at least {self.subgroup_order_bound}) are shown, as well as normal subgroups of index up to {self.normal_index_bound}. <br>"
            # TODO: add more verbiage here about Sylow subgroups, maximal subgroups, explain when we don't know subgroups up to automorphism/conjugacy, etc
        return ""

    def get_profile(self, sub_all, sub_aut):
        if sub_all == "subgroup":
            if sub_aut:
                profile = self.subgroup_autprofile
                desc = "Classes of subgroups up to automorphism"
            else:
                profile = self.subgroup_profile
                desc = "Classes of subgroups up to conjugation"
            summary = self._subgroup_summary(in_profile=True)
        else:
            if sub_aut:
                profile = self.normal_autprofile
                desc = "Normal subgroups up to automorphism (quotient in parentheses)"
            else:
                profile = self.normal_profile
                desc = "Normal subgroups (quotient in parentheses)"
            summary = self._normal_summary()
        if profile is None:
            summary = "not computed"
        return self._display_profile(profile, bool(sub_aut)), desc, summary

    @cached_method
    def diagram_count(self, sub_all, sub_aut, limit=0):
        # The number of subgroups shown in the diagram of this type; sub_all can be "subgroup" or "normal" and sub_aut can be "aut" or ""
        # If limit is nonzero, then a count of 0 is returned (indicating that the diagram should not be shown) when there would be more nodes than the limit.
        if not self.subgroup_inclusions_known:
            return 0

        def impose_limit(n):
            if limit != 0 and n > limit:
                return 0
            return n
        if sub_all == "subgroup":
            if sub_aut:
                subs = [H for H in self.subgroups.values() if (H.quotient_order <= self.subgroup_index_bound) or (self.subgroup_index_bound == 0)]
                if any(H.aut_label is None or H.diagramx is None for H in subs):
                    # We don't know subgroups up to automorphism or can't lay out the subgroups
                    return 0
                return impose_limit(len(set(subs)))
            else:
                if self.outer_equivalence:
                    # We don't know subgroups up to conjugacy
                    return 0
                subs = [H for H in self.subgroups.values() if (H.quotient_order <= self.subgroup_index_bound) or (self.subgroup_index_bound == 0)]
                if any(H.diagramx is None for H in subs):
                    # No layout computed
                    return 0
                return impose_limit(len(subs))
        else:
            subs = [H for H in self.subgroups.values() if H.normal]
            if sub_aut:
                if any(H.aut_label is None or H.diagramx is None for H in subs):
                    # We don't know subgroups up to automorphism or can't lay out the subgroups
                    return 0
                return impose_limit(len({H.aut_label for H in subs}))
            else:
                if self.outer_equivalence or any(H.diagramx is None for H in subs):
                    # We don't know subgroups up to conjugacy or can't lay out subgroups
                    return 0
                return impose_limit(len(subs))

    def get_diagram_info(self, sub_all, sub_aut, limit=0):
        summary = ""
        if sub_all == "subgroup":
            if sub_aut:
                desc = "Classes of subgroups up to automorphism"
            else:
                desc = "Classes of subgroups up to conjugation"
            summary = self._subgroup_summary(in_profile=False)
        else:
            if sub_aut:
                desc = "Normal subgroups up to automorphism"
            else:
                desc = "Normal subgroups"
            # I don't think the following can be nonempty in the current data, since we stopped computing inclusions before we cut the middle of the normal lattice out, but it's included for completeness
            summary = self._normal_summary()
        count = 0
        if not self.subgroup_inclusions_known:
            summary = "No diagram available: inclusions not computed"
        elif self.outer_equivalence and not sub_aut:
            summary = "No diagram available: subgroups only stored up to automorphism"
        else:
            count = self.diagram_count(sub_all, sub_aut, limit=limit)
            if count == 0:
                if self.diagram_count(sub_all, sub_aut, limit=0) > 0:
                    url = url_for(f".{sub_all}_{sub_aut}diagram", label=self.label)
                    summary = f'There are too many subgroups to show.\n<a href="{url}">See a full page version of the diagram</a>.\n'
                else:
                    summary = "No diagram available"
        return desc, summary, count

    def diagram_classes(self):
        # Which combinations of subgroup/normal and conj/aut have a diagram
        # Note that it's possible that the only diagrams "shown" will be for cases where there's a link to a fullpage version.
        classes = []
        for sub_all in ["subgroup", "normal"]:
            for sub_aut in ["", "aut"]:
                if self.diagram_count(sub_all, sub_aut) > 0:
                    classes.append(f"{sub_all}_{sub_aut}diagram")
        return " ".join(classes)

    @cached_method
    def subgroup_lattice(self, sub_all, sub_aut):
        if not self.subgroup_inclusions_known:
            raise RuntimeError("Subgroup inclusions not known")
        if self.outer_equivalence and not sub_aut:
            raise RuntimeError("Subgroups not known up to conjugacy")
        subs = self.subgroups
        sib = self.subgroup_index_bound
        by_aut = defaultdict(set)
        if sub_all == "subgroup":
            def test(H):
                if sib == 0 or H.quotient_order <= sib:
                    by_aut[H.aut_label].add(H.short_label)
                    return True

            def contains(G):
                return [h for h in G.contains if test(subs[h])]
        else:
            def test(H):
                if H.normal:
                    by_aut[H.aut_label].add(H.short_label)
                    return True

            def contains(G):
                return [h for h in G.normal_contains if test(subs[h])]
        nodes = [H for H in subs.values() if test(H)]
        if self.outer_equivalence or not sub_aut:
            edges = [[h, G.short_label]
                     for G in nodes
                     for h in contains(G)]
        else:
            # Subgroups are stored up to conjugacy but we want them up to automorphism.
            # We pick a rep from each autjugacy class
            aut_rep = {}
            for aut_label, short_labels in by_aut.items():
                # In the standard labeling, there will be exactly one ending in .a1
                short_labels = list(short_labels)
                for short_label in short_labels:
                    if short_label.endswith(".a1"):
                        aut_rep[aut_label] = short_label
                        break
                else:
                    # We just pick the first one; I don't think this case should happen
                    aut_rep[aut_label] = short_labels[0]
            edges = set() # avoid multiedges; this may not be the desired behavior
            for G in nodes:
                glabel = aut_rep[G.aut_label]
                for h in contains(G):
                    hlabel = aut_rep[subs[h].aut_label]
                    edges.add((hlabel, glabel))
            nodes = [subs[short_label] for short_label in aut_rep.values()]
            edges = [list(edge) for edge in edges]
        return [nodes, edges]

    # The following layout elements go in different places depending on whether
    # the subgroup diagram is wide or not, so they are abstracted here

    def fullpage_links(self, getpositions=False):
        s = ""
        for sub_all in ["subgroup", "normal"]:
            for sub_aut in ["", "aut"]:
                cls = f'{sub_all}_{sub_aut}diagram'
                s += f'<div class="{cls}">\n'
                url = url_for(f'.{cls}', label=self.label)
                s += f'<a href="{url}">See a full page version of the diagram</a>\n</div>\n'
        return s

    def diagramorder_links(self):
        s = ""
        s += '<div>\n For the  default diagram, subgroups are sorted vertically by the number of prime divisors (counted with multiplicity) in  their orders. <br>  To see  subgroups sorted vertically by order instead, check this box.'
        s += '<input type="checkbox" id="orderForHeight" onchange="toggleheight()" />\n</div>\n'
        return s

    def sub_info_area(self):
        s = '<h4>Subgroup information</h4>\n'
        s += '<div class="selectedsub">\n'
        s += 'Click on a subgroup in the diagram to see information about it.\n'
        s += '</div>\n'
        return s

    def canvas(self, width, height):
        s = f'<canvas id="subdiagram" width="{width}" height="{height}">\n'
        s += 'Sorry, your browser does not support the subgroup diagram.\n'
        s += '</canvas>\n'
        return s

    @lazy_attribute
    def conjugacy_classes(self):
        if self.live():
            if isinstance(self.G, LiveAbelianGroup):
                cl = [
                    WebAbstractConjClass(self.label, f"{m}?", {
                        "size": ZZ(1),
                        "order": m})
                    for m in self.G.element_orders()
                ]
            else:
                # We just record size, order, and a representative
                cl = [
                    WebAbstractConjClass(self.label, f"{c.Representative().Order()}?", {
                        "size": ZZ(c.Size()),
                        "order": ZZ(c.Representative().Order()),
                        "representative": c.Representative()})
                    for c in self.G.ConjugacyClasses()
                ]
            # no divisions or autjugacy classes
            return cl
        cl = [
            WebAbstractConjClass(self.label, ccdata["label"], ccdata)
            for ccdata in db.gps_conj_classes.search({"group_order": self.order, "group_counter": self.counter})
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
    def has_nontrivial_schur_character(self):
        return any(chtr.schur_index > 1 for chtr in self.rational_characters)

    @lazy_attribute
    def linear_degrees_table(self):
        knowls = [("group.min_faithful_linear", "Irreducible"),
                  ("group.min_faithful_linear", "Arbitrary")]
        names = [["irrC_degree", "irrR_degree", "irrQ_dim"], ["linC_degree", "linR_degree", "linQ_dim"]]
        data = [[getattr(self, c, None) for c in row] for row in names]
        if all(all(c is None for c in row) for row in data):
            return f"<p>{display_knowl('group.min_faithful_linear', 'Minimal degrees of linear representations')} for this group have not been computed</p>"

        def display(c):
            if c is None:
                return "not computed"
            elif c == -1:
                return "none"
            else:
                return str(c)
        table = "".join(['  <tr>\n'
                         + f'    <td class="border-right">{display_knowl(knowl, disp)}</td>\n'
                         + ''.join([f'    <td>{display(c)}</td>\n' for c in row])
                         + '  </tr>\n'
                         for (knowl, disp), row in zip(knowls, data)])
        table = fr"""<h3>{display_knowl('group.min_faithful_linear', 'Minimal degrees of faithful linear representations')}</h3>
<table class="ntdata centered nobottom">
  <thead>
    <tr>
      <th class="border-right"></th>
      <th>Over $\mathbb{{C}}$</th>
      <th>Over $\mathbb{{R}}$</th>
      <th>Over $\mathbb{{Q}}$</th>
    </tr>
  </thead>
{table}
</table>"""
        return table

    @lazy_attribute
    def maximal_subgroup_of(self):
        # Could show up multiple times as non-conjugate maximal subgroups in the same ambient group
        # So we should eliminate duplicates from the following list
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
        # So we should eliminate duplicates from the following list
        return [
            WebAbstractSupergroup(self, "quo", supdata["label"], supdata)
            for supdata in db.gps_subgroups.search(
                {"quotient": self.label, "minimal_normal": True},
                sort=["ambient_order", "ambient"],
            )
        ]

    def most_product_expressions(self):
        return max(1, len(self.semidirect_products), len(self.nonsplit_products), len(self.as_aut_gp))

    @lazy_attribute
    def display_direct_product(self):
        # Need to pick an ordering
        # return [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]
        if not self.direct_product or self.direct_factorization is None:
            return False  # signal that it is a direct product, but we don't have the data
        else:
            C = dict(self.direct_factorization)
            # We can use the list of subgroups to get the latex
            latex_lookup = {}
            sort_key = {}
            for sub in self.subgroups.values():
                slab = sub.subgroup # Might be None
                if slab in C:
                    latex_lookup[slab] = abstract_group_display_knowl(slab, name='$'+sub.subgroup_tex_parened+'$')
                    sort_key[slab] = (
                        not sub.abelian,
                        sub.subgroup_order.is_prime_power(get_data=True)[0]
                        if sub.abelian
                        else sub.subgroup_order,
                        sub.subgroup_order,
                    )
                    if len(latex_lookup) == len(C):
                        break
            # What if the subgroup doesn't have information?
            for c in C:
                if c not in sort_key:
                    cgroup = WebAbstractGroup(c)
                    sort_key[c] = (
                        not cgroup.abelian,
                        cgroup.order.is_prime_power(get_data=True)[0]
                        if cgroup.abelian
                        else cgroup.order,
                        cgroup.order,
                    )
                    latex_lookup[c] = abstract_group_display_knowl(slab, name='$'+sub_paren(cgroup.tex_name)+'$')
            df = sorted(self.direct_factorization, key=lambda x: sort_key[x[0]])
            s = r" $\, \times\, $ ".join(
                "%s%s" % (latex_lookup[label], r" ${}^%s$ " % e if e > 1 else "")
                for (label, e) in df
            )
        return s

    @lazy_attribute
    def display_wreath_product(self):
        if not self.has_subgroups or not self.wreath_product:
            return None
        wpd = self.wreath_data
        from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
        if len(wpd) == 3:
            [A, B, nt] = wpd
            # try to guess actual group for A from the latex
            cn_re = re.compile(r'^C_\{?(\d+)\}?$')
            cn_match = cn_re.match(A)
            if cn_match:
                order = cn_match.group(1)
                Agroup = db.gps_groups.lucky({'order':int(order), 'cyclic':True})
                A = Agroup['label']
                A = abstract_group_display_knowl(Agroup['label'])
            elif A == 'S_3':
                A = abstract_group_display_knowl('6.1')
            else:
                A = rf'${sub_paren(A)}$ '
            B = sub_paren(B)
            B = transitive_group_display_knowl(nt, rf'${B}$')
        else:
            [A, B, C, nt] = wpd
            allsubs = self.subgroups.values()
            A = [z for z in allsubs if z.short_label == A][0]
            A = abstract_group_display_knowl(A.subgroup, name='$'+A.subgroup_tex_parened+'$')
            B = [z for z in allsubs if z.short_label == B][0]
            B = B.subgroup_tex_parened
            B = transitive_group_display_knowl(nt, rf'${B}$')
        return A+r"$\ \wr\ $" + B

    @lazy_attribute
    def semidirect_products(self):
        if not self.has_subgroups:
            return None
        semis = []
        subs = defaultdict(list)
        for sub in self.subgroups.values():
            if sub.normal and sub.split and not sub.direct and sub.subgroup is not None and sub.quotient is not None and sub.subgroup_order != 1 and sub.quotient_order != 1:
                pair = (sub.subgroup, sub.quotient)
                if pair not in subs:
                    semis.append(sub)
                subs[pair].append(sub.short_label)
        semis.sort(key=product_sort_key)
        for V in subs.values():
            V.sort(key=label_sortkey)
        return [(sub, len(subs[sub.subgroup, sub.quotient]), subs[sub.subgroup, sub.quotient]) for sub in semis]

    @lazy_attribute
    def nonsplit_products(self):
        if not self.has_subgroups:
            return None
        nonsplit = []
        subs = defaultdict(list)
        for sub in self.subgroups.values():
            if sub.normal and not sub.split:
                pair = (sub.subgroup, sub.quotient)
                if pair not in subs:
                    nonsplit.append(sub)
                subs[pair].append(sub.short_label)
        nonsplit.sort(key=product_sort_key)
        for V in subs.values():
            V.sort(key=label_sortkey)
        return [(sub, len(subs[sub.subgroup, sub.quotient]), subs[sub.subgroup, sub.quotient]) for sub in nonsplit]

    @lazy_attribute
    def as_aut_gp(self):
        return [(rec['label'], fr"\Aut({rec['tex_name']})") for rec in db.gps_groups.search({"aut_group": self.label}, ["label", "tex_name"]) if rec['label'] != self.label]

    # Figuring out the subgroup count for an autjugacy class might not be stored
    # directly.  We do them all at once.  If we only computed up to aut
    # return empty Counter since we don't need this.
    # Output is a Counter of aut_labels and counts
    @lazy_attribute
    def aut_class_counts(self):
        counts = Counter()
        if self.outer_equivalence:
            return counts
        subs = self.subgroups
        for s in subs.values():
            counts[s.aut_label] += s.count
        return counts

    @lazy_attribute
    def tex_images(self):
        all_tex = list({H.subgroup_tex for H in self.subgroups.values()}) + ["?"]
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
        # Dimensions that occur for either a rational or complex irreducible character
        return sorted(
            set([d for (d,cnt) in self.irrep_stats]
                + [d for (d,cnt) in self.ratrep_stats]))

    @lazy_attribute
    def irrep_stats(self):
        # This should be cached for groups coming from the database, so this is only used for live groups
        return [(ZZ(d), ZZ(cnt)) for (d, cnt) in self.G.CharacterDegrees()]

    @lazy_attribute
    def irrep_statistics(self):
        D = Counter()
        for d,cnt in self.irrep_stats:
            D[d] = cnt
        return [D[d] for d in self.rep_dims]

    @lazy_attribute
    def ratrep_stats(self):
        # This should be cached for groups coming from the database, so this is only used for live groups
        D = Counter([rep.qdim for rep in self.rational_characters])
        return sorted(D.items())

    @lazy_attribute
    def ratrep_statistics(self):
        D = Counter()
        for d,cnt in self.ratrep_stats:
            D[d] = cnt
        return [D[d] for d in self.rep_dims]

    @lazy_attribute
    def cc_stats(self):
        # This should be cached for groups coming from the database, so this is only used for live groups
        if self.abelian:
            return [[o, 1, cnt] for (o, cnt) in self.order_stats]
        D = Counter([(cc.order, cc.size) for cc in self.conjugacy_classes])
        return sorted((o, s, m) for ((o, s), m) in D.items())

    @lazy_attribute
    def cc_statistics(self):
        D = Counter()
        for (o, s, m) in self.cc_stats:
            D[o] += m
        return sorted(D.items())

    @lazy_attribute
    def div_stats(self):
        # This should be cached for groups coming from the database, so this is only used for live groups
        D = Counter()
        for div in self.conjugacy_class_divisions:
            D[div.order, len(div.classes), div.classes[0].size] += 1
        return sorted((o, s, k, m) for ((o, s, k), m) in D.items())

    @lazy_attribute
    def div_statistics(self):
        D = Counter()
        for (o, s, k, m) in self.div_stats:
            D[o] += m
        return sorted(D.items())

    @lazy_attribute
    def aut_stats(self):
        # This should be cached for groups coming from the database, so this is only used for live groups
        D = Counter()
        for c in self.autjugacy_classes:
            D[c.order, len(c.classes), c.classes[0].size] += 1
        return sorted((o, s, k, m) for ((o, s, k), m) in D.items())

    @lazy_attribute
    def aut_statistics(self):
        if self.aut_stats is None:
            return None
        D = Counter()
        for o, s, k, m in self.aut_stats:
            D[o] += m
        return sorted(D.items())

    @lazy_attribute
    def pcgs(self):
        return self.G.Pcgs()

    @lazy_attribute
    def pcgs_relative_orders(self):
        return [ZZ(c) for c in self.pcgs.RelativeOrders()]

    def pcgs_expos_to_str(self, vec):
        w = []
        e = 0
        # We need to shift the relative orders by 1, since we're multiplying on the previous pass of the for loop
        relords = [1] + self.pcgs_relative_orders[:-1]
        for i, (c, m) in reversed(list(enumerate(zip(vec, relords)))):
            e += c
            if i + 1 in self.gens_used:
                w.append(e)
                e = 0
            else:
                e *= m
        w.reverse()
        s = ""
        for i, c in enumerate(w):
            if c == 1:
                s += var_name(i)
            elif c != 0:
                s += "%s^{%s}" % (var_name(i), c)
        return s

    def pcgs_as_str(self, elt):
        # take an element of a pcgs in GAP and make our string form
        if elt == '':
            return ''
        return self.pcgs_expos_to_str(self.pcgs.ExponentsOfPcElement(elt))

    def decode_as_pcgs(self, code, as_str=False):
        # Decode an element
        vec = []
        if code < 0 or code >= self.order:
            raise ValueError
        for m in self.pcgs_relative_orders:
            c = code % m
            vec.append(c)
            code = code // m
        if as_str:
            # Need to combine some generators
            return self.pcgs_expos_to_str(vec)
        else:
            return self.pcgs.PcElementByExponents(vec)

    def decode_as_perm(self, code, n=None, as_str=False):
        if n is None:
            n = self.representations["Perm"]["d"]
        # code should be an integer with 0 <= m < factorial(n)
        x = SymmetricGroup(n)(Permutations(n).unrank(code))
        if as_str:
            return str(x)
        return x

    def _matrix_coefficient_data(self, rep_type, as_str=False):
        rep_data = self.representations[rep_type]
        sq_flag = False # used later for certain groups
        if rep_type == "Lie":
            rep_data = rep_data[0]
            d = rep_data["d"]
            rep_type = "GLFq"
            fam = rep_data['family']
            if fam in ["AGL", "ASL"]:
                d += 1 # for AGL and ASL the matrices are in GL(d+1,q)
            elif fam in ["CSU", "CU", "GU", "SU", "PSU", "PGU"]:
                sq_flag = True # need q^2 instead of q
            elif fam in ["Spin", "SpinPlus"]:
                d = 2**(d//2)  # d even for SpinPlus, odd for Spin
            elif fam == "SpinMinus":
                d = 2**(d//2)  # d even
                sq_flag = True  # also need q^2 instead of q in this case
        else:
            d = rep_data["d"]
        k = 1
        if rep_type == "GLZ":
            N = rep_data["b"]
            R = r"\Z" if as_str else ZZ
        elif rep_type == "GLFp":
            N = rep_data["p"]
            R = rf"\F_{{{N}}}" if as_str else GF(N)
        elif rep_type == "GLZN":
            N = rep_data["p"]
            R = rf"\Z/{N}\Z" if as_str else Zmod(N)
        elif rep_type == "GLZq":
            N = rep_data["q"]
            R = rf"\Z/{N}\Z" if as_str else Zmod(N)
        elif rep_type == "GLFq":
            q = ZZ(rep_data["q"])
            if sq_flag:
                q = q**2
            if as_str:
                R = rf"\F_{{{q}}}"
            else:
                R = GF(q, modulus="primitive", names=('a',))
                (a,) = R._first_ngens(1)
            N, k = q.is_prime_power(get_data=True)
            if k == 1:
                # Might happen for Lie
                rep_type = "GLFp"
        return R, N, k, d, rep_type

    def decode_as_matrix(self, code, rep_type, as_str=False, LieType=False, ListForm=False, GLFq_logs=None):
        if GLFq_logs is None:
            GLFq_logs = as_str or ListForm
        # ListForm is for code snippet
        if rep_type == "GLZ" and not isinstance(code, int):  # decimal here represents an integer encoding b
            a, b = str(code).split(".")
            code = int(a)
            N = int(b)
            k = 1
            R = ZZ
            rep_data = self.representations[rep_type]
            d = rep_data["d"]
        else:
            R, N, k, d, rep_type = self._matrix_coefficient_data(rep_type)
            if rep_type == "GLFq":
                q = N**k
                R = GF(q, modulus="primitive", names=('a',))
                (a,) = R._first_ngens(1) #need a for powers
        L = ZZ(code).digits(N)

        def pad(X, m):
            return X + [0] * (m - len(L))
        L = pad(L, k * d**2)
        if rep_type == "GLFq":
            L = [R(L[i:i+k]) for i in range(0, k*d**2, k)]
            if GLFq_logs:
                L = [l.log(a) if l != 0 else -1 for l in L]  #-1 represents 0, to distinguish from  a^0
        elif rep_type == "GLZ":
            shift = (N - 1) // 2
            L = [c - shift for c in L]
        if ListForm:
            return L  #as ints representing powers of primitive element if GLFq
        if rep_type == "GLFq" and GLFq_logs:
            x = matrix(ZZ, d, d, L)  #giving powers of alpha (primitive element)
        else:
            x = matrix(R, d, d, L)
        if as_str:
            # for projective families, we add "[ ]"
            if LieType and self.representations["Lie"][0]["family"][0] == "P":
                return r"\left[" + latex(x) + r"\right]"
            if rep_type == "GLFq":  #need to customize latex command for GLFq
                ls = 'l'*d
                st_latex = r'\left(\begin{array}{'+ls+'}'
                for i, entrylog in enumerate(L):
                    if entrylog > 1:
                        st_latex += rf'\alpha^{{{entrylog}}}'
                    elif entrylog == 1:
                        st_latex += r'\alpha'
                    elif entrylog == 0:
                        st_latex += "1"
                    else:
                        st_latex += "0"
                    if (i + 1) % d == 0:
                        st_latex += r' \\ '
                    else:
                        st_latex += ' & '
                st_latex += r'\end{array}\right)'
                return st_latex
            return latex(x)
        return x

    def decode(self, code, rep_type=None, as_str=False):
        if rep_type is None:
            rep_type = self.element_repr_type
        if rep_type == "Perm":
            return self.decode_as_perm(code, as_str=as_str)
        elif rep_type == "PC":
            if code == 0 and as_str:
                return "1"
            return self.decode_as_pcgs(code, as_str=as_str)
        else:
            return self.decode_as_matrix(code, rep_type=rep_type, as_str=as_str, LieType=(rep_type == "Lie"))

    @lazy_attribute
    def pc_code(self):
        return ZZ(self.representations["PC"]["code"])

    @lazy_attribute
    def gens_used(self):
        if self.live():
            return list(range(1, 1 + len(self.G.GeneratorsOfGroup())))
        return self.representations["PC"]["gens"]

    def show_subgroup_flag(self):
        if self.representations.get("Lie"):
            if self.representations["Lie"][0]["family"][0] == "P" and self.order < 2000: # Issue with projective Lie groups
                return False
        return True

    def show_subgroup_generators(self, H):
        if H.subgroup_order == 1:
            return ""
        gens = ", ".join(self.decode(g, as_str=True) for g in H.generators)
        if self.element_repr_type == "Perm":
            return raw_typeset(gens,compress_perm(gens))
        return raw_typeset(gens,"$" + gens + "$")

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

    def presentation(self):
        # We use knowledge of the form of the presentation to construct it manually.
        gens = list(self.PCG.GeneratorsOfGroup())
        pcgs = self.PCG.FamilyPcgs()
        used = [u - 1 for u in sorted(self.gens_used)]  # gens_used is 1-indexed
        rel_ords = [ZZ(p) for p in self.PCG.FamilyPcgs().RelativeOrders()]
        assert len(gens) == len(rel_ords)
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
                        s = var_name(i) + s
                    elif e > 1:
                        s = "%s^{%s}" % (var_name(i), e) + s
                    i -= 1
                    u = used[i]
                    e = 0
            return s

        ngens = len(used)
        for i in range(ngens):
            a = used[i]
            e = prod(rel_ords[a:] if i == ngens - 1 else rel_ords[a: used[i + 1]])
            ae = pcgs.ExponentsOfPcElement(gens[a] ** e)
            if all(x == 0 for x in ae):
                pure_powers.append("%s^{%s}" % (var_name(i), e))
            else:
                rel_powers.append("%s^{%s}=%s" % (var_name(i), e, print_elt(ae)))
            for j in range(i + 1, ngens):
                b = used[j]
                if all(x == 0 for x in pcgs.ExponentsOfCommutator(b + 1, a + 1)):  # back to 1-indexed
                    if not self.abelian:
                        comm.append("[%s,%s]" % (var_name(i), var_name(j)))
                else:
                    v = pcgs.ExponentsOfConjugate(b + 1, a + 1)  # back to 1-indexed
                    relators.append("%s^{%s}=%s" % (var_name(j), var_name(i), print_elt(v)))
        show_gens = ", ".join(var_name(i) for i in range(len(used)))
        if pure_powers or comm:
            rel_powers = ["=".join(pure_powers + comm) + "=1"] + rel_powers
        relators = ", ".join(rel_powers + relators)
        return r"\langle %s \mid %s \rangle" % (show_gens, relators)

    def presentation_raw(self, as_str=True):
        # We use knowledge of the form of the presentation to construct it manually.
        # Need as_str = False for code snippet
        gens = list(self.PCG.GeneratorsOfGroup())
        pcgs = self.PCG.FamilyPcgs()
        used = [u - 1 for u in sorted(self.gens_used)]  # gens_used is 1-indexed
        rel_ords = [ZZ(p) for p in self.PCG.FamilyPcgs().RelativeOrders()]
        assert len(gens) == len(rel_ords)
        pure_powers = []
        rel_powers = []
        comm = []
        relators = []

        def print_elt(vec):
            s = ""
            e = 0
            u = used[-1]
            i = len(used) - 1
            first_pass = True
            for j, (c, p) in reversed(list(enumerate(zip(vec, rel_ords)))):
                e *= p
                e += c
                if j == u:
                    if e == 1:
                        if first_pass:
                            s = var_name(i) + s
                            first_pass = False
                        else:
                            s = var_name(i) + '*' + s

                    elif e > 1:
                        if first_pass:
                            s = "%s^%s" % (var_name(i), e) + s
                            first_pass = False
                        else:
                            s = "%s^%s" % (var_name(i), e) + "*" + s
                    i -= 1
                    u = used[i]
                    e = 0
            return s

        ngens = len(used)
        for i in range(ngens):
            a = used[i]
            e = prod(rel_ords[a:] if i == ngens - 1 else rel_ords[a: used[i + 1]])
            ae = pcgs.ExponentsOfPcElement(gens[a] ** e)
            if all(x == 0 for x in ae):
                pure_powers.append("%s^%s" % (var_name(i), e))
            else:
                rel_powers.append("%s*%s^-%s" % (print_elt(ae),var_name(i), e))
            for j in range(i + 1, ngens):
                b = used[j]
                if all(x == 0 for x in pcgs.ExponentsOfCommutator(b + 1, a + 1)):  # back to 1-indexed
                    if not as_str:  # print commutator out for code snippets
                        comm.append("%s^-1*%s^-1*%s*%s" % (var_name(i), var_name(j), var_name(i), var_name(j)))
                    elif not self.abelian:
                        comm.append("[%s,%s]" % (var_name(i), var_name(j)))
                else:
                    v = pcgs.ExponentsOfConjugate(b + 1, a + 1)  # back to 1-indexed
                    relators.append("%s*%s^-1*%s^-1*%s" % (print_elt(v), var_name(i), var_name(j), var_name(i)))
        if pure_powers or comm:
            rel_powers = [",".join(pure_powers + comm)] + rel_powers
        relators = ", ".join(rel_powers + relators)
        if as_str:
            show_gens = ", ".join(var_name(i) for i in range(len(used)))
            return r"< %s | %s >" % (show_gens, relators)
        else:
            show_gens = ",".join(var_name(i) for i in range(len(used)))  # no space for code snipptes
            return show_gens

    @lazy_attribute
    def representations(self):
        # For live groups
        return {}

    def auto_gens_list(self):
        gens = self.aut_gens
        return [ [ self.decode(gen, as_str=True) for gen in gens[i]] for i in range(len(gens))]

    def auto_gens_data(self):
        gens = self.aut_gens
        gens = [ [ self.decode(gen) for gen in z ] for z in gens]
        auts = [libgap.GroupHomomorphismByImagesNC(self.G,self.G,gens[0],z) for z in gens]
        orders = [z.Order() for z in auts]

        def myisinner(a):
            if a.IsInnerAutomorphism():
                return a.ConjugatorOfConjugatorIsomorphism()
            return ''
        inners = [myisinner(z) for z in auts]
        rep_type = self.element_repr_type
        if rep_type == "PC":
            inners = [self.pcgs_as_str(z) for z in inners]
        elif rep_type == "Perm":
            inners = [str(z) for z in inners]
        else:
            if self.element_repr_type == "GLFq":
                R, N, k, d, rep_type = self._matrix_coefficient_data(self.element_repr_type)
                inners = [matrix(R, d, d, [list(zz) for zz in z3])
                          if z3 != '' else '' for z3 in inners]
            inners = [latex(matrix(z)) if z != '' else '' for z in inners]
        return {'orders': orders, 'inners': inners}

    def representation_line(self, rep_type, skip_head=False):
        # TODO: Add links to searches for other representations when available
        # skip_head is used for matrix groups, where we only include the header for the first
        # or for PC groups if not on the same page
        if rep_type != "PC":
            rdata = self.representations[rep_type]
        if rep_type == "Lie":
            desc = "Groups of " + display_knowl("group.lie_type", "Lie type")
            reps = ", ".join([fr"$\{rep['family']}({rep['d']},{rep['q']})$" for rep in rdata])
            return f'<tr><td>{desc}:</td><td colspan="5">{reps}</td></tr>'
        elif rep_type == "PC":
            pres = self.presentation()
            if not skip_head:  #add copy button in certain cases
                pres_raw = self.presentation_raw()
                pres = raw_typeset(pres_raw,compress_pres(pres))
                if self.live():  # skip code snippet on live group for now
                    return f'<tr><td>{display_knowl("group.presentation", "Presentation")}:<td><td colspan="5">{pres}</td></tr>'
                code_cmd = self.create_snippet('presentation')
            else:
                pres = " $" + pres + "$"
            if self.abelian and not self.cyclic:
                if skip_head:
                    pres = " of the abelian group " + pres
                else:
                    pres = "Abelian group " + pres
            if skip_head:
                return f'{pres} .'  # for repr_strg
            return f'<tr><td>{display_knowl("group.presentation", "Presentation")}:</td><td colspan="5">{pres}</td></tr>{code_cmd}'
        elif rep_type == "Perm":
            gens = ", ".join(self.decode_as_perm(g, as_str=True) for g in rdata["gens"])
            gens = raw_typeset(gens,compress_perm(gens))
            d = rdata["d"]
            if self.live():  # skip code snippet on live group for now
                code_cmd = ""
            else:
                code_cmd = self.create_snippet('permutation')
            if d >= 10:
                gens = f"Degree ${d}$" + gens
            return f'<tr><td>{display_knowl("group.permutation_gens", "Permutation group")}:</td><td colspan="5">{gens}</td></tr>{code_cmd}'
        else:
            # Matrix group
            R, N, k, d, _ = self._matrix_coefficient_data(rep_type, as_str=True)
            gens = ", ".join(self.decode_as_matrix(g, rep_type, as_str=True) for g in rdata["gens"])
            ambient = fr"\GL_{{{d}}}({R})"
            if rep_type == "GLFq":
                Fq = GF(N**k, "alpha")
                poly = latex(Fq.polynomial())
                ambient += fr" = \GL_{{{d}}}(\F_{{{N}}}[\alpha]/({poly}))"
            gens = fr"$\left\langle {gens} \right\rangle \subseteq {ambient}$"
            code_cmd = self.create_snippet(rep_type)
            if skip_head:
                return f'<tr><td></td><td colspan="5">{gens}</td></tr>{code_cmd}'
            else:
                return f'<tr><td>{display_knowl("group.matrix_group", "Matrix group")}:</td><td colspan="10">{gens}</td></tr>{code_cmd}'

    @lazy_attribute
    def transitive_friends(self):
        return list(db.gps_transitive.search({"abstract_label":self.label}, "label"))

    @lazy_attribute
    def stored_representations(self):
        from .main import abstract_group_label_regex
 #       from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl

        def sort_key(typ):
            return ["Lie", "PC", "Perm", "GLZ", "GLFp", "GLFq", "GLZq", "GLZN"].index(typ)

        def truncate_opts(opts, display_opt, link_knowl, show_more_info=True):
            # Should only be called when opts is a nonempty list
            n = len(opts)
            opts = [display_opt(opt) for opt in opts[:4]]
            opts += [""] * (4 - len(opts))
            if n > 4:
                opts.append(link_knowl(self.label, f"all {n}"))
            elif show_more_info:
                opts.append(link_knowl(self.label, "more information"))
            opts = [f"<td>{opt}</td>" for opt in opts]
            return "\n  ".join(opts)

        def content_from_opts(test, opts, construction_type=None, display_opt=None, link_knowl=None, show_more_info=True):
            if test:
                if not opts:
                    return "<td>not computed</td>"
                elif isinstance(opts, str):
                    return f"<td>{opts}</td>"
                else:
                    return truncate_opts(opts, display_opt, link_knowl, show_more_info)
            elif not construction_type:
                return ""
            elif test is False:
                return f'<td colspan="8">not isomorphic to a non-trivial {construction_type}</td>'
            else:
                return "<td>not computed</td>"

        def display_transitive(label):
            return f'<a href="{url_for("galois_groups.by_label", label=label)}">{label}</a>'

        def transitive_expressions_knowl(label, name=None):
            if not name:
                name = f"Transitive permutation group descriptions of {label}"
            return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=trans_expr_data">{name}</a>'

        def display_semidirect(trip):
            sub, count, labels = trip
            out = fr"{sub.knowl(paren=True)} $\,\rtimes\,$ {sub.quotient_knowl(paren=True)}"
            if count > 1:
                out += f" ({count})"
            return out

        def semidirect_expressions_knowl(label, name=None):
            if not name:
                name = f"Semidirect product expressions for {label}"
            return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=semidirect_data">{name}</a>'

        def rep_line(head_knowl, head_text, content):
            if content:
                return f"\n<tr>\n  <td>{display_knowl(head_knowl, head_text)}:</td>\n  {content}\n</tr>"
            return ""

        def display_nonsplit(trip):
            sub, count, labels = trip
            out = fr"{sub.knowl(paren=True)}&nbsp;.&nbsp;{sub.quotient_knowl(paren=True)}"
            if count > 1:
                out += f" ({count})"
            return out

        def nonsplit_expressions_knowl(label, name=None):
            if not name:
                name = f"Nonsplit product expressions for {label}"
            return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=nonsplit_data">{name}</a>'

        def display_as_aut(pair):
            label, disp = pair
            return f'<a href="{url_for(".by_label", label=label)}">${disp}$</a>'

        def autgp_expressions_knowl(label, name=None):
            if not name:
                name = f"Expressions for {label} as an automorphism group"
            return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args={label}&func=aut_data">{name}</a>'

        def show_reps(rtype):
            if rtype == "direct":
                return rep_line(
                    "group.direct_product",
                    "Direct product",
                    content_from_opts(self.direct_product,
                                      self.display_direct_product,
                                      "direct product"))
            elif rtype == "transitive":
                if not abstract_group_label_regex.fullmatch(self.label):
                    return ""
                return rep_line(
                    "group.permutation_representation",
                    "Transitive group",
                    content_from_opts(self.transitive_friends,
                                      self.transitive_friends,
                                      False, # hide if not present
                                      display_transitive,
                                      transitive_expressions_knowl))
            elif rtype == "semidirect":
                return rep_line(
                    "group.semidirect_product",
                    "Semidirect product",
                    content_from_opts(self.semidirect_product and not self.abelian,
                                      self.semidirect_products,
                                      "semidirect product",
                                      display_semidirect,
                                      semidirect_expressions_knowl))
            elif rtype == "wreath":
                return rep_line(
                    "group.wreath_product",
                    "Trans. wreath product",
                    content_from_opts(self.wreath_product,
                                      self.display_wreath_product,
                                      "transitive wreath product"))
            elif rtype == "nonsplit":
                return rep_line(
                    "group.nonsplit_product",
                    "Non-split product",
                    content_from_opts(self.nonsplit_products,
                                      self.nonsplit_products,
                                      False, # hide if no expressions
                                      display_nonsplit,
                                      nonsplit_expressions_knowl))
            elif rtype == "aut":
                return rep_line(
                    "group.automorphism",
                    "Aut. group",
                    content_from_opts(self.as_aut_gp,
                                      self.as_aut_gp,
                                      False, # hide if no expressions
                                      display_as_aut,
                                      autgp_expressions_knowl,
                                      show_more_info=False))

        output_strg = ""
        if self.live():
            if self.solvable:
                output_strg += self.representation_line("PC")
            output_strg += show_reps("transitive")
        else:
            skip_head = False
            for rep_type in sorted(self.representations, key=sort_key):
                output_strg += "\n" + self.representation_line(rep_type, skip_head)
                if rep_type.startswith("GL"):
                    # a matrix group, so we omit the "Matrix group" head in the future
                    skip_head = True
            output_strg += show_reps("transitive")
            output_strg += show_reps("direct")
            output_strg += show_reps("semidirect")
            output_strg += show_reps("wreath")
            output_strg += show_reps("nonsplit")
        output_strg += show_reps("aut")
        if output_strg == "":  #some live groups have no constructions
            return "data not computed"
        return output_strg

    def is_null(self):
        return self._data is None

    # TODO if prime factors get large, use factors in database
    def order_factor(self):
        return latex(factor(self.order))

    # automorphism group
    def show_aut_group(self):
        try:
            if self.aut_group is None:
                if self.aut_order is None:
                    return r"not computed"
                else:
                    return f"Group of order {pos_int_and_factor(self.aut_order)}"
            else:
                if self.aut_order is None:
                    return r"not computed"
                else:
                    url = url_for(".by_label", label=self.aut_group)
                    return f'<a href="{url}">${group_names_pretty(self.aut_group)}$</a>, of order {pos_int_and_factor(self.aut_order)}'
        except AssertionError:  # timed out
            return r"$\textrm{Computation timed out}$"

    # TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return latex(factor(self.aut_order))

    def aut_gens_flag(self): #issue with Lie type when family is projective, auto stored as permutations often
        if self.aut_gens is None:
            return False
        if self.element_repr_type == "Lie":
            if self.representations["Lie"][0]["family"][0] == "P":
                return False
        if self.element_repr_type in ["GLZN", "GLZq", "Lie", "GLFq", "GLFp"]:
            return False
        return True

    # outer automorphism group
    def show_outer_group(self):
        try:
            if self.outer_group is None:
                if self.outer_order is None:
                    return r"$\textrm{not computed}$"
                else:
                    return f"Group of order {pos_int_and_factor(self.outer_order)}"
            else:
                url = url_for(".by_label", label=self.outer_group)
                return f'<a href="{url}">${group_names_pretty(self.outer_group)}$</a>, of order {pos_int_and_factor(self.outer_order)}'
        except AssertionError:  # timed out
            return r"$\textrm{Computation timed out}$"

    # TODO if prime factors get large, use factors in database
    def out_order_factor(self):
        return latex(factor(self.outer_order))

    def perm_degree(self):
        if self.permutation_degree is None:
            return r"not computed"
        else:
            return f"${self.permutation_degree}$"

    def trans_degree(self):
        if self.transitive_degree is None:
            return r"not computed"
        else:
            return f"${self.transitive_degree}$"

    def live_composition_factors(self):
        from .main import url_for_label
        basiclist = []
        if isinstance(self.G, LiveAbelianGroup) or self.solvable:
            theorder = ZZ(self.G.Order()).factor()
            # We could work harder here to get small group labels for
            # these cyclic groups, but why bother?  This way, the lookup
            # is only done for one of them, and only if the user clicks
            # on the link
            basiclist = [(url_for(".by_abelian_label", label=z[0]),
                "C_{%d}" % z[0],
                "" if z[1] == 1 else "<span style='font-size: small'> x %d</span>" % z[1]
                )
                for z in theorder]

        # The only non-solvable option with order a multiple of 128
        # below 2000 is ...
        elif ZZ(self.G.Order()) == 1920:
            basiclist = [
                (url_for(".by_abelian_label", label=2), "C_2", "<span style='font-size: small'> x 5</span>"),
                (url_for_label("60.5"), "A_5", "")]
        if not basiclist:
            return "data not computed"
        return ", ".join('<a href="%s">$%s$</a>%s' % z for z in basiclist)

    def show_composition_factors(self):
        if self.live():
            return self.live_composition_factors()
        if self.order == 1:
            return "none"
        CF = Counter(self.composition_factors)
        display = {
            rec["label"]: '$'+rec["tex_name"]+'$'
            for rec in db.gps_groups.search(
                {"label": {"$in": list(set(CF))}}, ["label", "tex_name"]
            )
        }
        from .main import url_for_label

        def exp(n):
            #return "" if n == 1 else f" ({n})"
            return "" if n == 1 else f"<span style='font-size: small'> x {n}</span>"

        return ", ".join(
            f'<a href="{url_for_label(label)}">{display.get(label,label)}</a>{exp(e)}'
            for (label, e) in CF.items()
        )

    # special subgroups

    #first function is if we only know special subgroups as abstract groups
    def special_subs_label(self,label):
        info = db.gps_groups.lucky({"label": label})
        if info is None:
            return label
        else:
            return f"${info['tex_name']}$"

    def cent(self):
        return self.special_search("Z")

    def cent_label(self):
        cent = self.cent()
        if cent:
            return self.subgroups[self.cent()].knowl()
        return None

    def cent_order_factor(self):
        if self.live():
            ZGord = ZZ(self.G.Center().Order())
        else:
            cent = self.cent()
            if not cent:
                return None
            ZGord = self.order // ZZ(cent.split(".")[0])
        if ZGord == 1: # factor(1) causes problems
            return 1
        return ZGord.factor()

    def comm(self):
        return self.special_search("D")

    def comm_label(self):
        comm = self.comm()
        if comm:
            return self.subgroups[comm].knowl()
        return nc

    def abelian_quot(self):
        return abelian_gp_display(self.smith_abelian_invariants)

    def abelian_quot_primary(self):
        return abelian_gp_display(self.primary_abelian_invariants)
        return r" \times ".join(
            ("C_{%s}^{%s}" % (q, e) if e > 1 else "C_{%s}" % q)
            for (q, e) in Counter(self.primary_abelian_invariants).items()
        )

    def abelianization_label(self):
        return ".".join(str(m) for m in self.smith_abelian_invariants)

    def Gab_order_factor(self):
        return ZZ.prod(self.primary_abelian_invariants).factor()  # better to use the partial factorization

    def fratt(self):
        return self.special_search("Phi")

    def fratt_label(self):
        fratt = self.fratt()
        if fratt:
            return self.subgroups[fratt].knowl()
        return None

    def gen_noun(self):
        if self.rank == 1:
            return "generators"
        elif self.rank == 2:
            return "generating pairs"
        elif self.rank == 3:
            return "generating triples"
        elif self.rank == 4:
            return "generating quadruples"
        elif not self.rank:
            return "generating tuples"
        else:
            return f"generating {self.rank}-tuples"

    def repr_strg(self, other_page=False):
        # string to say where elements of group live
        # other_page is if the description is not on main page for the group (eg. automorphism group generators)
        rep_type = self.element_repr_type
        data = self.representations.get(rep_type)
        if rep_type == "Lie":  # same whether from main page or not
            fam, d, q = data[0]["family"], data[0]["d"], data[0]["q"]
            if fam[0] == "P":   # note about matrix parentheses
                return fr"Elements of the group are displayed as equivalence classes (represented by square brackets) of matrices in $\{fam[1:]}({d},{q})$."
            else:
                return fr"Elements of the group are displayed as matrices in $\{fam}({d},{q})$."
        elif rep_type == "Perm":
            d = data["d"]
            return f"Elements of the group are displayed as permutations of degree {d}."
        elif rep_type == "PC":
            rep_str = "Elements of the group are displayed as words in the presentation"
            if other_page:
                return rep_str + self.representation_line("PC", skip_head=True)
            else:
                return rep_str + " generators from the presentation above."
        elif rep_type in ["GLFp", "GLFq", "GLZN", "GLZq", "GLZ"]:
            d = data["d"]
            if rep_type == "GLFp":
                R = fr"\F_{{{data['p']}}}"
            elif rep_type == "GLFq":
                R = fr"\F_{{{data['q']}}}"
            elif rep_type == "GLZN":
                R = fr"\Z/{{{data['p']}}}\Z"
            elif rep_type == "GLZq":
                R = fr"\Z/{{{data['q']}}}\Z"
            else:
                R = r"\Z"
            return fr"Elements of the group are displayed as matrices in $\GL_{{{d}}}({R})$."
        else: # if not any of these types
            return ""

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

    def image(self):
        if self.cc_stats is not None and self.number_conjugacy_classes <= 2000:
            circles = []
            for order, size, num_classes in self.cc_stats:
                circles.extend([(size, order)] * num_classes)
            circles, R = find_packing(circles)
            R = R.ceiling()
            circles = "\n".join(
                f'<circle cx="{x}" cy="{y}" r="{rad}" fill="rgb({r},{g},{b})" />'
                for (x, y, rad, (r, g, b)) in circles
            )
        else:
            R = 1
            circles = ""
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-{R} -{R} {2*R} {2*R}" width="200" height="150">\n{circles}</svg>'

    def create_snippet(self,item):
        # mimics jinja macro place_code to be included in Constructions section
        # this is specific for embedding in a table. eg. we need to replace "<" with "&lt;"
        code = self.code_snippets()
        snippet_str = "" # initiate new string
        if code[item]:
            for L in code[item]:
                if isinstance(code[item][L],str):
                    lines = code[item][L].split('\n')[:-1] if '\n' in code[item][L] else [code[item][L]]
                    lines = [line.replace("<", "&lt;").replace(">", "&gt;") for line in lines]
                else:   # not currently used in groups
                    lines = code[item][L]
                prompt = code['prompt'][L] if 'prompt' in code and L in code['prompt'] else L
                class_str = " ".join([L,'nodisplay','codebox'])
                col_span_val = '"6"'
                for line in lines:
                    snippet_str += f"""
<tr>
    <td colspan={col_span_val}>
        <div class="{class_str}">
            <span class="raw-tset-copy-btn" onclick="copycode(this)"><img alt="Copy content" class="tset-icon"></span>
            <span class="prompt">{prompt}:&nbsp;</span><span class="code">{line}</span>
            <div style="margin: 0; padding: 0; height: 0;">&nbsp;</div>
        </div>
    </td>
</tr>
"""
        return snippet_str

    @cached_method
    def code_snippets(self):
        if self.live():
            return
        _curdir = os.path.dirname(os.path.abspath(__file__))
        code = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)
        code['show'] = { lang:'' for lang in code['prompt'] }
        if "PC" in self.representations:
            gens = self.presentation_raw(as_str=False)
            pccodelist = self.representations["PC"]["pres"]
            pccode = self.representations["PC"]["code"]
            ordgp = self.order
            used_gens = create_gens_list(self.representations["PC"]["gens"])
            gap_assign = create_gap_assignment(self.representations["PC"]["gens"])
            magma_assign = create_magma_assignment(self)
        else:
            gens, pccodelist, pccode, ordgp, used_gens, gap_assign, magma_assign = None, None, None, None, None, None, None
        if "Perm" in self.representations:
            rdata = self.representations["Perm"]
            perms = ", ".join(self.decode_as_perm(g, as_str=True) for g in rdata["gens"])
            deg = rdata["d"]
        else:
            perms, deg = None, None

        if "GLZ" in self.representations:
            nZ = self.representations["GLZ"]["d"]
            LZ = [self.decode_as_matrix(g, "GLZ", ListForm=True) for g in self.representations["GLZ"]["gens"]]
            LZsplit = [split_matrix_list(self.decode_as_matrix(g, "GLZ", ListForm=True),nZ) for g in self.representations["GLZ"]["gens"]]
        else:
            nZ, LZ, LZsplit = None, None, None
        if "GLFp" in self.representations:
            nFp = self.representations["GLFp"]["d"]
            Fp = self.representations["GLFp"]["p"]
            LFp = [self.decode_as_matrix(g, "GLFp", ListForm=True) for g in self.representations["GLFp"]["gens"]]
            e = libgap.One(GF(Fp))
            LFpsplit = [split_matrix_list_Fp(A,nFp,e) for A in LFp]
        else:
            nFp, Fp, LFp, LFpsplit = None, None, None, None
        if "GLZN" in self.representations:
            nZN = self.representations["GLZN"]["d"]
            N = self.representations["GLZN"]["p"]
            LZN = [self.decode_as_matrix(g, "GLZN", ListForm=True) for g in self.representations["GLZN"]["gens"]]
            LZNsplit = "[" + ",".join(split_matrix_list_ZN(mat, nZN, N) for mat in LZN) + "]"
        else:
            nZN, N, LZN, LZNsplit = None, None, None, None
        if "GLZq" in self.representations:
            nZq = self.representations["GLZq"]["d"]
            Zq = self.representations["GLZq"]["q"]
            LZq = [self.decode_as_matrix(g, "GLZq", ListForm=True) for g in self.representations["GLZq"]["gens"]]
            LZqsplit = "[" + ",".join([split_matrix_list_ZN(self.decode_as_matrix(g, "GLZq", ListForm=True) , nZq, Zq) for g in self.representations["GLZq"]["gens"]]) + "]"
        else:
            nZq, Zq, LZq, LZqsplit = None, None, None, None
# add below for GLFq implementation
        if "GLFq" in self.representations:
            nFq = self.representations["GLFq"]["d"]
            Fq = self.representations["GLFq"]["q"]
            mats = [self.decode_as_matrix(g, "GLFq", ListForm=True) for g in self.representations["GLFq"]["gens"]]
            LFq = ",".join(split_matrix_Fq_add_al(mat, nFq ) for mat in mats)
            LFqsplit = "[" + ",".join(split_matrix_list_Fq(mat, nFq, Fq) for mat in mats) + "]"
        else:
            nFq, Fq, LFq, LFqsplit = None, None, None, None

        data = {'gens' : gens, 'pccodelist': pccodelist, 'pccode': pccode,
                'ordgp': ordgp, 'used_gens': used_gens, 'gap_assign': gap_assign,
                'magma_assign': magma_assign, 'deg': deg, 'perms' : perms,
                'nZ': nZ, 'nFp': nFp, 'nZN': nZN, 'nZq': nZq, 'nFq': nFq,
                'Fp': Fp, 'N': N, 'Zq': Zq, 'Fq': Fq,
                'LZ': LZ, 'LFp': LFp, 'LZN': LZN, 'LZq': LZq, 'LFq': LFq,
                'LZsplit': LZsplit, 'LZNsplit': LZNsplit, 'LZqsplit': LZqsplit,
                'LFpsplit': LFpsplit, 'LFqsplit': LFqsplit, # add for GLFq GAP
        }
        for prop in code:
            for lang in code['prompt']:
                code[prop][lang] = code[prop][lang].format(**data)
        return code

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

# We may get abelian groups which are too large for GAP, so handle them directly
class LiveAbelianGroup():
    def __init__(self, data):
        self.snf = data

    def Order(self):
        return libgap(prod(self.snf))

    def Center(self):
        return LiveAbelianGroup(self.snf)

    def Zquotient(self):
        return libgap.TrivialGroup()

    def DerivedSubgroup(self):
        return libgap.TrivialGroup()

    def Dquotient(self):
        return self

    def FrattiniSubgroup(self):
        # Reduce all exponents by 1
        snf1 = (prod([z[0]**(z[1] - 1) for z in factor(n)]) for n in self.snf)
        snf1 = [z for z in snf1 if z > 1]
        return LiveAbelianGroup(snf1)

    def Phiquotient(self):
        # Make all exponents by 1
        snf1 = [prod(list(ZZ(n).prime_factors())) for n in self.snf]
        return LiveAbelianGroup(snf1)

    def FittingSubgroup(self):
        return self

    def Fquotient(self):
        return libgap.TrivialGroup()

    def RadicalGroup(self):
        return self

    def Rquotient(self):
        return libgap.TrivialGroup()

    def Socle(self):
        # Isomorphic to Frattini quotient
        return self.Phiquotient()

    def Squotient(self):
        # Isomorphic to Frattini subgroup
        return self.FrattiniSubgroup()

    def IsNilpotent(self):
        return True

    def IsSolvable(self):
        return True

    def IsAbelian(self):
        return True

    def IsSupersolvable(self):
        return True

    def IsMonomial(self):
        return True

    def IsSimple(self):
        return (len(self.snf) == 1 and is_prime(self.snf[0]))

    def IsAlmostSimpleGroup(self):
        return False

    def IsPerfect(self):
        return len(self.snf) == 0

    def IsCyclic(self):
        return len(self.snf) < 2

    def NilpotencyClassOfGroup(self):
        return 1 if self.snf else 0

    def DerivedLength(self):
        return 1 if self.snf else 0

    def Exponent(self):
        return self.snf[-1] if self.snf else 1

    def CharacterDegrees(self):
        return [(1,self.Order())]

    def Sylows(self):
        if not self.snf:
            return []
        plist = ZZ(self.snf[-1]).prime_factors()

        def get_sylow(snf, p):
            ppart = [p**z.ord(p) for z in snf]
            return [z for z in ppart if z > 1]
        sylows = [get_sylow(self.snf, p) for p in plist]
        return [LiveAbelianGroup(syl) for syl in sylows]

    def SylowSystem(self):
        return self.Sylows()

    def AbelianInvariants(self):
        primaryl = [factor(z) for z in self.snf]
        primary2 = []
        for f in primaryl:
            primary2.extend([z[0]**z[1] for z in f])
        return sorted(primary2)

    def AutomorphismGroup(self):
        return None

    def RankPGroup(self):
        return len(self.snf)

    def IdGroup(self):
        return libgap.AbelianGroup(self.snf).IdGroup()

    def element_orders(self):
        return sorted(
            lcm(c.additive_order() for c in T)
            for T in cartesian_product_iterator(
                    [Zmod(m) for m in self.snf]))


class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups

    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        s = self.subgroup_tex
        if s is None:
            self.subgroup_tex = "?"
            self.subgroup_tex_parened = "(?)"
        else:
            self.subgroup_tex_parened = s if is_atomic(s) else "(%s)" % s
        if self.normal:
            q = self.quotient_tex
            if q is None:
                self.quotient_tex = "?"
                self.quotient_tex_parened = "(?)"
                if self._data.get("quotient"):
                    tryhard = db.gps_groups.lookup(self.quotient)
                    if tryhard and tryhard["tex_name"]:
                        q = tryhard["tex_name"]
                        self.quotient_tex = q
                        self.quotient_tex_parened = q if is_atomic(q) else "(%s)" % q
            else:
                self.quotient_tex_parened = q if is_atomic(q) else "(%s)" % q
        # Temp fix for a bug in sylow data
        p, k = self.subgroup_order.is_prime_power(get_data=True)
        if self.subgroup_order == 1:
            self.sylow = self.hall = 1
        elif self.subgroup_order.gcd(self.quotient_order) == 1:
            self.hall = self.subgroup_order.radical()
            if k > 0:
                self.sylow = p
            else:
                self.sylow = p
        else:
            self.sylow = self.hall = 0

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
        if not label:
            return None
        for rec in data:
            if rec:
                if rec["label"] == label:
                    return Wtype(label, rec)
                elif 'short_label' in rec and rec.get("short_label") == label:
                    return Wtype(rec["label"], rec)
        # It's possible that the label refers to a small group that is not in the database
        # but that we can create dynamically
        return Wtype(label)

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
        if not S:
            order = self.subgroup_order
            newgroup = WebAbstractGroup('nolabel',
                data={'order': order, 'G': None, 'abelian': self.abelian,'cyclic': self.cyclic,
                      # What if aut_label is set?
                      'aut_group': self.aut_label, 'aut_order': None,
                      'pgroup':len(ZZ(order).abs().factor()) == 1})
            return newgroup
        if self.subgroup_order == 6561:
            gp = WebAbstractGroup(self.subgroup, None)
            if gp.source == "Missing":
                order = self.subgroup_order
                newgroup = WebAbstractGroup('nolabel',
                      data={'order': order, 'G': None, 'abelian': self.abelian,'cyclic': self.cyclic,
                      # What if aut_label is set?
                      'aut_group': self.aut_label, 'aut_order': None, 'sub_missing' : True,
                      'pgroup':len(ZZ(order).abs().factor()) == 1})
                return newgroup
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

    def knowl(self, paren=False):
        from lmfdb.groups.abstract.main import sub_display_knowl
        knowlname = self.subgroup_tex_parened if paren else self.subgroup_tex
        return sub_display_knowl(self.label, name=rf'${knowlname}$')

    def quotient_knowl(self, paren=False):
        # assumes there is a quotient group
        if '?' in self.quotient_tex:
            if self.quotient is None:
                return "(?)"
            else:
                knowlname = WebAbstractGroup(self.quotient).tex_name
        else:
            knowlname = self.quotient_tex_parened if paren else self.quotient_tex
        return abstract_group_display_knowl(self.quotient, name=rf'${knowlname}$')

    def display_quotient(self, subname=None, ab_invs=None):
        if subname is None:
            prefix = quoname = ""
        else:
            quoname = f"$G/{subname}$ "
            prefix = fr"$G/{subname} \simeq$ "
        if hasattr(self, 'quotient') and self.quotient:
            return prefix + abstract_group_display_knowl(self.quotient)
        elif hasattr(self, 'quotient_tex') and self.quotient_tex:
            return prefix + '$'+self.quotient_tex+'$'
        if ab_invs:
            ablabel = '.'.join([str(z) for z in ab_invs])
            url = url_for(".by_abelian_label", label=ablabel)
            return prefix + f'<a href="{url}">$' + abelian_gp_display(ab_invs) + '$</a>'
        if self.quotient_tex is None:
            return quoname + "not computed"
        else:
            return prefix + f'${self.quotient_tex}$'

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
        if self.amb.outer_equivalence is False and self.amb.complements_known is False and self.amb.subgroup_inclusions_known is False:
            return None  #trying to say subgroups not computed up to autjugacy
        else:
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
    table = db.gps_conj_classes
    def __init__(self, group, label, data=None):
        if data is None:
            group_order, group_counter = gp_label_to_cc_data(group)
            data = db.gps_conj_classes.lucky({"group_order": group_order, "group_counter" : group_counter, "label": label})
        WebObj.__init__(self, label, data)
        self.force_repr_elt = False

    # Allows us to use representative from a Galois group
    def force_repr(self, newrep):
        newrep = newrep.replace(' ','')
        self.representative = newrep
        self.force_repr_elt = True

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        force_string = ''
        if self.force_repr_elt:
            force_string = "%7C"+str(self.representative)
        group = cc_data_to_gp_label(self.group_order, self.group_counter)
        return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={group}%7C{self.label}%7Ccomplex{force_string}">{name}</a>'

class WebAbstractDivision():
    def __init__(self, group, label, classes):
        self.group = group
        self.label = label
        self.classes = classes
        self.order = classes[0].order

    def size(self):
        return sum([z.size for z in self.classes])

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        return f'<a title = "{name} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={self.group}%7C{self.label}%7Crational">{name}</a>'

class WebAbstractAutjClass():
    def __init__(self, group, label, classes):
        self.group = group
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
