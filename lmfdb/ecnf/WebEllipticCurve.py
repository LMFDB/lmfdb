import re
from flask import url_for
from urllib.parse import quote
from markupsafe import Markup, escape
from sage.all import (Infinity, PolynomialRing, QQ, RDF, ZZ, RR, KodairaSymbol,
                      implicit_plot, plot, prod, rainbow, sqrt, text, var)
from lmfdb import db
from lmfdb.utils import (encode_plot, names_and_urls, web_latex, display_knowl,
                         web_latex_split_on, integer_squarefree_part, nf_string_to_label)
from lmfdb.number_fields.web_number_field import WebNumberField, field_pretty
from lmfdb.lfunctions.LfunctionDatabase import (get_lfunction_by_url,
                                        get_instances_by_Lhash_and_trace_hash)
from lmfdb.sato_tate_groups.main import st_display_knowl
from lmfdb.elliptic_curves.web_ec import conductor_from_label, cremona_label_to_lmfdb_label

# The conductor label seems to only have three parts for the trivial ideal (1.0.1)
# field 3.1.23.1 uses upper case letters for isogeny class
LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+-\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+\d+")
SHORT_LABEL_RE = re.compile(r"\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+\d+")
CLASS_LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+-\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+")
SHORT_CLASS_LABEL_RE = re.compile(r"\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+")
FIELD_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")

def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    if not LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid elliptic curve label." % escape(lab)))
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = re.search("(CM)?[a-zA-Z]+", data[2]).group()
    curve_number = re.search(r"\d+", data[2]).group()  # (a string)
    return (field_label, conductor_label, isoclass_label, curve_number)


def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    if not SHORT_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid short elliptic curve label." % escape(lab)))
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = re.search("[a-zA-Z]+", data[1]).group()
    curve_number = re.search(r"\d+", data[1]).group()  # (a string)
    return (conductor_label, isoclass_label, curve_number)


def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    if not CLASS_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid elliptic curve isogeny class label." % escape(lab)))
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label, conductor_label, isoclass_label)


def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    if not SHORT_CLASS_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid short elliptic curve isogeny class label." % escape(lab)))
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label, isoclass_label)

def conductor_label_norm(lab):
    r""" extract norm from conductor label (as a string)"""
    s = lab.replace(' ','')
    if re.match(r'\d+.\d+',s):
        return s.split('.')[0]
    else:
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid conductor label. It must be of the form N.m or [N,c,d]" % escape(lab)))

def get_nf_info(lab):
    r""" extract number field label from string and pretty"""
    try:
        label = nf_string_to_label(lab)
        pretty = field_pretty(label)
    except ValueError as err:
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid number field label. %s" % (escape(lab),err)))
    return label, pretty

special_names = {'2.0.4.1': 'i',
                 '2.2.5.1': 'phi',
                 '4.0.125.1': 'zeta5',
                 }

def rename_j(j):
    sj = str(j)
    for name in ['zeta5', 'phi', 'i']:
        sj = sj.replace(name,'a')
    return sj

field_list = {}  # cached collection of enhanced WebNumberFields, keyed by label

def FIELD(label):
    nf = WebNumberField(label, gen_name=special_names.get(label, 'a'))
    nf.parse_NFelt = lambda s: nf.K()([QQ(c.encode()) for c in s.split(",")])
    nf.latex_poly = web_latex(nf.poly())
    return nf

def parse_NFelt(K, s):
    r"""
    Returns an element of K defined by the string s.
    """
    return K([QQ(c.encode()) for c in s.split(",")])

def parse_ainvs(K,ainvs):
    return [parse_NFelt(K,ai) for ai in ainvs.split(";")]

def web_ainvs(field_label, ainvs):
    K = FIELD(field_label).K()
    ainvsinlatex = web_latex_split_on(parse_ainvs(K,ainvs), on=[","])
    ainvsinlatex = ainvsinlatex.replace("\\left[", "\\bigl[")
    ainvsinlatex = ainvsinlatex.replace("\\right]", "\\bigr]")
    return ainvsinlatex

from sage.misc.all import latex
def web_point(P):
    return '$\\left(%s\\right)$' % (" : ".join(str(latex(x)) for x in P))


def pretty_ideal(Kgen, s, enclose=True):
    r"""Returns the a latex string an ideal of K defined by the string s,
    where Kgen is a strong representing the generator of K.  NB 'w' is
    used for the generator name for all fields for numbers stored in
    the database, and elements of K within the string s are
    polynomials in 'w'.

    s has the form "(g1)" or "(g1,g2)", ... where the gi are ideal
    generators.

    If enclose==True (default) then latex math delimiters are pre- and
    appended.
    """
    gens = s.replace('w', Kgen).replace("*","")
    if Kgen == 'phi':
        gens = gens.replace(Kgen, r"\phi")
    return r"\(" + gens + r"\)" if enclose else gens

