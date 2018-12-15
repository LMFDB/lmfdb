import os
import yaml
from flask import url_for
from urllib import quote
from sage.all import ZZ, var, PolynomialRing, QQ, RDF, rainbow, implicit_plot, plot, text, Infinity, sqrt, prod, Factorization
from lmfdb.db_backend import db
from lmfdb.utils import web_latex, web_latex_split_on, web_latex_ideal_fact, encode_plot
from lmfdb.WebNumberField import WebNumberField
from lmfdb.sato_tate_groups.main import st_link_by_name

# For backwards compatibility of labels of conductors (ideals) over
# imaginary quadratic fields we provide this conversion utility.  Labels have been of 3 types:
# 1. [N,c,d] with N=norm and [N/d,0;c,d] the HNF
# 2. N.c.d
# 3. N.i with N=norm and i the index in the standard list of ideals of norm N (per field).
#
# Converting 1->2 is trivial and 2->3 is done via a stored lookup
# table, which contains entries for the five Euclidean imaginary
# quadratic fields 2.0.d.1 for d in [4,8,3,7,11] and all N<=10000.
#

def convert_IQF_label(fld, lab):
    if fld.split(".")[:2] != ['2','0']:
        return lab
    newlab = lab
    if lab[0]=='[':
        newlab = lab[1:-1].replace(",",".")
    if len(newlab.split("."))!=3:
        return newlab
    newlab = db.ec_iqf_labels.lucky({'fld':fld, 'old':newlab}, projection = 'new')
    if newlab:
        if newlab!=lab:
            print("Converted label {} to {} over {}".format(lab, newlab, fld))
        return newlab
    return lab

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
    return '$\\left(%s\\right)$'%(" : ".join([str(latex(x)) for x in P]))

