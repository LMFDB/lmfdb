"""
Web object for an isogeny class of motives of K3 type over a finite field,
i.e. one row of the table ``k3_fq_isog``.

Each class is determined by a polynomial

    P(T) = q + a_1 T + ... + a_22 T^22,   a_{22-i} = sign * a_i,

whose roots lie on the unit circle.  Many columns of the table are not yet
computed for every class, so every display method here has to cope with
missing (null) values.
"""

import re
from collections import Counter

from flask import url_for

from lmfdb import db
from lmfdb.utils import (
    bigint_knowl, display_float, encode_plot, raw_typeset_poly, list_factored_to_factored_poly_otherorder,
)
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
from lmfdb.number_fields.web_number_field import field_pretty

from sage.all import ZZ, QQ, RR, Integer, PolynomialRing, cyclotomic_polynomial, euler_phi, factor, latex
from sage.databases.cremona import cremona_letter_code, class_to_int
from sage.misc.cachefunc import cached_function
from sage.misc.lazy_attribute import lazy_attribute
from sage.plot.all import circle, points


ISOG_TABLE = "k3_fq_isog"
LATTICE_TABLE = "k3_fq_lattices"


class LazyTable:
    """
    A stand-in for ``db.<name>`` that looks the table up only when it is used.

    The tables for this section are not yet present in every copy of the
    database (e.g. devmirror), so we must not access them when the module is
    imported: the rest of the website should keep working without them.
    """
    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        return getattr(getattr(db, self._name), attr)

    def __repr__(self):
        return "LazyTable(%r)" % self._name


isog_table = LazyTable(ISOG_TABLE)
lattice_table = LazyTable(LATTICE_TABLE)


def table_exists(name=ISOG_TABLE):
    return name in db.tablenames


#########################
#   Labels
#########################

# A label q.rho.c.t describes the factorization P = C * P_T into the
# cyclotomic part C, of degree rho (the geometric Picard rank), and the
# transcendental part P_T = q + b_1 T + ... + q T^{2k}, which is palindromic of
# degree 2k = 22 - rho.  The code c is the index of the exponent vector
# (e_1, e_2, e_3, ...) of C = (1 - T)^{e_1} prod_{m > 1} Phi_m^{e_m} among
# those of degree rho, in decreasing lexicographic order.  The code t is
# b_1, ..., b_k in balanced base 26 (a-z are the digits -13, ..., 12, so n = 0),
# padded with leading n's to the smallest common width and concatenated.  When
# rho = 22 the label is q.22.c.  See the knowl k3.fq.lmfdb_label; this is the
# same code as k3fq/labels.py in the repository that computes the data.

LABEL_RE = re.compile(r"^(\d+)\.(\d+)\.([a-z]+)(?:\.([a-z]+))?$")
DEGREE = 22
HALF = 11
LABEL_FORM = "q.rho.c.t"

# The m with phi(m) <= 22, in increasing order (phi(m) >= sqrt(m/2))
CYCLOTOMIC_ORDERS = [m for m in range(1, 2 * DEGREE**2 + 1) if euler_phi(m) <= DEGREE]


def balanced_code(n, width=1):
    """
    ``n`` in balanced base 26, with the letters a-z standing for the digits
    -13, ..., 12, padded with leading n's (the digit 0) to ``width`` letters.
    """
    n = int(n)
    digits = []
    while n or not digits:
        r = (n + 13) % 26 - 13
        digits.append(r)
        n = (n - r) // 26
    digits.extend([0] * (width - len(digits)))
    return "".join(chr(110 + d) for d in reversed(digits))


def balanced_value(code):
    n = 0
    for c in code:
        n = 26 * n + ord(c) - 110
    return ZZ(n)


def transcendental_code(lower):
    """
    The coefficients ``lower`` = [b_1, ..., b_k] in balanced base 26, all
    padded to the smallest common width.
    """
    width = max(len(balanced_code(b)) for b in lower)
    return "".join(balanced_code(b, width) for b in lower)