def latex_factorization(plist, exponents, sign=+1):
    """plist is a list of strings representing prime ideals P (or other things) in latex without math delimiters.
    exponents is a list (of the same length) of non-negative integer exponents e, possibly  0.

    output is a latex string for the product of the P^e.

    When the factors are integers (for the factorization of a norm,
    for example) set sign=-1 to preprend a minus sign.

    """
    factors = ["{}^{{{}}}".format(q,n) if n > 1 else "{}".format(q) if n > 0 else "" for q,n in zip(plist, exponents)]
    factors = [f for f in factors if f] # exclude any factors with exponent 0
    return r"\({}{}\)".format("-" if sign == -1 else "", r"\cdot".join(factors))

def parse_point(K, s):
    r""" Returns a point in P^2(K) defined by the string s.  s has the form
    '[x,y,z]' where x, y, z have the form '[c0,c1,..]' with each ci
    representing a rational number.
    """
    #print("parse_point({})".format(s))
    cc = s[2:-2].replace("],[",":").split(":")
    return [K([QQ(ci.encode()) for ci in c.split(",")]) for c in cc]

def inflate_interval(a,b,r):
    c = (a+b)/2
    d = (b-a)/2
    d *= r
    return (c-d,c+d)


def plot_zone_union(R, S):
    return (min(R[0], S[0]), max(R[1], S[1]), min(R[2], S[2]), max(R[3], S[3]))


# Finds a suitable plotting zone for the component a <= x <= b of the EC y**2+h(x)*y=f(x)
def EC_R_plot_zone_piece(f,h,a,b):
    npts = 50
    Y = []
    g = f+h**2/4
    t = a
    s = (b-a)/npts
    for _ in range(npts+1):
        y = g(t)
        if y > 0:
            y = sqrt(y)
            w = h(t)/2
            Y.append(y-w)
            Y.append(-y-w)
        t += s
    (ymin,ymax) = inflate_interval(min(Y),max(Y),1.2)
    (a,b) = inflate_interval(a,b,1.3)
    return (a,b,ymin,ymax)

# Finds a suitable plotting zone for the EC y**2+h(x)*y=f(x)
def EC_R_plot_zone(f,h):
    F = f+h**2/4
    F1 = F.derivative()
    F2 = F1.derivative()
    G = F*F2-F1**2/2
    ZF = [z[0] for z in F.roots()]
    ZG = [z[0] for z in G.roots()]
    xi = max(ZG)
    if len(ZF) == 1:
        return EC_R_plot_zone_piece(f,h,ZF[0],2*xi-ZF[0])
    if len(ZF) == 3:
        return plot_zone_union(EC_R_plot_zone_piece(f,h,ZF[0],ZF[1]),EC_R_plot_zone_piece(f,h,ZF[2],2*xi-ZF[2]))
    return EC_R_plot_zone_piece(f,h,ZF[0],2*ZF[1]-ZF[0])

def EC_R_plot(ainvs, xmin, xmax, ymin, ymax, colour, legend):
    x = var('x')
    y = var('y')
    c = (xmin + xmax) / 2
    d = (xmax - xmin)
    return implicit_plot(y ** 2 + ainvs[0] * x * y + ainvs[2] * y - x ** 3 - ainvs[1] * x ** 2 - ainvs[3] * x - ainvs[4], (x, xmin, xmax), (y, ymin, ymax), plot_points=500, aspect_ratio="automatic", color=colour) + plot(0, xmin=c - 1e-5 * d, xmax=c + 1e-5 * d, ymin=ymin, ymax=ymax, aspect_ratio="automatic", color=colour, legend_label=legend)  # Add an extra plot outside the visible frame because implicit plots are buggy: their legend does not show (https://trac.sagemath.org/ticket/15903)

Rx = PolynomialRing(RDF,'x')

def EC_nf_plot(K, ainvs, base_field_gen_name):
    try:
        n1 = K.signature()[0]
        if n1 == 0:
            return plot([])
        R = []
        S = K.embeddings(RDF)
        for s in S:
            A = [s(c) for c in ainvs]
            R.append(EC_R_plot_zone(Rx([A[4],A[3],A[1],1]),Rx([A[2],A[0]])))
        xmin = min([r[0] for r in R])
        xmax = max([r[1] for r in R])
        ymin = min([r[2] for r in R])
        ymax = max([r[3] for r in R])
        cols = rainbow(n1) # Default choice of n colours
        # However, these tend to be too pale, so we preset them for small values of n
        if n1 == 1:
            cols = ["blue"]
        elif n1 == 2:
            cols = ["red","blue"]
        elif n1 == 3:
            cols = ["red","limegreen","blue"]
        elif n1 == 4:
            cols = ["red", "orange", "forestgreen", "blue"]
        elif n1 == 5:
            cols = ["red", "orange", "forestgreen", "blue", "darkviolet"]
        elif n1 == 6:
            cols = ["red", "darkorange", "gold", "forestgreen", "blue", "darkviolet"]
        elif n1 == 7:
            cols = ["red", "darkorange", "gold", "forestgreen", "blue", "darkviolet", "fuchsia"]
        return sum([EC_R_plot([S[i](c) for c in ainvs], xmin, xmax, ymin, ymax, cols[i], "$" + base_field_gen_name + r" \mapsto$ " + str(S[i].im_gens()[0].n(20)) + r"$\dots$") for i in range(n1)])
    except Exception:
        return text("Unable to plot", (1, 1), fontsize=36)

