import os
import yaml
from flask import url_for
from urllib import quote
from sage.all import ZZ, var, PolynomialRing, QQ, GCD, RR, rainbow, implicit_plot, plot, text, Infinity, sqrt
from lmfdb.base import app, getDBConnection
from lmfdb.utils import image_src, web_latex, web_latex_ideal_fact, encode_plot
from lmfdb.WebNumberField import WebNumberField
from kraus import (non_minimal_primes, is_global_minimal_model, has_global_minimal_model, minimal_discriminant_ideal)

ecnf = None
nfdb = None

def db_ecnf():
    global ecnf
    if ecnf is None:
        ecnf = getDBConnection().elliptic_curves.nfcurves
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

Rx=PolynomialRing(RR,'x')

def EC_nf_plot(E, base_field_gen_name):
    try:
        K = E.base_field()
        n1 = K.signature()[0]
        if n1 == 0:
            return plot([])
        R=[]
        S=K.embeddings(RR)
        for s in S:
            A=[s(c) for c in E.ainvs()]
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
        return sum([EC_R_plot([S[i](c) for c in E.ainvs()], xmin, xmax, ymin, ymax, cols[i], "$" + base_field_gen_name + " \mapsto$ " + str(S[i].im_gens()[0].n(20))+"$\dots$") for i in range(n1)]) 
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
        from sage.schemes.elliptic_curves.all import EllipticCurve
        self.E = E = EllipticCurve(self.ainvs)
        self.equn = web_latex(E)
        self.numb = str(self.number)

        # Conductor, discriminant, j-invariant
        N = E.conductor()
        self.cond = web_latex(N)
        self.cond_norm = web_latex(N.norm())
        if N.norm() == 1:  # since the factorization of (1) displays as "1"
            self.fact_cond = self.cond
        else:
            self.fact_cond = web_latex_ideal_fact(N.factor())
        self.fact_cond_norm = web_latex(N.norm().factor())

        D = self.field.K().ideal(E.discriminant())
        self.disc = web_latex(D)
        self.disc_norm = web_latex(D.norm())
        if D.norm() == 1:  # since the factorization of (1) displays as "1"
            self.fact_disc = self.disc
        else:
            self.fact_disc = web_latex_ideal_fact(D.factor())
        self.fact_disc_norm = web_latex(D.norm().factor())

        # Minimal model?
        #
        # All curves in the database should be given
        # by models which are globally minimal if possible, else
        # minimal at all but one prime.  But we do not rely on this
        # here, and the display should be correct if either (1) there
        # exists a global minimal model but this model is not; or (2)
        # this model is non-minimal at more than one prime.
        #
        self.non_min_primes = non_minimal_primes(E)
        self.is_minimal = (len(self.non_min_primes) == 0)
        self.has_minimal_model = True
        if not self.is_minimal:
            self.non_min_prime = ','.join([web_latex(P) for P in self.non_min_primes])
            self.has_minimal_model = has_global_minimal_model(E)

        if not self.is_minimal:
            Dmin = minimal_discriminant_ideal(E)
            self.mindisc = web_latex(Dmin)
            self.mindisc_norm = web_latex(Dmin.norm())
            if Dmin.norm() == 1:  # since the factorization of (1) displays as "1"
                self.fact_mindisc = self.mindisc
            else:
                self.fact_mindisc = web_latex_ideal_fact(Dmin.factor())
            self.fact_mindisc_norm = web_latex(Dmin.norm().factor())

        j = E.j_invariant()
        if j:
            d = j.denominator()
            n = d * j  # numerator exists for quadratic fields only!
            g = GCD(list(n))
            n1 = n / g
            self.j = web_latex(n1)
            if d != 1:
                if n1 > 1:
                # self.j = "("+self.j+")\(/\)"+web_latex(d)
                    self.j = web_latex(r"\frac{%s}{%s}" % (self.j, d))
                else:
                    self.j = web_latex(d)
                if g > 1:
                    if n1 > 1:
                        self.j = web_latex(g) + self.j
                    else:
                        self.j = web_latex(g)
        self.j = web_latex(j)

        self.fact_j = None
        # See issue 1258: some j factorizations work bu take too long (e.g. EllipticCurve/6.6.371293.1/1.1/a/1)
        # If these are really wanted, they could be precomputed and stored in the db
        if j.is_zero():
            self.fact_j = web_latex(j)
        else:
            if self.field.K().degree() < 3: #j.numerator_ideal().norm()<1000000000000:
                try:
                    self.fact_j = web_latex(j.factor())
                except (ArithmeticError, ValueError):  # if not all prime ideal factors principal
                    pass

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
                self.ST = '<a href="%s">$%s$</a>' % (url_for('st.by_label', label='1.2.U(1)'),'\\mathrm{U}(1)')
            else:
                self.ST = '<a href="%s">$%s$</a>' % (url_for('st.by_label', label='1.2.N(U(1))'),'N(\\mathrm{U}(1))')
        else:
            self.ST = '<a href="%s">$%s$</a>' % (url_for('st.by_label', label='1.2.SU(2)'),'\\mathrm{SU}(2)')

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
        torsion_gens = [E([self.field.parse_NFelt(x) for x in P])
                        for P in self.torsion_gens]
        self.torsion_gens = ",".join([web_latex(P) for P in torsion_gens])

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
            gens = [E([self.field.parse_NFelt(x) for x in P])
                    for P in self.gens]
            self.gens = ", ".join([web_latex(P) for P in gens])
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
        self.local_data = []
        for p in N.prime_factors():
            self.local_info = E.local_data(p, algorithm="generic")
            self.local_data.append({'p': web_latex(p),
                                    'norm': web_latex(p.norm().factor()),
                                    'tamagawa_number': self.local_info.tamagawa_number(),
                                    'kodaira_symbol': web_latex(self.local_info.kodaira_symbol()).replace('$', ''),
                                    'reduction_type': self.local_info.bad_reduction_type(),
                                    'ord_den_j': max(0, -E.j_invariant().valuation(p)),
                                    'ord_mindisc': self.local_info.discriminant_valuation(),
                                    'ord_cond': self.local_info.conductor_valuation()
                                    })

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
        real_quadratic = sig == [2,0]
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
        self.friends += [('Twists', url_for('ecnf.index', field_label=self.field_label, jinv=self.jinv))]
        if totally_real:
            self.friends += [('Hilbert Modular Form ' + self.hmf_label, self.urls['hmf'])]
            self.friends += [('L-function', self.urls['Lfunction'])]
        if imag_quadratic:
            self.friends += [('Bianchi Modular Form %s not available' % self.bmf_label, '')]

        self.properties = [
            ('Base field', self.field.field_pretty()),
            ('Label', self.label)]

        # Plot
        if E.base_field().signature()[0]:
            self.plot = encode_plot(EC_nf_plot(E, self.field.generator_name()))
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