def transcendental_chunks(code, k):
    """
    The codes of b_1, ..., b_k in the transcendental part ``code`` of a label.
    """
    width = len(code) // k
    return [code[i:i + width] for i in range(0, len(code), width)]


@cached_function
def cyclotomic_tail_counts():
    """
    N[i][k] is the number of exponent vectors of degree k supported on
    CYCLOTOMIC_ORDERS[i:].
    """
    n = len(CYCLOTOMIC_ORDERS)
    N = [[0] * (DEGREE + 1) for _ in range(n + 1)]
    N[n][0] = 1
    for i in range(n - 1, -1, -1):
        ph = euler_phi(CYCLOTOMIC_ORDERS[i])
        for k in range(DEGREE + 1):
            N[i][k] = sum(N[i + 1][k - e * ph] for e in range(k // ph + 1))
    return N


def num_cyclotomic_parts(rho):
    return cyclotomic_tail_counts()[0][rho]


def cyclotomic_index(orders):
    """
    The index of the cyclotomic part prod Phi_m (m in ``orders``, with
    multiplicity) among those of the same degree.
    """
    exps = Counter(orders)
    k = sum(euler_phi(m) for m in orders)
    N = cyclotomic_tail_counts()
    idx = 0
    for i, m in enumerate(CYCLOTOMIC_ORDERS):
        ph = euler_phi(m)
        e = exps[m]
        # vectors agreeing so far but with a larger exponent of Phi_m come first
        for f in range(e + 1, k // ph + 1):
            idx += N[i + 1][k - f * ph]
        k -= e * ph
    return idx


def cyclotomic_orders(rho, idx):
    """
    The sorted list of m (with multiplicity) for the cyclotomic part of degree
    ``rho`` with index ``idx``.
    """
    N = cyclotomic_tail_counts()
    orders = []
    k = rho
    for i, m in enumerate(CYCLOTOMIC_ORDERS):
        ph = euler_phi(m)
        for e in range(k // ph, -1, -1):
            n = N[i + 1][k - e * ph]
            if idx < n:
                break
            idx -= n
        orders.extend([m] * e)
        k -= e * ph
    return orders


def cyclotomic_product(orders):
    """
    prod Phi_m over ``orders``, normalized to have constant term 1.
    """
    R = PolynomialRing(ZZ, "T")
    C = R(1)
    for m in orders:
        f = R(cyclotomic_polynomial(m).list())
        C *= f if f[0] == 1 else -f
    return C


def split_label(label):
    """
    Returns the tuple (q, rho, c, codes) for a label q.rho.c.t, where codes is
    the list of the codes of b_1, ..., b_k in t (empty when rho = 22).
    """
    q, rho, c, t = LABEL_RE.fullmatch(label).groups()
    q, rho = int(q), int(rho)
    return q, rho, c, transcendental_chunks(t, (DEGREE - rho) // 2) if t else []


def validate_label(label):
    """
    Raises a ValueError (with a message suitable for display) if ``label`` is
    not a valid label for a class of K3-type motives over a finite field.
    """
    match = LABEL_RE.fullmatch(label)
    if not match:
        raise ValueError("it must be of the form %s, with q a prime power, rho an even integer between 0 and 22, and c and t consisting of lower case letters (with no t when rho = 22)" % LABEL_FORM)
    q, rho, c, codes = match.groups()
    if q[0] == "0" or not ZZ(q).is_prime_power():
        raise ValueError("it must be of the form %s, where q is a prime power" % LABEL_FORM)
    if (rho[0] == "0" and rho != "0") or int(rho) > DEGREE or int(rho) % 2:
        raise ValueError("it must be of the form %s, where the geometric Picard rank rho is an even integer between 0 and 22" % LABEL_FORM)
    rho = int(rho)
    if cremona_letter_code(class_to_int(c)) != c:
        raise ValueError("the cyclotomic code c must not start with a (unless it is a)")
    if class_to_int(c) >= num_cyclotomic_parts(rho):
        raise ValueError("there are only %s cyclotomic parts of degree %s, so the cyclotomic code c must come before %s" % (num_cyclotomic_parts(rho), rho, cremona_letter_code(num_cyclotomic_parts(rho))))
    k = (DEGREE - rho) // 2
    if k == 0:
        if codes:
            raise ValueError("when rho = 22 there is no transcendental part, so the label has the form q.22.c")
        return
    if not codes:
        raise ValueError("when rho = %s the label needs a transcendental part t, encoding %s coefficient%s" % (rho, k, "" if k == 1 else "s"))
    if len(codes) % k:
        raise ValueError("when rho = %s the transcendental part t encodes %s coefficients, so its length must be a multiple of %s" % (rho, k, k))
    if len(codes) > k and all(b[0] == "n" for b in transcendental_chunks(codes, k)):
        raise ValueError("the transcendental part t is padded with more leading n's than necessary")


def label_to_poly(label):
    """
    The coefficients [a_0, ..., a_22] of P(T) determined by a (valid) label.
    """
    q, rho, c, codes = split_label(label)
    lower = [balanced_value(b) for b in codes]
    trans = [q] + lower + lower[:-1][::-1] + [q] if lower else [q]
    P = cyclotomic_product(cyclotomic_orders(rho, class_to_int(c))) * PolynomialRing(ZZ, "T")(trans)
    return [ZZ(a) for a in P.padded_list(DEGREE + 1)]


def poly_to_label(coeffs):
    """
    The label of the class with P(T) given by ``coeffs`` = [a_0, ..., a_22].

    Raises a ValueError if ``coeffs`` does not have the shape of the
    polynomial of a K3-type motive (constant term a prime power q, and
    a_{22-i} = sign * a_i with sign = +1 or -1).  The condition that the roots
    lie on the unit circle is not checked.
    """
    coeffs = [ZZ(c) for c in coeffs]
    if len(coeffs) != DEGREE + 1:
        raise ValueError("the polynomial must have degree 22")
    q = coeffs[0]
    if q <= 1 or not q.is_prime_power():
        raise ValueError("the constant term must be a prime power q")
    if coeffs[-1] == q:
        eps = 1
    elif coeffs[-1] == -q:
        eps = -1
    else:
        raise ValueError("the leading coefficient must be q or -q")
    if any(coeffs[DEGREE - i] != eps * coeffs[i] for i in range(DEGREE + 1)):
        raise ValueError("the coefficients must satisfy a_{22-i} = %s a_i" % ("" if eps == 1 else "-"))
    R = PolynomialRing(ZZ, "T")
    P = R(coeffs)
    C = P.cyclotomic_part()
    orders = []
    if C.degree() > 0:
        for f, e in C.factor():
            m = f.is_cyclotomic(certificate=True)
            orders.extend([m] * e)
    orders.sort()
    trans = P // cyclotomic_product(orders)
    rho = sum(euler_phi(m) for m in orders)
    k = (DEGREE - rho) // 2
    if trans.list() != trans.list()[::-1] or trans[0] != q:
        raise ValueError("the transcendental part must be palindromic with constant term q")
    label = "%s.%s.%s" % (q, rho, cremona_letter_code(cyclotomic_index(orders)))
    if k:
        label += "." + transcendental_code([trans[i] for i in range(1, k + 1)])
    return label


def lpoly_to_poly(lcoeffs):
    """
    Converts the coefficients of L(T) = q^{-1} P(qT) (constant term 1, leading
    coefficient sign * q^22) to those of P(T).
    """
    lcoeffs = [ZZ(c) for c in lcoeffs]
    if len(lcoeffs) != DEGREE + 1 or lcoeffs[0] != 1:
        raise ValueError("L(T) must have degree 22 and constant term 1")
    lead = lcoeffs[-1].abs()
    q, exact = lead.nth_root(DEGREE, truncate_mode=True)
    if not exact or q <= 1:
        raise ValueError("the leading coefficient of L(T) must be plus or minus q^22")
    coeffs = [q]
    for i in range(1, DEGREE + 1):
        a, r = lcoeffs[i].quo_rem(q**(i - 1))
        if r:
            raise ValueError("the coefficient of T^%s in L(T) must be divisible by q^%s" % (i, i - 1))
        coeffs.append(a)
    return coeffs


#########################
#   Display helpers
#########################

def field_display(q):
    p, r = ZZ(q).is_prime_power(get_data=True)
    if r == 1:
        return r"\F_{%s}" % p
    return r"\F_{%s^{%s}}" % (p, r)


def yesno(val, none="not computed"):
    if val is None:
        return none
    return "yes" if val else "no"


def realizable_display(val):
    if val is None:
        return "not computed"
    return {1: "yes", -1: "no", 0: "unknown"}.get(val, str(val))


def strip_slope(s):
    # Remove the multiset indicators ("1/2A" -> "1/2")
    return re.sub(r"[A-Z]+$", "", s)


def slope_latex(s):
    return latex(QQ(s))


def poly_latex_increasing(coeffs, var="T"):
    # Product of a single factor, printed in increasing order
    return list_factored_to_factored_poly_otherorder([[list(coeffs), 1]], vari=var)


def integer_display(n, factor_bound=10**24):
    """
    Typesets an integer, along with its factorization when it is not too big.
    Large integers (such as Artin-Tate values over big extensions) are abbreviated,
    with the full value in a knowl.
    """
    if n is None:
        return "not computed"
    n = ZZ(n)
    if abs(n) > factor_bound:
        return bigint_knowl(n, cutoff=24)
    if abs(n) <= 1 or n.is_prime():
        return "$%s$" % n
    return r"$%s = %s$" % (n, latex(factor(n)).replace(r"-1 \cdot", "-"))


def label_wbr(label):
    """
    The label with line break opportunities between the coefficient codes
    when they take several letters each, since labels of classes with large
    coefficients (such as base changes) can be long.
    """
    parts = label.split(".")
    if len(parts) == 4 and LABEL_RE.fullmatch(label):
        codes = split_label(label)[3]
        if len(codes[0]) > 1:
            parts[3] = "<wbr>".join(codes)
    return ".".join(parts)


def k3_class_link(label):
    return '<a href="%s">%s</a>' % (url_for("k3fq.by_label", label=label), label_wbr(label))


def av_class_link(label):
    return '<a href="%s">%s</a>' % (url_for("abvarfq.by_label", label=label), label)


# The columns of k3_fq_isog, so that rows missing from a projection behave like nulls
ISOG_COLUMNS = [
    "label", "q", "p", "r", "sign", "poly", "poly_str", "real_poly", "angles", "angle_rank",
    "angle_corank", "slopes", "height", "has_k3_newton_polygon", "newton_elevation",
    "newton_coelevation", "is_ordinary", "is_supersingular", "cyclotomic_factors",
    "picard_rank", "geometric_picard_rank", "geometric_extension_degree", "extension_degrees",
    "picard_ranks", "artin_tate_values", "artin_tate_value", "ns_disc_class", "ej_condition",
    "transcendental_poly", "transcendental_factors", "transcendental_irreducible",
    "number_fields", "number_field_coeffs", "galois_groups", "k3_counts", "k3_count",
    "cubic_counts", "cubic_count", "gm_counts", "gm_count", "verra_counts", "verra_count",
    "has_nonnegative_counts", "has_count_growth",
    "is_pointless", "is_primitive", "primitive_models", "geometric_class", "twist_count",
    "twists", "max_twist_degree", "kummer_av_classes", "realizable_k3", "realizable_nck3",
    "realizable_cubic", "realizable_nccubic", "realizable_gm", "realizable_ncgm",
    "realizable_verra", "realizable_ncverra", "realizable_kummer", "polarization_degrees",
    "polarization_degrees_complete",
    "num_lattices", "min_ample_degree", "min_quasi_ample_degree",
]

# (title, knowl, column for the variety, column for the noncommutative version)
REALIZABILITY_TYPES = [
    ("K3 surface", "k3.fq.realizability", "realizable_k3", "realizable_nck3"),
    ("Cubic fourfold", "k3.fq.realizability", "realizable_cubic", "realizable_nccubic"),
    ("Gushel&ndash;Mukai fourfold", "k3.fq.realizability", "realizable_gm", "realizable_ncgm"),
    ("Verra fourfold", "k3.fq.realizability", "realizable_verra", "realizable_ncverra"),
    ("Kummer surface", "k3.fq.realizability", "realizable_kummer", None),
]

# (title, knowl, column)
POINT_COUNT_TYPES = [
    ("K3 surface", "k3.fq.point_counts", "k3_counts"),
    ("Cubic fourfold", "k3.fq.point_counts", "cubic_counts"),
    ("Gushel&ndash;Mukai fourfold", "k3.fq.point_counts", "gm_counts"),
    ("Verra fourfold", "k3.fq.point_counts", "verra_counts"),
]

LATTICE_COLUMNS = [
    "label", "rank", "genus_label", "lattice_label", "disc", "invariant_rank", "invariant_disc",
    "brauer_order", "min_quasi_ample_degree", "min_ample_degree", "has_roots",
    "contains_kummer_lattice", "conditions", "realizable_k3",
]
LATTICE_DISPLAY_LIMIT = 100


class WebK3Fq():
    """
    Class for an isogeny class of motives of K3 type over a finite field.
    """
    def __init__(self, dbdata):
        for col in ISOG_COLUMNS:
            setattr(self, col, None)
        self.__dict__.update(dbdata)
        if self.poly is None and self.label is not None:
            self.poly = label_to_poly(self.label)
        if self.q is None and self.poly is not None:
            self.q = self.poly[0]
        if self.q is not None:
            p, r = ZZ(self.q).is_prime_power(get_data=True)
            if self.p is None:
                self.p = p
            if self.r is None:
                self.r = r
        if self.sign is None and self.poly is not None:
            self.sign = 1 if self.poly[-1] > 0 else -1

    @classmethod
    def by_label(cls, label):
        """
        Searches for a specific class in the database by label.
        """
        data = isog_table.lookup(label)
        if data is None:
            raise ValueError("Label not found in database")
        return cls(data)

    #########################
    #   Invariants
    #########################

    def field(self, q=None):
        return field_display(self.q if q is None else q)

    @lazy_attribute
    def sign_display(self):
        return "+1" if self.sign == 1 else "-1"

    @lazy_attribute
    def polynomial_display(self):
        return raw_typeset_poly(self.poly, var="T", decreasing=False, compress_threshold=1000)

    @lazy_attribute
    def formatted_polynomial(self):
        # Used in search results: P(T) in increasing order
        return poly_latex_increasing(self.poly)

    @lazy_attribute
    def lpoly(self):
        q = ZZ(self.q)
        return [ZZ(1)] + [q**(i - 1) * ZZ(a) for i, a in enumerate(self.poly) if i > 0]

    @lazy_attribute
    def lpolynomial_display(self):
        return raw_typeset_poly(self.lpoly, var="T", decreasing=False, compress_threshold=300)

    @lazy_attribute
    def cyclotomic_counter(self):
        return Counter(self.cyclotomic_factors or [])

    def factor_lists(self):
        """
        A list of pairs (coefficient list, multiplicity), one for each distinct
        irreducible factor of P(T), each normalized to have positive constant
        term, together with the content of P(T).
        Returns None if the transcendental factorization is not available.
        """
        if self.cyclotomic_factors is None or self.transcendental_factors is None:
            return None
        ans = []
        cyc = self.cyclotomic_counter
        for m in sorted(cyc):
            if m == 1:
                ans.append(([1, -1], cyc[m]))
            else:
                ans.append((cyclotomic_polynomial(m).list(), cyc[m]))
        prod_const = ZZ(1)
        for f, e in self.transcendental_factors:
            if len(f) > 1:
                ans.append((list(f), e))
                prod_const *= ZZ(f[0])**e
        content = ZZ(self.q) / prod_const
        return ans, content

    @lazy_attribute
    def factored_polynomial(self):
        fl = self.factor_lists()
        if fl is None:
            return None
        factors, content = fl
        if not factors:
            return latex(content)
        s = list_factored_to_factored_poly_otherorder([[f, e] for f, e in factors], vari="T")
        if len(factors) == 1 and factors[0][1] == 1:
            s = "(%s)" % s
        if content != 1:
            s = "%s %s" % (latex(content), s)
        return s

    @lazy_attribute
    def is_irreducible_display(self):
        # Whether the factored form would just repeat P(T)
        fl = self.factor_lists()
        if fl is None:
            return True
        factors, content = fl
        return content == 1 and len(factors) == 1 and factors[0][1] == 1

    @lazy_attribute
    def real_poly_display(self):
        if self.real_poly is None:
            return None
        return raw_typeset_poly(self.real_poly, var="x", compress_threshold=1000)

    def frob_angles(self):
        """
        The angles (divided by pi) of the roots in the upper half plane, grouped
        with multiplicity.
        """
        if self.angles is None:
            return "not computed"
        eps = 0.00000001
        grouped = []
        for angle in self.angles:
            if grouped and abs(grouped[-1][0] - angle) < eps:
                grouped[-1][1] += 1
            else:
                grouped.append([angle, 1])
        ans = []
        for angle, mult in grouped:
            angstr = display_float(angle, 12, 'round')
            if abs(angle) > eps and abs(angle - 1) > eps:
                s = r"$\pm" + angstr + "$"
            else:
                s = "$" + angstr + "$"
            if mult > 1:
                s += r" ($\times %s$)" % mult
            ans.append(s)
        return ", ".join(ans)

    def circle_plot(self):
        if self.angles is None:
            return None
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
        P += points(pts, size=150, rgbcolor="darkblue")
        P.axes(False)
        P.set_aspect_ratio(1)
        return encode_plot(P, pad=0, pad_inches=None, transparent=True, axes_pad=0.04)

    #########################
    #   Newton polygon
    #########################

    @lazy_attribute
    def slope_multiplicities(self):
        if self.slopes is None:
            return None
        C = Counter(strip_slope(s) for s in self.slopes)
        return sorted(C.items(), key=lambda x: QQ(x[0]))

    def display_slopes(self):
        if self.slopes is None:
            return "not computed"
        ans = []
        for s, m in self.slope_multiplicities:
            disp = "$%s$" % slope_latex(s)
            if m > 1:
                disp += r" ($\times %s$)" % m
            ans.append(disp)
        return ", ".join(ans)

    @lazy_attribute
    def pretty_slopes(self):
        # Used in search results: slopes with multiplicities, such as 0, 1 (x20), 2
        if self.slopes is None:
            return None
        return ", ".join(slope_latex(s) + (r"\,(\times %s)" % m if m > 1 else "") for s, m in self.slope_multiplicities)

    @lazy_attribute
    def height_display(self):
        if self.height is None:
            if self.is_supersingular:
                return r"\infty"
            return None
        return str(self.height)

    #########################
    #   Picard ranks and Artin-Tate
    #########################

    @lazy_attribute
    def cyclotomic_display(self):
        if self.cyclotomic_factors is None:
            return None
        if not self.cyclotomic_factors:
            return "1"
        cyc = self.cyclotomic_counter
        return " ".join(r"\Phi_{%s}%s" % (m, "^{%s}" % cyc[m] if cyc[m] > 1 else "") for m in sorted(cyc))

    def artin_tate_table(self):
        """
        Rows (n, field, rho_n, AT_n display) for n in extension_degrees.
        """
        if self.extension_degrees is None:
            return []
        n = len(self.extension_degrees)
        ranks = self.picard_ranks if self.picard_ranks is not None else [None] * n
        ats = self.artin_tate_values if self.artin_tate_values is not None else [None] * n
        rows = []
        for d, rho, at in zip(self.extension_degrees, ranks, ats):
            rows.append((d, self.field(ZZ(self.q)**d), "not computed" if rho is None else rho, integer_display(at)))
        return rows

    #########################
    #   Transcendental part
    #########################

    @lazy_attribute
    def transcendental_degree(self):
        if self.transcendental_poly is None:
            return None
        return len(self.transcendental_poly) - 1

    @lazy_attribute
    def transcendental_poly_display(self):
        if self.transcendental_poly is None:
            return None
        return raw_typeset_poly(self.transcendental_poly, var="T", decreasing=False, compress_threshold=1000)

    def transcendental_factor_table(self):
        """
        Rows (factor display, multiplicity, degree, number field display, Galois group display),
        one for each irreducible factor of the transcendental part.
        """
        if not self.transcendental_factors:
            return []
        rows = []
        nfs = self.number_fields or []
        nfcoeffs = self.number_field_coeffs or []
        gals = self.galois_groups or []
        for i, (f, e) in enumerate(self.transcendental_factors):
            fdisp = raw_typeset_poly(f, var="T", decreasing=False, compress_threshold=100)
            nf = nfs[i] if i < len(nfs) else None
            if nf:
                pretty = field_pretty(nf)
                nfdisp = '<a href="%s">%s</a>' % (url_for("number_fields.by_label", label=nf), pretty)
            elif i < len(nfcoeffs) and nfcoeffs[i]:
                nfdisp = r"\(\Q[x]/(\)" + raw_typeset_poly(nfcoeffs[i], var="x", compress_threshold=100) + r"\()\)"
            else:
                nfdisp = "not computed"
            gal = gals[i] if i < len(gals) else None
            galdisp = transitive_group_display_knowl(gal) if gal else "not computed"
            rows.append((fdisp, e, len(f) - 1, nfdisp, galdisp))
        return rows

    def galois_groups_pretty(self):
        # Used in search results
        if not self.galois_groups:
            return ""
        cache = getattr(self, "gal_cache", None)
        return ", ".join(transitive_group_display_knowl(gal, cache=cache) for gal in self.galois_groups if gal)

    #########################
    #   Point counts
    #########################

    def point_count_table(self, n=None):
        """
        Rows (title, knowl, counts) for the different varieties of K3 type,
        omitting those whose counts are not computed.
        """
        rows = []
        for title, knowl, col in POINT_COUNT_TYPES:
            counts = getattr(self, col)
            if counts is not None:
                rows.append((title, knowl, list(counts) if n is None else list(counts[:n])))
        return rows

    def point_count_length(self):
        return max([len(getattr(self, col) or []) for _, _, col in POINT_COUNT_TYPES])

    #########################
    #   Realizability
    #########################

    def realizability_table(self):
        rows = []
        for title, knowl, col, nccol in REALIZABILITY_TYPES:
            rows.append((title, knowl, realizable_display(getattr(self, col)),
                         None if nccol is None else realizable_display(getattr(self, nccol))))
        return rows

    def kummer_display(self):
        if self.kummer_av_classes is None:
            return None
        if not self.kummer_av_classes:
            return "none"
        return ", ".join(av_class_link(lab) for lab in self.kummer_av_classes)

    def polarization_degrees_display(self):
        """
        The known polarization degrees, saying whether other degrees may occur.
        """
        if self.polarization_degrees is None:
            return None
        complete = getattr(self, "polarization_degrees_complete", None)
        if not self.polarization_degrees:
            return "none" if complete else "none known"
        ans = ", ".join("$%s$" % d for d in self.polarization_degrees)
        if not complete:
            ans += " (other degrees may occur)"
        return ans

    #########################
    #   Base change and twists
    #########################

    def primitive_models_display(self):
        if not self.primitive_models:
            return []
        return [(self.field(split_label(model)[0]), k3_class_link(model)) for model in self.primitive_models]

    def geometric_class_link(self):
        if self.geometric_class is None:
            return None
        return k3_class_link(self.geometric_class)

    def twists_search_url(self):
        if self.geometric_class is None:
            return None
        return url_for("k3fq.index", geometric_class=self.geometric_class)

    def twist_table(self):
        """
        Rows (twist link, n, common base change display) for the stored twists.
        """
        if not self.twists:
            return []
        # The common base changes are usually over fields that are much too big for the database
        bc_labels = list({tw[1] for tw in self.twists if tw[1]})
        known = set(isog_table.search({"label": {"$in": bc_labels}}, "label")) if bc_labels else set()
        rows = []
        for label, bc_label, n in self.twists:
            if bc_label is None:
                bc = "not computed"
            elif bc_label in known:
                bc = k3_class_link(bc_label)
            else:
                bc = '<span title="%s">not in the LMFDB</span>' % bc_label
            rows.append((k3_class_link(label), n, bc))
        return rows

    #########################
    #   Lattices
    #########################

    def lattices_available(self):
        return self.num_lattices is not None and table_exists(LATTICE_TABLE)

    @lazy_attribute
    def lattices(self):
        if not self.lattices_available():
            return []
        cols = [col for col in LATTICE_COLUMNS if col in lattice_table.search_cols]
        rows = list(lattice_table.search({"isog_label": self.label}, cols, limit=LATTICE_DISPLAY_LIMIT, sort=[]))

        def counter(rec):
            try:
                return int(rec["label"].split(".")[-1])
            except (KeyError, ValueError):
                return 0
        rows.sort(key=counter)
        for rec in rows:
            for col in LATTICE_COLUMNS:
                rec.setdefault(col, None)
        return rows

    def lattice_display(self, rec, col):
        val = rec.get(col)
        if val is None:
            return ""
        if col in ["has_roots", "contains_kummer_lattice"]:
            return "yes" if val else "no"
        if col == "realizable_k3":
            return realizable_display(val)
        if col == "lattice_label":
            return '<a href="%s">%s</a>' % (url_for("lattice.render_lattice_webpage", label=val), val)
        if col == "conditions":
            return ", ".join(val)
        if isinstance(val, (int, Integer)):
            return "$%s$" % val
        return str(val)

    #########################
    #   Properties and friends
    #########################

    def properties(self):
        props = [("Label", self.label)]
        plot = self.circle_plot()
        if plot is not None:
            props.append((None, '<img src="%s" width="200" height="150"/>' % plot))
        props.append(("Base field", "$%s$" % self.field()))
        props.append(("Sign", "$%s$" % self.sign_display))
        if self.picard_rank is not None:
            props.append(("Picard rank", "$%s$" % self.picard_rank))
        if self.geometric_picard_rank is not None:
            props.append(("Geom. Picard rank", "$%s$" % self.geometric_picard_rank))
        if self.height_display is not None:
            props.append(("Height", "$%s$" % self.height_display))
        if self.is_ordinary is not None:
            props.append(("Ordinary", yesno(self.is_ordinary)))
        if self.is_supersingular is not None:
            props.append(("Supersingular", yesno(self.is_supersingular)))
        if self.is_primitive is not None:
            props.append(("Primitive", yesno(self.is_primitive)))
        if self.realizable_k3:
            props.append(("K3 surface", realizable_display(self.realizable_k3)))
        return props

    def friends(self):
        friends = []
        for lab in self.kummer_av_classes or []:
            friends.append(("Abelian surface " + lab, url_for("abvarfq.by_label", label=lab)))
        if self.twist_count is not None and self.twist_count > 1 and self.geometric_class is not None:
            friends.append(("Twists", self.twists_search_url()))
        return friends