def ec_disc(ainvs):
    """
    Return discriminant of a Weierstrass equation from its list of a-invariants.
    (Temporary function pending inclusion of model discriminant in database.)
    """
    a1, a2, a3, a4, a6 = ainvs
    b2 = a1*a1 + 4*a2
    b4 = a3*a1 + 2*a4
    b6 = a3*a3 + 4*a6
    c4 = b2*b2 - 24*b4
    c6 = -b2*b2*b2 + 36*b2*b4 - 216*b6
    return (c4*c4*c4 - c6*c6) / 1728


def latex_equation(ainvs):
    a1, a2, a3, a4, a6 = ainvs

    def co(coeff):
        pol = coeff.polynomial()
        mons = pol.monomials()
        n = len(mons)
        if n == 0:
            return ""
        if n > 1:
            return r"+\left({}\right)".format(latex(coeff))
        # now we have a numerical coefficient times a power of the generator
        if coeff == 1:
            return "+"
        if coeff == -1:
            return "-"
        co = pol.monomial_coefficient(mons[0])
        s = "+" if co > 0 else ""
        return "{}{}".format(s, latex(coeff))

    def term(coeff, mon):
        if not coeff:
            return ""
        if not mon:
            return "+{}".format(latex(coeff)).replace("+-","-")
        return "{}{}".format(co(coeff), mon)

    return ''.join([r'y^2',
                    term(a1,'xy'),
                    term(a3,'y'),
                    '=x^3',
                    term(a2,'x^2'),
                    term(a4,'x'),
                    term(a6,''),
                    r''])