def ideal_from_string(K,s, IQF_format=False):
    r"""Returns the ideal of K defined by the string s.  If IQF_format is
    True, this is "[N,c,d]" with N,c,d as in a label, while otherwise
    it is of the form "[N,a,alpha]" where N is the norm, a the least
    positive integer in the ideal and alpha a second generator so that
    the ideal is (a,alpha).  alpha is a polynomial in the variable w
    which represents the generator of K (but may actually be an
    integer).  """
    #print("ideal_from_string({}) over {}".format(s,K))
    N, a, alpha = s[1:-1].split(",")
    N = ZZ(N)
    a = ZZ(a)
    if IQF_format:
        d = ZZ(alpha)
        I = K.ideal(N//d, K([a, d]))
    else:
        # 'w' is used for the generator name for all fields for
        # numbers stored in the database
        alpha = alpha.encode().replace('w',str(K.gen()))
        I = K.ideal(a,K(alpha.encode()))
    if I.norm()==N:
        return I
    else:
        return "wrong" ## caller must check

def pretty_ideal(I):
    easy = I.number_field().degree()==2 or I.norm()==1
    gens = I.gens_reduced() if easy else I.gens()
    return "\((" + ",".join([latex(g) for g in gens]) + ")\)"

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

def ideal_to_string(I,IQF_format=False):
    K = I.number_field()
    if IQF_format:
        a, c, d = ideal_HNF(I)
        return "[%s,%s,%s]" % (a * d, c, d)
    N = I.norm()
    a = I.smallest_integer()
    gens = I.gens_reduced()
    alpha = gens[-1]
    assert I == K.ideal(a,alpha)
    alpha = str(alpha).replace(str(K.gen()),'w')
    return ("[%s,%s,%s]" % (N,a,alpha)).replace(" ","")

def parse_point(K, s):
    r""" Returns a point in P^2(K) defined by the string s.  s has the form
    '[x,y,z]' where x, y, z have the form '[c0,c1,..]' with each ci
    representing a rational number.
    """
    #print("parse_point({})".format(s))
    cc = s[2:-2].replace("],[",":").split(":")
    return [K([QQ(ci.encode()) for ci in c.split(",")]) for c in cc]

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
        self.field = FIELD(self.field_label)
        self.non_surjective_primes = dbdata.get('non-surjective_primes',None)
        self.make_E()

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db.ec_nfcurves.lookup(label)
        if data:
            return ECNF(data)
        print "No such curve in the database: %s" % label

    def make_E(self):
        #print("Creating ECNF object for {}".format(self.label))
        #sys.stdout.flush()
        K = self.field.K()

        # a-invariants
        self.ainvs = parse_ainvs(K,self.ainvs)
        self.latex_ainvs = web_latex(self.ainvs)
        self.numb = str(self.number)

        # Conductor, discriminant, j-invariant
        if self.conductor_norm==1:
            N = K.ideal(1)
        else:
            N = ideal_from_string(K,self.conductor_ideal)
        # The following can trigger expensive computations!
        #self.cond = web_latex(N)
        self.cond = pretty_ideal(N)
        self.cond_norm = web_latex(self.conductor_norm)
        local_data = self.local_data

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
            Pmin = self.non_min_primes[0]
            P_index = badprimes.index(Pmin)
            self.non_min_prime = pretty_ideal(Pmin)
            disc_ords[P_index] += 12

        if self.conductor_norm == 1:  # since the factorization of (1) displays as "1"
            self.fact_cond = self.cond
            self.fact_cond_norm = '1'
        else:
            Nfac = Factorization([(P,ld['ord_cond']) for P,ld in zip(badprimes,local_data)])
            self.fact_cond = web_latex_ideal_fact(Nfac)
            Nnormfac = Factorization([(q,ld['ord_cond']) for q,ld in zip(badnorms,local_data)])
            self.fact_cond_norm = web_latex(Nnormfac)

        # D is the discriminant ideal of the model
        D = prod([P**e for P,e in zip(badprimes,disc_ords)], K.ideal(1))
        self.disc = pretty_ideal(D)
        Dnorm = D.norm()
        self.disc_norm = web_latex(Dnorm)
        if Dnorm == 1:  # since the factorization of (1) displays as "1"
            self.fact_disc = self.disc
            self.fact_disc_norm = '1'
        else:
            Dfac = Factorization([(P,e) for P,e in zip(badprimes,disc_ords)])
            self.fact_disc = web_latex_ideal_fact(Dfac)
            Dnormfac = Factorization([(q,e) for q,e in zip(badnorms,disc_ords)])
            self.fact_disc_norm = web_latex(Dnormfac)

        if not self.is_minimal:
            Dmin = ideal_from_string(K,self.minD)
            self.mindisc = pretty_ideal(Dmin)
            Dmin_norm = Dmin.norm()
            self.mindisc_norm = web_latex(Dmin_norm)
            if Dmin_norm == 1:  # since the factorization of (1) displays as "1"
                self.fact_mindisc = self.mindisc
                self.fact_mindisc_norm = self.mindisc
            else:
                Dminfac = Factorization([(P,e) for P,edd in zip(badprimes,mindisc_ords)])
                self.fact_mindisc = web_latex_ideal_fact(Dminfac)
                Dminnormfac = Factorization([(q,e) for q,e in zip(badnorms,mindisc_ords)])
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
        # (e.g. EllipticCurve/6.6.371293.1/1.1/a/1).  Note that we do
        # store the factorization of the denominator of j and display
        # that, which is the most interesting part.

        # Images of Galois representations

        if not hasattr(self,'galois_images'):
            #print "No Galois image data"
            self.galois_images = "?"
            self.non_surjective_primes = "?"
            self.galois_data = []
        else:
            self.galois_data = [{'p': p,'image': im }
                                for p,im in zip(self.non_surjective_primes,
                                                self.galois_images)]

        # CM and End(E)
        self.cm_bool = "no"
        self.End = "\(\Z\)"
        if self.cm:
            self.rational_cm = K(self.cm).is_square()
            self.cm_sqf = ZZ(self.cm).squarefree_part()
            self.cm_bool = "yes (\(%s\))" % self.cm
            if self.cm % 4 == 0:
                d4 = ZZ(self.cm) // 4
                self.End = "\(\Z[\sqrt{%s}]\)" % (d4)
            else:
                self.End = "\(\Z[(1+\sqrt{%s})/2]\)" % self.cm

        # Galois images in CM case:
        if self.cm and self.galois_images != '?':
            self.cm_ramp = [p for p in ZZ(self.cm).support() if not p in self.non_surjective_primes]
            self.cm_nramp = len(self.cm_ramp)
            if self.cm_nramp==1:
                self.cm_ramp = self.cm_ramp[0]
            else:
                self.cm_ramp = ", ".join([str(p) for p in self.cm_ramp])

        # Sato-Tate:
        # The lines below will need to change once we have curves over non-quadratic fields
        # that contain the Hilbert class field of an imaginary quadratic field
        if self.cm:
            if self.signature == [0,1] and ZZ(-self.abs_disc*self.cm).is_square():
                self.ST = st_link_by_name(1,2,'U(1)')
            else:
                self.ST = st_link_by_name(1,2,'N(U(1))')
        else:
            self.ST = st_link_by_name(1,2,'SU(2)')

        # Q-curve / Base change
        self.qc = self.q_curve
        if self.qc == "?":
            self.qc = "not determined"
        elif self.qc == True:
            self.qc = "yes"
        elif self.qc == False:
            self.qc = "no"
        else: # just in case
            self.qc = "not determined"

        # Torsion
        self.ntors = web_latex(self.torsion_order)
        self.tr = len(self.torsion_structure)
        if self.tr == 0:
            self.tor_struct_pretty = "Trivial"
        if self.tr == 1:
            self.tor_struct_pretty = "\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr == 2:
            self.tor_struct_pretty = r"\(\Z/%s\Z\times\Z/%s\Z\)" % tuple(self.torsion_structure)

        torsion_gens = [parse_point(K,P) for P in self.torsion_gens]
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
            gens = [parse_point(K,P) for P in self.gens]
            self.gens = ", ".join([web_point(P) for P in gens])
            if self.rk == "?":
                self.reg = "not available"
            else:
                if gens:
                    try:
                        self.reg = self.reg
                    except AttributeError:
                        self.reg = "not available"
                    pass # self.reg already set
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
            ld['kod'] = ld['kod'].replace('\\\\', '\\')
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

        # Isogeny information

        self.one_deg = ZZ(self.class_deg).is_prime()
        isodegs = [str(d) for d in self.isogeny_degrees if d>1]
        if len(isodegs)<3:
            self.isogeny_degrees = " and ".join(isodegs)
        else:
            self.isogeny_degrees = " and ".join([", ".join(isodegs[:-1]),isodegs[-1]])


        sig = self.signature
        totally_real = sig[1] == 0
        imag_quadratic = sig == [0,1]

        if totally_real:
            self.hmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])
            self.urls['hmf'] = url_for('hmf.render_hmf_webpage', field_label=self.field.label, label=self.hmf_label)
            if sig[0] <= 2:
                self.urls['Lfunction'] = url_for("l_functions.l_function_ecnf_page", field_label=self.field_label, conductor_label=self.conductor_label, isogeny_class_label=self.iso_label)
            elif self.abs_disc ** 2 * self.conductor_norm < 70000:
                # we shouldn't trust the Lfun computed on the fly for large conductor
                self.urls['Lfunction'] = url_for("l_functions.l_function_hmf_page", field=self.field_label, label=self.hmf_label, character='0', number='0')

        if imag_quadratic:
            self.bmf_label = "-".join([self.field.label, self.conductor_label, self.iso_label])
            self.bmf_url = url_for('bmf.render_bmf_webpage', field_label=self.field_label, level_label=self.conductor_label, label_suffix=self.iso_label)
            self.urls['Lfunction'] = url_for("l_functions.l_function_ecnf_page", field_label=self.field_label, conductor_label=self.conductor_label, isogeny_class_label=self.iso_label)

        self.friends = []
        self.friends += [('Isogeny class ' + self.short_class_label, self.urls['class'])]
        self.friends += [('Twists', url_for('ecnf.index', field=self.field_label, jinv=rename_j(j)))]
        if totally_real:
            self.friends += [('Hilbert Modular Form ' + self.hmf_label, self.urls['hmf'])]

        if imag_quadratic:
            if "CM" in self.label:
                self.friends += [('Bianchi Modular Form is not cuspidal', '')]
            else:
                if db.bmf_forms.label_exists(self.bmf_label):
                    self.friends += [('Bianchi Modular Form %s' % self.bmf_label, self.bmf_url)]
                else:
                    self.friends += [('(Bianchi Modular Form %s)' % self.bmf_label, '')]

        if 'Lfunction' in self.urls:
            self.friends += [('L-function', self.urls['Lfunction'])]
        else:
            self.friends += [('L-function not available', "")]

        self.properties = [
            ('Base field', self.field.field_pretty()),
            ('Label', self.label)]

        # Plot
        if K.signature()[0]:
            self.plot = encode_plot(EC_nf_plot(K,self.ainvs, self.field.generator_name()))
            self.plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)
            self.properties += [(None, self.plot_link)]

        self.properties += [
            ('Conductor', self.cond),
            ('Conductor norm', self.cond_norm),
            # See issue #796 for why this is hidden (can be very large)
            # ('j-invariant', self.j),
            ('CM', self.cm_bool)]

        if self.base_change:
            self.properties += [('base-change', 'yes: %s' % ','.join([str(lab) for lab in self.base_change]))]
        else:
            self.base_change = []  # in case it was False instead of []
            self.properties += [('base-change', 'no')]
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

        self.downloads = [('Download all stored data', url_for(".download_ECNF_all", nf=self.field_label, conductor_label=quote(self.conductor_label), class_label=self.iso_label, number=self.number))]
        for lang in [["Magma","magma"], ["SageMath","sage"], ["GP", "gp"]]:
            self.downloads.append(('Download {} code'.format(lang[0]),
                                   url_for(".ecnf_code_download", nf=self.field_label, conductor_label=quote(self.conductor_label),
                                           class_label=self.iso_label, number=self.number, download_type=lang[1])))



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
            pol = str(self.field.poly())
            if lang=='pari':
                pol = pol.replace('x',gen)
            elif lang=='magma':
                pol = str(self.field.poly().list())
            self._code['field'][lang] = (self._code['field'][lang] % pol).replace("<a>", "<%s>" % gen)

        for lang in ['sage', 'magma', 'pari']:
            self._code['curve'][lang] = self._code['curve'][lang] % self.ainvs
