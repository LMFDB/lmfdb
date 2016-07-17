import os
import yaml
from flask import url_for
from urllib import quote
from sage.all import ZZ, var, PolynomialRing, QQ, RDF, rainbow, implicit_plot, plot, text, Infinity, sqrt, prod, Factorization
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex, web_latex_ideal_fact, encode_plot
from lmfdb.WebNumberField import WebNumberField
from lmfdb.sato_tate_groups.main import st_link_by_name

ecnf = None
nfdb = None

def db_ecnf():
    global ecnf
    if ecnf is None:
        ecnf = getDBConnection().elliptic_curves.nfcurves2
    return ecnf

def db_nfdb():
    global nfdb
    if nfdb is None:
        nfdb = getDBConnection().numberfields.fields
    return nfdb

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
    nf.parse_NFelt = lambda s: nf.K()([QQ(str(c)) for c in s])
    nf.latex_poly = web_latex(nf.poly())
    return nf

def make_field(label):
    global field_list
    if not label in field_list:
        #print("Constructing field %s" % label)
        field_list[label] = FIELD(label)
    return field_list[label]

def web_ainvs(field_label, ainvs):
    return web_latex([make_field(field_label).parse_NFelt(x) for x in ainvs])

from sage.misc.all import latex
def web_point(P):
    return '$\\left(%s\\right)$'%(" : ".join([str(latex(x)) for x in P]))