class ECNF():

    """
    ECNF Wrapper
    """

    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        # del dbdata["_id"]
        self.__dict__.update(dbdata)
        self.field = FIELD(self.field_label)
        self.nonmax_primes = dbdata.get('nonmax_primes',None)
        self.make_E()

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db.ec_nfcurves.lookup(label)
        if data:
            return ECNF(data)
        return "Elliptic curve not found: %s" % label # caller must check for this

    def make_E(self):
        #print("Creating ECNF object for {}".format(self.label))
        #sys.stdout.flush()
        K = self.field.K()
        Kgen = str(K.gen())

        # a-invariants
        # NB Here we construct the ai as elements of K, which are used as follows:
        # (1) to compute the model discriminant (if not stored)
        # (2) to compute the latex equation (if not stored)
        # (3) to compute the plots under real embeddings of K
        # Of these, (2) is not needed and (1) will soon be obsolete;
        #  for (3) it would be possible to rewrite the function EC_nf_plot() not to need this.
        # Then we might also be able to avoid constructing the field K also.

        self.ainvs = parse_ainvs(K,self.ainvs)
        self.numb = str(self.number)

        # Conductor, discriminant, j-invariant

        self.cond_norm = web_latex(self.conductor_norm)

        Dnorm = self.normdisc
        self.model_disc = self.disc.replace('w', Kgen).replace("*","").replace("(","").replace(")","")
        if Kgen == 'phi':
            self.model_disc = self.model_disc.replace(Kgen, r"\phi")
        self.disc = pretty_ideal(Kgen, self.disc)

        local_data = self.local_data
        local_data.sort(key=lambda ld: ld['normp'])

        badprimes = [pretty_ideal(Kgen, ld['p'], enclose=False) for ld in local_data]
        badnorms = [ld['normp'] for ld in local_data]
        disc_ords = [ld['ord_disc'] for ld in local_data]
        mindisc_ords = [ld['ord_disc'] for ld in local_data]
        cond_ords = [ld['ord_cond'] for ld in local_data]

        if self.conductor_norm == 1:
            self.cond = r"\((1)\)"
            self.fact_cond = self.cond
            self.fact_cond_norm = '1'
        else:
            self.cond = pretty_ideal(Kgen, self.conductor_ideal)
            self.fact_cond = latex_factorization(badprimes, cond_ords)
            self.fact_cond_norm = latex_factorization(badnorms, cond_ords)

        # Assumption: the curve models stored in the database are
        # either global minimal models or minimal at all but one
        # prime, so the list here has length 0 or 1:

        self.is_minimal = (len(self.non_min_p) == 0)
        self.has_minimal_model = self.is_minimal

        if not self.is_minimal:
            non_min_p = self.non_min_p[0]
            self.non_min_prime = pretty_ideal(Kgen, non_min_p)
            ip = [ld['p'] for ld in local_data].index(non_min_p)
            disc_ords[ip] += 12
            Dnorm_factor = local_data[ip]['normp']**12

        self.disc_norm = web_latex(Dnorm)
        signDnorm = 1 if Dnorm > 0 else -1
        if Dnorm in [1, -1]:  # since the factorization of (1) displays as "1"
            self.fact_disc = self.disc
            self.fact_disc_norm = str(Dnorm)
        else:
            self.fact_disc = latex_factorization(badprimes, disc_ords)
            self.fact_disc_norm = latex_factorization(badnorms, disc_ords, sign=signDnorm)

        if self.is_minimal:
            Dmin_norm = Dnorm
            self.mindisc = self.disc
        else:
            Dmin_norm = Dnorm // Dnorm_factor
            self.mindisc = pretty_ideal(Kgen, self.minD)

        self.mindisc_norm = web_latex(Dmin_norm)
        if Dmin_norm in [1,-1]:  # since the factorization of (1) displays as "1"
            self.fact_mindisc = self.mindisc
            self.fact_mindisc_norm = self.mindisc_norm
        else:
            self.fact_mindisc = latex_factorization(badprimes, mindisc_ords)
            self.fact_mindisc_norm = latex_factorization(badnorms, mindisc_ords, sign=signDnorm)

        j = self.field.parse_NFelt(self.jinv)
        self.j = web_latex(j)
        self.fact_j = None
        # See issue 1258: some j factorizations work but take too long
        # (e.g. EllipticCurve/6.6.371293.1/1.1/a/1).  Note that we do
        # store the factorization of the denominator of j and display
        # that, which is the most interesting part.

        # When the equation is stored in the database as a latex string,
        # it may have extraneous double quotes at beginning and
        # end, which we fix here.  We also strip out initial \( and \)
        # (if present) which are added in the template.
        try:
            self.equation = self.equation.replace('"','').replace(r'\\(','').replace(r'\\)','')
        except AttributeError:
            self.equation = latex_equation(self.ainvs)

        # Images of Galois representations

        if not hasattr(self,'galois_images'):
            #print "No Galois image data"
            self.galois_images = "?"
            self.nonmax_primes = "?"
            self.galois_data = []
        else:
            self.galois_data = [{'p': p,'image': im }
                                for p,im in zip(self.nonmax_primes,
                                                self.galois_images)]

        # CM and End(E)
        self.cm_bool = "no"
        self.End = r"\(\Z\)"
        self.rational_cm = self.cm_type > 0
        if self.cm:
            self.cm_sqf = integer_squarefree_part(ZZ(self.cm))
            self.cm_bool = r"yes (\(%s\))" % self.cm
            if self.cm % 4 == 0:
                d4 = ZZ(self.cm) // 4
                self.End = r"\(\Z[\sqrt{%s}]\)" % (d4)
            else:
                self.End = r"\(\Z[(1+\sqrt{%s})/2]\)" % self.cm

        # Galois images in CM case:
        if self.cm and self.galois_images != '?':
            self.cm_ramp = [p for p in ZZ(self.cm).support() if p not in self.nonmax_primes]
            self.cm_nramp = len(self.cm_ramp)
            if self.cm_nramp == 1:
                self.cm_ramp = self.cm_ramp[0]
            else:
                self.cm_ramp = ", ".join(str(p) for p in self.cm_ramp)

        # Sato-Tate:
        self.ST = st_display_knowl('1.2.A.1.1a' if not self.cm_type else ('1.2.B.2.1a' if self.cm_type < 0 else '1.2.B.1.1a'))

        # Q-curve / Base change
        try:
            qc = self.q_curve
            if qc is True:
                self.qc = "yes"
            elif qc is False:
                self.qc = "no"
            else: # just in case
                self.qc = "not determined"
        except AttributeError:
            self.qc = "not determined"

        # Mordell-Weil group
        try:
            invs = [0 for a in range(self.rank)] + list(self.torsion_structure)
            self.mw_struct = "trivial" if len(invs) == 0 else r'\(' + r' \oplus '.join((r'\Z' if n == 0 else r'\Z/{%s}\Z' % n) for n in invs) + r'\)'
        except AttributeError: # if self.rank not set
            self.mw_struct = "unknown"

        # Torsion
        BSDntors = self.torsion_order
        self.ntors = web_latex(BSDntors)
        self.tr = len(self.torsion_structure)
        if self.tr == 0:
            self.tor_struct_pretty = "$0$"
        if self.tr == 1:
            self.tor_struct_pretty = r"\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr == 2:
            self.tor_struct_pretty = r"\(\Z/%s\Z\oplus\Z/%s\Z\)" % tuple(self.torsion_structure)

        self.torsion_gens = [web_point(parse_point(K,P)) for P in self.torsion_gens]
        self.tor_gens_and_orders = list(zip(self.torsion_gens, self.torsion_structure))

        # BSD data
        #
        # We divide into 3 cases, based on rank_bounds [lb,ub],
        # analytic_rank ar, (lb=ngens always).  The flag
        # self.bsd_status is set to one of the following:
        #
        # "unconditional"
        #     lb=ar=ub: we always have reg but in some cases over sextic fields we do not have omega, Lvalue, sha.
        #     i.e. [lb,ar,ub] = [r,r,r]
        #
        # "conditional"
        #     lb=ar<ub: we always have reg but in some cases over sextic fields we do not have omega, Lvalue, sha.
        #     e.g. [lb,ar,ub] = [0,0,2], [1,1,3]
        #
        # "missing_gens"
        #     lb<ar<=ub
        #     e.g. [lb,ar,ub] = [0,1,1], [0,2,2], [1,2,2], [0,1,3]
        #
        # "incomplete"
        #     ar not computed.  (We can always set lb=0, ub=Infinity.)

        # Rank and bounds
        try:
            self.rk = web_latex(self.rank)
        except AttributeError:
            self.rank = None
            self.rk = "not available"

        try:
            self.rk_lb, self.rk_ub = self.rank_bounds
        except AttributeError:
            self.rk_lb = 0
            self.rk_ub = Infinity
            self.rank_bounds = "not available"

        # Analytic rank
        try:
            self.ar = web_latex(self.analytic_rank)
        except AttributeError:
            self.analytic_rank = None
            self.ar = "not available"

        # for debugging:
        assert self.rk == "not available" or (self.rk_lb == self.rank
                                              and self.rank == self.rk_ub)
        assert self.ar == "not available" or (self.rk_lb <= self.analytic_rank and self.analytic_rank <= self.rk_ub)

        self.bsd_status = "incomplete"
        if self.analytic_rank is not None:
            if self.rk_lb == self.rk_ub:
                self.bsd_status = "unconditional"
            elif self.rk_lb == self.analytic_rank:
                self.bsd_status = "conditional"
            else:
                self.bsd_status = "missing_gens"

        # Regulator only in conditional/unconditional cases, or when we know the rank:
        BSDReg = None
        if self.bsd_status in ["conditional", "unconditional"]:
            if self.analytic_rank == 0:
                BSDReg = 1
                self.reg = self.NTreg = web_latex(BSDReg)  # otherwise we only get 1.00000...
            else:
                try:
                    R = self.reg
                    BSDReg = R * K.degree()**self.rank
                    self.reg = web_latex(R)
                    self.NTreg = web_latex(BSDReg)
                except Exception:
                    self.reg = "not available"
                    self.NTreg = "not available"
        elif self.rk != "not available":
            R = self.reg
            BSDReg = R * K.degree()**self.rank
            self.reg = web_latex(R) if self.rank else web_latex(1)
            self.NTreg = web_latex(BSDReg) if self.rank else web_latex(1)
        else:
            self.reg = "not available"
            self.NTreg = "not available"

        # Generators
        try:
            self.gens = [web_point(parse_point(K, P)) for P in self.gens]
            self.gens_and_heights = list(zip(self.gens,self.heights))
            self.gens_and_heights.sort(key=lambda Ph: Ph[1])
        except AttributeError:
            self.gens = []
            self.gens_and_heights = []

        # Global period -- see issue #5409 for why we multiply by
        # 2**nc in most cases.  However, data computed after
        # 2024-07-09 (including all data for imaginary quadratic
        # fields of absolute discriminant > 600 as well as some larger
        # conductors for other IQFs) already has the extra factor of
        # 2.  As a fail-safe until we fix the data in all cases, we
        # will test (using the BSD formula) whether to remove the
        # factor of 2 added here.
        BSDomega = None
        try:
            BSDomega = self.omega
            nc = self.signature[1] # number of complex places
            if nc:
                BSDomega *= 2**nc
            self.omega = web_latex(BSDomega)
        except AttributeError:
            self.omega = "not available"

        # L-value
        BSDLvalue = None
        try:
            r = int(self.analytic_rank)
            # lhs = "L(E,1) = " if r==0 else "L'(E,1) = " if r==1 else "L^{{({})}}(E,1)/{}! = ".format(r,r)
            BSDLvalue = self.Lvalue
            self.Lvalue = web_latex(BSDLvalue)
        except (TypeError, AttributeError):
            self.Lvalue = "not available"

        # Tamagawa product
        tamagawa_numbers = [ZZ(_ld['cp']) for _ld in self.local_data]
        cp_fac = [cp.factor() for cp in tamagawa_numbers]
        cp_fac = [latex(cp) if len(cp) < 2 else '('+latex(cp)+')' for cp in cp_fac]
        if len(cp_fac) > 1:
            self.tamagawa_factors = r'\cdot'.join(cp_fac)
        else:
            self.tamagawa_factors = None
        BSDprodcp = prod(tamagawa_numbers,1)
        self.tamagawa_product = web_latex(BSDprodcp)

        # Analytic Sha
        BSDsha = None
        try:
            BSDsha = self.sha
            self.sha = web_latex(BSDsha) + " (rounded)"
        except AttributeError:
            self.sha = "not available"

        # Check analytic Sha value compatible with formula in the knowl (see issue #5409)

        BSDrootdisc = RR(K.discriminant().abs()).sqrt()
        BSDok = True
        if BSDLvalue and BSDsha and BSDReg and (self.rank is not None):
            BSDsha_numerator = BSDrootdisc * BSDntors**2
            BSDsha_denominator = BSDReg * BSDomega * BSDprodcp
            BSDsha_from_formula = BSDLvalue * BSDsha_numerator / BSDsha_denominator
            BSDsha_from_formula_rounded = BSDsha_from_formula.round()
            BSDok = (BSDsha_from_formula_rounded == BSDsha) and ((BSDsha_from_formula_rounded - BSDsha_from_formula).abs() < 0.001)
            #print(f"{BSDsha_from_formula=}")
            #print(f"{BSDsha_from_formula_rounded=}")
            #print(f"{BSDsha=}")
            #print(f"{BSDok=}")
            if not BSDok:
                # this means that we doubled BSDomega when we should
                # not have, so BSDsha_denominator is doubled and
                # BSDsha_from formula is halved
                print(f"BSD normalization: adjusting Omega for {self.label}: stored Sha = {BSDsha} but formula gives {BSDsha_from_formula}")
                BSDok = ((BSDsha/BSDsha_from_formula)-2).abs() < 0.01
                if not BSDok:
                    print(f"BSD normalization issue with {self.label}: stored Sha = {BSDsha} but formula gives {BSDsha_from_formula}")
                BSDomega /= 2
                BSDsha_denominator /= 2
                BSDsha_from_formula *= 2
                BSDsha_from_formula_rounded = BSDsha_from_formula.round()
            BSDLvalue_from_formula = BSDsha * BSDsha_denominator / BSDsha_numerator
            self.BSDsha = web_latex(BSDsha_from_formula)
            self.BSDLvalue = web_latex(BSDLvalue_from_formula)

            # The BSD formula for display

            dot = '\\cdot'
            approx = '\\approx'
            eq_query = '\\overset{?}{=}'
            frac = '\\frac'
            Sha = '\\# &#1064;(E/K)'
            Sha = '\\# Ш(E/K)'
            Om = '\\Omega(E/K)'
            Reg = '\\mathrm{Reg}_{\\mathrm{NT}}(E/K)'
            prodcp = '\\prod_{\\mathfrak{p}} c_{\\mathfrak{p}}'
            tors2 = '\\#E(K)_{\\mathrm{tor}}^2'
            rootD = '\\left|d_K\\right|^{1/2}'

            lder_name  = rf"L^{{({r})}}(E/K,1)/{r}!" if r >= 2 else "L'(E/K,1)" if r else "L(E/K,1)"
            lhs_num    = rf'{Sha} {dot} {Om} {dot} {Reg} {dot} {prodcp}'
            lhs_den    = rf'{tors2} {dot} {rootD}'
            lhs        = rf'{frac}{{ {lhs_num} }} {{ {lhs_den} }}'
            rhs_num    = rf'{BSDsha} {dot} {BSDomega:0.6f} {dot} {BSDReg} {dot} {BSDprodcp}'
            if r:
                rhs_num    = rf'{BSDsha} {dot} {BSDomega:0.6f} {dot} {BSDReg:0.6f} {dot} {BSDprodcp}'
            rhs_den    = rf'{{{BSDntors}^2 {dot} {BSDrootdisc:0.6f}}}'
            rhs        = rf'{frac}{{ {rhs_num} }} {{ {rhs_den} }}'
            self.bsd_formula = rf'\begin{{aligned}}{BSDLvalue:0.9f} {approx} {lder_name} & {eq_query} {lhs} \\ & {approx} {rhs} \\ & {approx} {BSDLvalue_from_formula:0.9f} \end{{aligned}}'

        else:
            self.BSDsha = "not available"
            self.BSDLvalue = "not available"
            self.bsd_formula = None

        if not BSDok: # don't display the formula if it is not correct
            self.bsd_formula = None

        # Local data

        # The Kodaira symbol is stored as an int in pari encoding. The
        # conversion to latex must take into account the bug (in Sage
        # 9.2) for I_m^* when m has more than one digit.

        def latex_kod(kod):
            return latex(KodairaSymbol(kod)) if kod > -14 else 'I_{%s}^{*}' % (-kod - 4)

        for P,NP,ld in zip(badprimes, badnorms, local_data):
            ld['p'] = P
            ld['norm'] = NP
            ld['kod'] = latex_kod(ld['kod'])

        # URLs of self and related objects:
        self.urls = {}
        # It's useful to be able to use this class out of context, when calling url_for will fail:
        try:
            self.urls['curve'] = url_for(".show_ecnf", nf=self.field_label, conductor_label=quote(self.conductor_label), class_label=self.iso_label, number=self.number)
        except RuntimeError:
            return
        self.urls['class'] = url_for(".show_ecnf_isoclass", nf=self.field_label, conductor_label=quote(self.conductor_label), class_label=self.iso_label)
        self.urls['conductor'] = url_for(".show_ecnf_conductor", nf=self.field_label, conductor_label=quote(self.conductor_label))
        self.urls['field'] = url_for(".show_ecnf1", nf=self.field_label)

        # Isogeny information

        self.one_deg = ZZ(self.class_deg).is_prime()
        isodegs = [str(d) for d in self.isodeg if d > 1]
        if len(isodegs) < 3:
            self.isodeg = " and ".join(isodegs)
        else:
            self.isodeg = " and ".join([", ".join(isodegs[:-1]), isodegs[-1]])

        sig = self.signature
        totally_real = sig[1] == 0
        imag_quadratic = sig == [0,1]

        if totally_real:
            self.hmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])
            self.urls['hmf'] = url_for('hmf.render_hmf_webpage', field_label=self.field.label, label=self.hmf_label)
            lfun_url = url_for("l_functions.l_function_ecnf_page", field_label=self.field_label, conductor_label=self.conductor_label, isogeny_class_label=self.iso_label)
            origin_url = lfun_url.lstrip('/L/').rstrip('/')
            if sig[0] <= 2 and db.lfunc_instances.exists({'url':origin_url}):
                self.urls['Lfunction'] = lfun_url
            elif self.abs_disc ** 2 * self.conductor_norm < 70000:
                # we shouldn't trust the Lfun computed on the fly for large conductor
                self.urls['Lfunction'] = url_for("l_functions.l_function_hmf_page", field=self.field_label, label=self.hmf_label, character='0', number='0')

        if imag_quadratic:
            self.bmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])
            self.bmf_url = url_for('bmf.render_bmf_webpage', field_label=self.field_label, level_label=self.conductor_label, label_suffix=self.iso_label)
            lfun_url = url_for("l_functions.l_function_ecnf_page", field_label=self.field_label, conductor_label=self.conductor_label, isogeny_class_label=self.iso_label)
            origin_url = lfun_url.lstrip('/L/').rstrip('/')
            if db.lfunc_instances.exists({'url':origin_url}):
                self.urls['Lfunction'] = lfun_url

        # most of this code is repeated in isog_class.py
        # and should be refactored
        self.friends = []
        self.friends += [('Isogeny class ' + self.short_class_label, self.urls['class'])]
        self.friends += [('Twists', url_for('ecnf.index', field=self.field_label, jinv=rename_j(j)))]
        if totally_real and 'Lfunction' not in self.urls:
            self.friends += [('Hilbert modular form ' + self.hmf_label, self.urls['hmf'])]

        if imag_quadratic:
            if "CM" in self.label:
                self.friends += [('Bianchi modular form is not cuspidal', '')]
            elif 'Lfunction' not in self.urls:
                if db.bmf_forms.label_exists(self.bmf_label):
                    self.friends += [('Bianchi modular form %s' % self.bmf_label, self.bmf_url)]
                else:
                    self.friends += [('(Bianchi modular form %s)' % self.bmf_label, '')]

        self.properties = [('Label', self.label)]

        # Plot
        if K.signature()[0]:
            self.plot = None
            if self.degree > 2:
                self.plot = db.ec_nfportraits.lookup(self.label, "portrait")
            if self.plot is None:
                self.plot = encode_plot(EC_nf_plot(K,self.ainvs, self.field.generator_name()), transparent=True)
            self.plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)
            self.properties += [(None, self.plot_link)]
        self.properties += [('Base field', self.field.field_pretty())]

        self.properties += [
            # hide conductor in Properties box (can be very large)
            # ('Conductor', self.cond),
            ('Conductor norm', self.cond_norm),
            # See issue #796 for why this is hidden (can be very large)
            # ('j-invariant', self.j),
            ('CM', self.cm_bool)]

        if not self.base_change:
            self.base_change = []  # in case it was False or None instead of []
        self.nbc = len(self.base_change)

        # add base_change yes/no to Properties box
        if self.base_change:
            self.properties += [('Base change', 'yes')]
        else:
            self.properties += [('Base change', 'no')]
        self.properties += [('Q-curve', self.qc)]

        r = self.rk
        if r == "?":
            r = self.rk_bnds
        self.properties += [
            ('Torsion order', self.ntors),
            ('Rank', r),
        ]

        # add links to base curves if base-change - first separate
        # labels over Q from others, and convert any Cremona labels to
        # LMFDB labels:
        self.base_change_Q = [cremona_label_to_lmfdb_label(lab) for lab in self.base_change if '-' not in lab]

        # sort by conductor (so also unknown curves come last)
        self.base_change_Q.sort(key=lambda lab:ZZ(conductor_from_label(lab)))
        self.bcQtext = [] # for the Base change section of the home page
        for lab in self.base_change_Q:
            if '?' in lab:
                cond = conductor_from_label(lab)
                self.bcQtext.append('a curve of conductor {} (not in the database)'.format(cond))
                # but omit from friends
            else:
                url = url_for("ec.by_ec_label", label=lab)
                self.bcQtext.append('<a href="{}">{}</a>'.format(url,lab))
                self.friends += [(r'Base change of {} /\(\Q\)'.format(lab), url)]

        self.base_change_NF = [lab for lab in self.base_change if '-' in lab]
        # we want to use split_full_label but that will fail if the class code + number are '?'
        self.base_change_NFsplit = [(lab,)+split_full_label(lab.replace('?','a1')) for lab in self.base_change_NF]
        self.bcNFtext = [] # for the Base change section of the home page
        for lab, nf, cond, cl, num in self.base_change_NFsplit:
            field_knowl = FIELD(nf).knowl()
            if '?' in lab:
                cond_norm = cond.split(".")[0]
                self.bcNFtext.append(["{}".format(field_knowl), "a curve with conductor norm {} (not in the database)".format(cond_norm)])
            else:
                url = url_for(".show_ecnf", nf=nf, conductor_label=cond, class_label=cl, number=num)
                self.bcNFtext.append(["{}".format(field_knowl), '<a href="{}">{}</a>'.format(url,lab)])
                self.friends += [(r'Base change of %s' % lab, url)]
        self._code = None # will be set if needed by get_code()

        self.downloads = [('All stored data to text', url_for(".download_ECNF_all", nf=self.field_label, conductor_label=quote(self.conductor_label), class_label=self.iso_label, number=self.number))]
        for lang in [["Magma","magma"], ["PariGP", "gp"], ["SageMath","sage"]]:
            self.downloads.append(('{} commands'.format(lang[0]),
                                   url_for(".ecnf_code_download", nf=self.field_label, conductor_label=quote(self.conductor_label),
                                           class_label=self.iso_label, number=self.number, download_type=lang[1])))
        self.downloads.append(('Underlying data', url_for(".ecnf_data", label=self.label)))

        if 'Lfunction' in self.urls:
            Lfun = get_lfunction_by_url(self.urls['Lfunction'].lstrip('/L').rstrip('/'), projection=['degree', 'trace_hash', 'Lhash'])
            if Lfun is None:
                self.friends += [('L-function not available', "")]
            else:
                instances = get_instances_by_Lhash_and_trace_hash(
                    Lfun['Lhash'],
                    Lfun['degree'],
                    Lfun.get('trace_hash'))
                exclude = {elt[1].rstrip('/').lstrip('/') for elt in self.friends
                         if elt[1]}
                self.friends += names_and_urls(instances, exclude=exclude)
                self.friends += [('L-function', self.urls['Lfunction'])]
        else:
            self.friends += [('L-function not available', "")]

    def display_modell_image(self,label):
        return display_knowl('gl2.subgroup_data', title=label, kwargs={'label':label})

    def code(self):
        if self._code is None:
            self._code = make_code(self.label)
        return self._code

sorted_code_names = ['field', 'curve', 'is_min', 'cond', 'cond_norm',
                     'disc', 'disc_norm', 'jinv', 'cm', 'rank',
                     'gens', 'heights', 'reg', 'tors', 'ntors', 'torgens', 'localdata']


Fullname = {'magma': 'Magma', 'sage': 'SageMath', 'gp': 'Pari/GP', 'pari': 'Pari/GP'}
Comment = {'magma': '//', 'sage': '#', 'gp': '\\\\', 'pari': '\\\\'}

def make_code(label, lang=None):
    """Return a dict of code snippets for one curve in either one
    language (if lang is 'pari' or 'gp', 'sage', or 'magma') or all
    three (if lang is None).
    """
    if lang == 'gp':
        lang = 'pari'
    all_langs = ['magma', 'pari', 'sage']

    # Get the base field label and a-invariants:

    E = db.ec_nfcurves.lookup(label, projection=['field_label', 'ainvs'])

    # Look up the defining polynomial of the base field:

    from lmfdb.utils import coeff_to_poly
    poly = coeff_to_poly(db.nf_fields.lookup(E['field_label'], projection='coeffs'))

    # read in code.yaml from current directory:

    import os
    import yaml
    _curdir = os.path.dirname(os.path.abspath(__file__))
    Ecode = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)

    # Fill in placeholders for this specific curve and language:
    if lang:
        for k in sorted_code_names:
            Ecode[k] = Ecode[k][lang] if lang in Ecode[k] else None

    # Fill in field polynomial coefficients:
    if lang:
        Ecode['field'] = Ecode['field'] % str(poly.list())
    else:
        for l in all_langs:
            Ecode['field'][l] = Ecode['field'][l] % str(poly.list())

    # Fill in curve coefficients:
    ainvs = [f"[{ai}]" for ai in E['ainvs'].split(";")]
    ainvs_string = {
        'magma': "[" + ",".join("K!{}".format(ai) for ai in ainvs) + "]",
        'sage': "[" + ",".join("K({})".format(ai) for ai in ainvs) + "]",
        'pari': "[" + ",".join("Polrev({})".format(ai) for ai in ainvs) + "], K",
        }
    if lang:
        Ecode['curve'] = Ecode['curve'] % ainvs_string[lang]
    else:
        for l in all_langs:
            Ecode['curve'][l] = Ecode['curve'][l] % ainvs_string[l]

    return Ecode