def ideal_from_string(K,s):
    r"""Returns the ideal of K defined by the string s.  For imaginary
    quadratic fields this is "[N,c,d]" with N,c,d as in a label, while
    for other fields it is of the form "[N,a,alpha]" where N is the
    norm, a the least positive integer in the ideal and alpha a second
    generator so that the ideal is (a,alpha).  alpha is a polynomial
    in the variable w which represents the generator of K.
    """
    N, a, alpha = s[1:-1].split(",")
    N = ZZ(N)
    a = ZZ(a)
    if 'w' in alpha:
        alpha = K(alpha.encode())
        #alpha = alpha.replace('w',str(K.gen()))
        I = K.ideal(a,alpha)
        assert I.norm()==N
        return I
    d = ZZ(alpha)
    return K.ideal(N//d, K([a, d]))

# HNF of an ideal I in a quadratic field

def ideal_HNF(I):
    r"""
    Returns an HNF triple defining the ideal I in a quadratic field
    with integral basis [1,w].

    This is a list [a,b,d] such that [a,c+d*w] is a Z-basis of I, with
    a,d>0; c>=0; N = a*d = Norm(I); d|a and d|c; 0 <=c < a.
    """
    N = I.norm()
    a, c, b, d = I.pari_hnf().python().list()
    assert a > 0 and d > 0 and N == a * d and d.divides(a) and d.divides(b) and 0 <= c < a
    return [a, c, d]

def ideal_to_string(I):
    K = I.number_field()
    if K.signature() == (0,1):
        a, c, d = ideal_HNF(I)
        return "[%s,%s,%s]" % (a * d, c, d)
    N = I.norm()
    a = I.smallest_integer()
    gens = I.gens_reduced()
    alpha = gens[-1]
    assert I == K.ideal(a,alpha)
    alpha = str(alpha).replace(str(K.gen()),'w')
    return "[%s,%s,%s]" % (N,a,alpha)

def parse_points(K,s):
    r""" The database stores two lists of points (gens and torsion_gens),
    each a list of r lists of d strings.  This converts such a list
    into a list of r lists of 3 elements of K.
    """
    return [[K([QQ(str(a)) for a in c]) for c in P] for P in s]


def inflate_interval(a,b,r): 
    c=(a+b)/2
    d=(b-a)/2
    d*=r
    return (c-d,c+d)

def plot_zone_union(R,S):
    return(min(R[0],S[0]),max(R[1],S[1]),min(R[2],S[2]),max(R[3],S[3]))

# Finds a suitable plotting zone for the component a <= x <= b of the EC y**2+h(x)*y=f(x) 
def EC_R_plot_zone_piece(f,h,a,b):
    npts=50
    Y=[]
    g=f+h**2/4
    t=a
    s=(b-a)/npts
    for i in range(npts+1):
        y=g(t)
        if y>0:
            y=sqrt(y)
            w=h(t)/2
            Y.append(y-w)
            Y.append(-y-w)
        t+=s
    (ymin,ymax)=inflate_interval(min(Y),max(Y),1.2)
    (a,b)=inflate_interval(a,b,1.3)
    return (a,b,ymin,ymax)

# Finds a suitable plotting zone for the EC y**2+h(x)*y=f(x) 
def EC_R_plot_zone(f,h):
    F=f+h**2/4
    F1=F.derivative()
    F2=F1.derivative()
    G=F*F2-F1**2/2
    ZF=[z[0] for z in F.roots()]
    ZG=[z[0] for z in G.roots()]
    xi=max(ZG)
    if len(ZF)==1:
        return EC_R_plot_zone_piece(f,h,ZF[0],2*xi-ZF[0])
    if len(ZF)==3:
        return plot_zone_union(EC_R_plot_zone_piece(f,h,ZF[0],ZF[1]),EC_R_plot_zone_piece(f,h,ZF[2],2*xi-ZF[2]))
    return EC_R_plot_zone_piece(f,h,ZF[0],2*ZF[1]-ZF[0])

def EC_R_plot(ainvs, xmin, xmax, ymin, ymax, colour, legend):
    x = var('x')
    y = var('y')
    c = (xmin + xmax) / 2
    d = (xmax - xmin)
    return implicit_plot(y ** 2 + ainvs[0] * x * y + ainvs[2] * y - x ** 3 - ainvs[1] * x ** 2 - ainvs[3] * x - ainvs[4], (x, xmin, xmax), (y, ymin, ymax), plot_points=500, aspect_ratio="automatic", color=colour) + plot(0, xmin=c - 1e-5 * d, xmax=c + 1e-5 * d, ymin=ymin, ymax=ymax, aspect_ratio="automatic", color=colour, legend_label=legend)  # Add an extra plot outside the visible frame because implicit plots are buggy: their legend does not show (http://trac.sagemath.org/ticket/15903)

Rx=PolynomialRing(RDF,'x')

def EC_nf_plot(K, ainvs, base_field_gen_name):
    try:
        n1 = K.signature()[0]
        if n1 == 0:
            return plot([])
        R=[]
        S=K.embeddings(RDF)
        for s in S:
            A=[s(c) for c in ainvs]
            R.append(EC_R_plot_zone(Rx([A[4],A[3],A[1],1]),Rx([A[2],A[0]]))) 
        xmin = min([r[0] for r in R])
        xmax = max([r[1] for r in R])
        ymin = min([r[2] for r in R])
        ymax = max([r[3] for r in R])
        cols = rainbow(n1) # Default choice of n colours
        # However, these tend to be too pale, so we preset them for small values of n
        if n1==1:
            cols=["blue"]
        elif n1==2:
            cols=["red","blue"]
        elif n1==3:
            cols=["red","limegreen","blue"]
        elif n1==4:
            cols = ["red", "orange", "forestgreen", "blue"]
        elif n1==5:
            cols = ["red", "orange", "forestgreen", "blue", "darkviolet"]
        elif n1==6:
            cols = ["red", "darkorange", "gold", "forestgreen", "blue", "darkviolet"]
        elif n1==7:
            cols = ["red", "darkorange", "gold", "forestgreen", "blue", "darkviolet", "fuchsia"]
        return sum([EC_R_plot([S[i](c) for c in ainvs], xmin, xmax, ymin, ymax, cols[i], "$" + base_field_gen_name + " \mapsto$ " + str(S[i].im_gens()[0].n(20))+"$\dots$") for i in range(n1)]) 
    except:
        return text("Unable to plot", (1, 1), fontsize=36)

class ECNF(object):

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
        self.field = make_field(self.field_label)
        self.make_E()

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db_ecnf().find_one({"label": label})
        if data:
            return ECNF(data)
        print "No such curve in the database: %s" % label

    def make_E(self):
        coeffs = self.ainvs  # list of 5 lists of d strings
        self.ainvs = [self.field.parse_NFelt(x) for x in coeffs]
        self.latex_ainvs = web_latex(self.ainvs)
        #from sage.schemes.elliptic_curves.all import EllipticCurve
        #self.E = E = EllipticCurve(self.ainvs)
        self.numb = str(self.number)

        # Conductor, discriminant, j-invariant
        K = self.field.K()
        N = ideal_from_string(K,self.conductor_ideal)
        self.cond = web_latex(N)
        self.cond_norm = web_latex(self.conductor_norm)
        local_data = self.local_data
        print("local data:")
        print(local_data)
        # NB badprimes is a list of primes which divide the
        # discriminant of this model.  At most one of these might
        # actually be a prime of good reduction, if the curve has no
        # global minimal model.
        badprimes = [ideal_from_string(K,ld['p']) for ld in local_data]
        badnorms = [ZZ(ld['normp']) for ld in local_data]
        mindisc_ords = [ld['ord_disc'] for ld in local_data]

        # Assumption: the curve models stored in the database are
        # either global minimal models or minimal at all but one
        # prime, so the list here has length 0 or 1:

        self.non_min_primes = [ideal_from_string(K,P) for P in self.non_min_p]
        self.is_minimal = (len(self.non_min_primes) == 0)
        self.has_minimal_model = self.is_minimal
        disc_ords = [ld['ord_disc'] for ld in local_data]
        if not self.is_minimal:
            P = self.non_min_primes[0]
            P_index = bad_primes.index(P)
            self.non_min_prime = web_latex(P)
            disc_ords[P_index] += 12

        if self.conductor_norm == 1:  # since the factorization of (1) displays as "1"
            self.fact_cond = self.cond
            self.fact_cond_norm = self.cond
        else:
            Nfac = Factorization([(P,ld['ord_cond']) for P,ld in zip(badprimes,local_data)])
            self.fact_cond = web_latex_ideal_fact(Nfac)
            Nnormfac = Factorization([(q,ld['ord_cond']) for q,ld in zip(badnorms,local_data)])
            self.fact_cond_norm = web_latex(Nnormfac)

        # D is the discriminant ideal of the model
        D = prod([P**e for P,e in zip(badprimes,disc_ords)])
        self.disc = web_latex(D)
        Dnorm = D.norm()
        self.disc_norm = web_latex(Dnorm)
        if Dnorm == 1:  # since the factorization of (1) displays as "1"
            self.fact_disc = self.disc
            self.fact_disc_norm = self.disc
        else:
            Dfac = Factorization([(P,e) for P,e in zip(badprimes,disc_ords)])
            self.fact_disc = web_latex_ideal_fact(Dfac)
            Dnormfac = Factorization([(q,e) for q,e in zip(badnorms,disc_ords)])
            self.fact_disc_norm = web_latex(Dnormfac)


        if not self.is_minimal:
            Dmin = ideal_from_string(K,self.minD)
            self.mindisc = web_latex(Dmin)
            Dmin_norm = Dmin.norm()
            self.mindisc_norm = web_latex(Dmin_norm)
            if Dmin_norm == 1:  # since the factorization of (1) displays as "1"
                self.fact_mindisc = self.mindisc
                self.fact_mindisc_norm = self.mindisc
            else:
                Dminfac = Factorization([(P,e) for P,edd in zip(badprimes,min_disc_ords)])
                self.fact_mindisc = web_latex_ideal_fact(Dminfac)
                Dminnormfac = Factorization([(q,e) for q,e in zip(badnorms,min_disc_ords)])
                self.fact_mindisc_norm = web_latex(Dminnormfac)

        j = self.field.parse_NFelt(self.jinv)
        # if j:
        #     d = j.denominator()
        #     n = d * j  # numerator exists for quadratic fields only!
        #     g = GCD(list(n))
        #     n1 = n / g
        #     self.j = web_latex(n1)
        #     if d != 1:
        #         if n1 > 1:
        #         # self.j = "("+self.j+")\(/\)"+web_latex(d)
        #             self.j = web_latex(r"\frac{%s}{%s}" % (self.j, d))
        #         else:
        #             self.j = web_latex(d)
        #         if g > 1:
        #             if n1 > 1:
        #                 self.j = web_latex(g) + self.j
        #             else:
        #                 self.j = web_latex(g)
        self.j = web_latex(j)

        self.fact_j = None
        # See issue 1258: some j factorizations work but take too long
        # (e.g. EllipticCurve/6.6.371293.1/1.1/a/1)

        # We now have, and display, the valuations of the denominator
        # of j (at bad primes) so do not need to factor it anyway
        # (no-one needs the factorization of the numerator even if it
        # is possible).

        # CM and End(E)
        self.cm_bool = "no"
        self.End = "\(\Z\)"
        if self.cm:
            self.cm_bool = "yes (\(%s\))" % self.cm
            if self.cm % 4 == 0:
                d4 = ZZ(self.cm) // 4
                self.End = "\(\Z[\sqrt{%s}]\)" % (d4)
            else:
                self.End = "\(\Z[(1+\sqrt{%s})/2]\)" % self.cm
            # The line below will need to change once we have curves over non-quadratic fields
            # that contain the Hilbert class field of an imaginary quadratic field
            if self.signature == [0,1] and ZZ(-self.abs_disc*self.cm).is_square():
                self.ST = st_link_by_name(1,2,'U(1)')
            else:
                self.ST = st_link_by_name(1,2,'N(U(1))')
        else:
            self.ST = st_link_by_name(1,2,'SU(2)')

        # Q-curve / Base change
        self.qc = "no"
        try:
            if self.q_curve:
                self.qc = "yes"
        except AttributeError:  # in case the db entry does not have this field set
            pass

        # Torsion
        self.ntors = web_latex(self.torsion_order)
        self.tr = len(self.torsion_structure)
        if self.tr == 0:
            self.tor_struct_pretty = "Trivial"
        if self.tr == 1:
            self.tor_struct_pretty = "\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr == 2:
            self.tor_struct_pretty = r"\(\Z/%s\Z\times\Z/%s\Z\)" % tuple(self.torsion_structure)

        torsion_gens = parse_points(K,self.torsion_gens)
        self.torsion_gens = ",".join([web_point(P) for P in torsion_gens])

        # Rank or bounds
        try:
            self.rk = web_latex(self.rank)
        except AttributeError:
            self.rk = "?"
        try:
            self.rk_bnds = "%s...%s" % tuple(self.rank_bounds)
        except AttributeError:
            self.rank_bounds = [0, Infinity]
            self.rk_bnds = "not available"

        # Generators
        try:
            gens = parse_points(K,self.gens)
            self.gens = ", ".join([web_point(P) for P in gens])
            if self.rk == "?":
                self.reg = "not available"
            else:
                if gens:
                    self.reg = E.regulator_of_points(gens)
                else:
                    self.reg = 1  # otherwise we only get 1.00000...

        except AttributeError:
            self.gens = "not available"
            self.reg = "not available"
            try:
                if self.rank == 0:
                    self.reg = 1
            except AttributeError:
                pass

        # Local data
        for P,ld in zip(badprimes,local_data):
            ld['p'] = web_latex(P)
            ld['norm'] = P.norm()
            ld['kod'] = web_latex(ld['kod']).replace('$', '')

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

        sig = self.signature
        totally_real = sig[1] == 0
        imag_quadratic = sig == [0,1]

        if totally_real:
            self.hmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])
            self.urls['hmf'] = url_for('hmf.render_hmf_webpage', field_label=self.field.label, label=self.hmf_label)
            self.urls['Lfunction'] = url_for("l_functions.l_function_hmf_page", field=self.field_label, label=self.hmf_label, character='0', number='0')

        if imag_quadratic:
            self.bmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])

        self.friends = []
        self.friends += [('Isogeny class ' + self.short_class_label, self.urls['class'])]
        self.friends += [('Twists', url_for('ecnf.index', field=self.field_label, jinv=rename_j(j)))]
        if totally_real:
            self.friends += [('Hilbert Modular Form ' + self.hmf_label, self.urls['hmf'])]
            self.friends += [('L-function', self.urls['Lfunction'])]
        if imag_quadratic:
            self.friends += [('Bianchi Modular Form %s not available' % self.bmf_label, '')]

        self.properties = [
            ('Base field', self.field.field_pretty()),
            ('Label', self.label)]

        # Plot
        if K.signature()[0]:
            self.plot = encode_plot(EC_nf_plot(K,self.ainvs, self.field.generator_name()))
            self.plot_link = '<img src="%s" width="200" height="150"/>' % self.plot
            self.properties += [(None, self.plot_link)]

        self.properties += [
            ('Conductor', self.cond),
            ('Conductor norm', self.cond_norm),
            # See issue #796 for why this is hidden
            # ('j-invariant', self.j),
            ('CM', self.cm_bool)]

        if self.base_change:
            self.properties += [('base-change', 'yes: %s' % ','.join([str(lab) for lab in self.base_change]))]
        else:
            self.base_change = []  # in case it was False instead of []
            self.properties += [('Q-curve', self.qc)]

        r = self.rk
        if r == "?":
            r = self.rk_bnds
        self.properties += [
            ('Torsion order', self.ntors),
            ('Rank', r),
        ]

        for E0 in self.base_change:
            self.friends += [('Base-change of %s /\(\Q\)' % E0, url_for("ec.by_ec_label", label=E0))]

        self._code = None # will be set if needed by get_code()

    def code(self):
        if self._code == None:
            self.make_code_snippets()
        return self._code

    def make_code_snippets(self):
        # read in code.yaml from current directory:

        _curdir = os.path.dirname(os.path.abspath(__file__))
        self._code =  yaml.load(open(os.path.join(_curdir, "code.yaml")))

        # Fill in placeholders for this specific curve:

        gen = self.field.generator_name().replace("\\","") # phi not \phi
        for lang in ['sage', 'magma', 'pari']:
            self._code['field'][lang] = self._code['field'][lang] % self.field.poly()
            if gen != 'a':
                self._code['field'][lang] = self._code['field'][lang].replace("<a>","<%s>" % gen)
                self._code['field'][lang] = self._code['field'][lang].replace("a=","%s=" % gen)

        for lang in ['sage', 'magma', 'pari']:
            self._code['curve'][lang] = self._code['curve'][lang] % self.ainvs
