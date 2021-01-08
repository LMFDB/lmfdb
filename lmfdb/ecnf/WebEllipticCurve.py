from __future__ import print_function
import os
import yaml
from flask import url_for
from six.moves.urllib_parse import quote
from sage.all import (Factorization, Infinity, PolynomialRing, QQ, RDF, ZZ,
                      implicit_plot, plot, prod, rainbow, sqrt, text, var)
from lmfdb import db
from lmfdb.utils import (encode_plot, names_and_urls, web_latex,
                         web_latex_split_on)
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.lfunctions.LfunctionDatabase import (get_lfunction_by_url,
                                        get_instances_by_Lhash_and_trace_hash)

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
    # if newlab and newlab!=lab:
    #     print("Converted label {} to {} over {}".format(lab, newlab, fld))
    return newlab if newlab else lab

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

def ideal_from_string(K,s):
    r"""Returns the ideal of K defined by the string s.

    Either: s has the form "[N,a,alpha]" where N is the norm, a the
    least positive integer in the ideal and alpha a second generator
    so that the ideal is (a,alpha).

    Or: s has the form "(g1)" or "(g1,g2)" or "(g1,g2,g3)", ... where
    the gi are ideal generators.

    alpha and the gi are polynomials in the variable 'w' which
    represents the generator of K.

    """
    #print("ideal_from_string({}) over {}".format(s,K))

    gens = s.replace('w',str(K.gen()))[1:-1].split(",")

    if s[0] == "[":
        N = ZZ(gens[0])
        a = ZZ(gens[1])
        alpha = K(gens[2])
        I = K.ideal(a,alpha)
        return I if I.norm()==N else "wrong" ## caller must check
    return K.ideal([K(g) for g in gens])
    
def pretty_ideal_from_string(K, s, enclose=True, simplify=False):
    r"""Returns the a latex string an ideal of K defined by the string s,
    where Kgen is a strong representing the generator of K.  NB 'w' is
    used for the generator name for all fields for numbers stored in
    the database, and elements of K within the string s are
    polynomials in 'w'.

    Either: s has the form "[N,a,alpha]" where N is the norm, a the
    least positive integer in the ideal and alpha a second generator
    so that the ideal is (a,alpha).

    Or: s has the form "(g1)" or "(g1,g2)" or "(g1,g2,g3)", ... where
    the gi are ideal generators.

    alpha and the gi are polynomials in the variable w which
    represents the generator of K.

    If enclose==True (default) then latex math delimiters are pre- and
    appended.

    If simplify=True then we construct the actual ideal and compute
    its reduced_gens, so in particular principal ideals will be shown
    with one generator; otherwise the given generators are used
    without change (except that repeats are eliminated).  This is a
    temporary measure until we change what is stored in the database
    to always represent ideals in reduced form.
    """
    start = 1
    if s[0]=="[":
        start += s.find(",")
        if ZZ(s[1:start-1])==1:
            return r"\((1)\)" if enclose else "(1)"
    s = s[start:-1].replace('w',str(K.gen()))
    # remove repeats from the list of gens
    gens = s.split(",")
    if len(gens)>1 and gens[0]==gens[1]:
        gens=gens[1:]
    if simplify:
        gens = [str(rg) for rg in K.ideal([K(g) for g in gens]).gens_reduced()]
    gens = "(" + ",".join(gens) + ")"
    gens = gens.replace("*","")
    return r"\(" + gens + r"\)" if enclose else gens
    
def pretty_ideal(I, enclose=True, simplify=False):
    gens = I.gens_reduced() if simplify else I.gens()
    gens = "(" + ",".join([latex(g) for g in gens]) + r")"
    return r"\(" + gens + r"\)" if enclose else gens

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
        return sum([EC_R_plot([S[i](c) for c in ainvs], xmin, xmax, ymin, ymax, cols[i], "$" + base_field_gen_name + r" \mapsto$ " + str(S[i].im_gens()[0].n(20)) + r"$\dots$") for i in range(n1)])
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
        return "Elliptic curve not found: %s" % label # caller must check for this

    def make_E(self):
        #print("Creating ECNF object for {}".format(self.label))
        #sys.stdout.flush()
        K = self.field.K()
        
        # This flag controls whether ideals are reduced before display
        # (conductor, discriminant/minimial discriminant, bad primes)
        simplify_ideals = self.field.class_number()==1 or self.field.degree()<4
        
        # a-invariants
        self.ainvs = parse_ainvs(K,self.ainvs)
        self.latex_ainvs = web_latex(self.ainvs)
        self.numb = str(self.number)

        # Conductor, discriminant, j-invariant

        self.cond_norm = web_latex(self.conductor_norm)

        local_data = self.local_data

        badprimes = [pretty_ideal_from_string(K, ld['p'], enclose=False, simplify=simplify_ideals) for ld in local_data]
        badnorms = [ZZ(ld['normp']) for ld in local_data]
        mindisc_ords = [ld['ord_disc'] for ld in local_data]

        if self.conductor_norm==1:
            self.cond = r"\((1)\)"
            self.fact_cond = self.cond
            self.fact_cond_norm = '1'
        else:
            exponents = [ld['ord_cond'] for ld in local_data]
            self.cond = pretty_ideal_from_string(K, self.conductor_ideal, simplify=simplify_ideals)
            factors = ["{}^{{{}}}".format(q,n) if n>1 else "{}".format(q) if n>0 else "" for q,n in zip(badprimes, exponents)]
            factors = [f for f in factors if f] # there may be an exponent of 0
            self.fact_cond = r"\({}\)".format("".join(factors))
            Nnormfac = Factorization([(q,ld['ord_cond']) for q,ld in zip(badnorms,local_data)])
            self.fact_cond_norm = web_latex(Nnormfac)

        # Assumption: the curve models stored in the database are
        # either global minimal models or minimal at all but one
        # prime, so the list here has length 0 or 1:

        self.non_min_primes = [ideal_from_string(K,P) for P in self.non_min_p]
        self.is_minimal = (len(self.non_min_p) == 0)
        self.has_minimal_model = self.is_minimal
        disc_ords = [ld['ord_disc'] for ld in local_data]
        Dnorm_factor = 1   # N(disc)/N(min-disc)
        if not self.is_minimal:
            self.non_min_prime = pretty_ideal_from_string(K, self.non_min_p[0], simplify=simplify_ideals)
            ip = [ld['p'] for ld in local_data].index(self.non_min_p[0])
            Dnorm_factor = local_data[ip]['normp']**12
            disc_ords[ip] += 12

        self.mindisc = pretty_ideal_from_string(K, self.minD, simplify=simplify_ideals)
        # We currently do not store the norm of the minimal
        # discriminant ideal, but it is inside its string:
        Dmin = None
        if self.minD[0]=="[":
            Dmin_norm = ZZ(self.minD[1:self.minD.find(",")])
        else:
            Dmin = ideal_from_string(K,self.minD)
            Dmin_norm = Dmin.norm()
        self.mindisc_norm = web_latex(Dmin_norm)
        if Dmin_norm == 1:  # since the factorization of (1) displays as "1"
            self.fact_mindisc = self.mindisc
            self.fact_mindisc_norm = self.mindisc_norm
        else:
            factors = ["{}^{{{}}}".format(q,n) if n>1 else "{}".format(q) if n>0 else "" for q,n in zip(badprimes, mindisc_ords)]
            factors = [f for f in factors if f] # there may be an exponent of 0
            self.fact_mindisc = r"\({}\)".format("".join(factors))
            Dminnormfac = Factorization(list(zip(badnorms,mindisc_ords)))
            self.fact_mindisc_norm = web_latex(Dminnormfac)

        # D is the discriminant ideal of the model.  This is not
        # currently stored so if different from the minimal
        # discriminant ideal we need to compute it for display:
        if self.is_minimal:
            self.disc = self.mindisc
            self.disc_norm = self.mindisc_norm
            self.fact_disc = self.fact_mindisc
            self.fact_disc_norm = self.fact_mindisc_norm
        else:
            # we may have already computed Dmin
            if not Dmin:
                Dmin = ideal_from_string(K,self.minD)
            # The next three lines involve computation which we would
            # like to avoid, and will be able to when we store the
            # model discriminant in the database:
            P = ideal_from_string(K, self.non_min_p[0])
            D = Dmin * P**12
            self.disc = pretty_ideal(D, simplify=simplify_ideals)
            Dnorm = Dmin_norm * Dnorm_factor
            self.disc_norm = web_latex(Dnorm)
            if Dnorm == 1:  # since the factorization of (1) displays as "1"
                self.fact_disc = self.disc
                self.fact_disc_norm = '1'
            else:
                factors = [r"{}^{{{}}}".format(q,n) if n>1 else "{}".format(q) if n>0 else "" for q,n in zip(badprimes, disc_ords)]
                factors = [f for f in factors if f] # there may be an exponent of 0
                self.fact_disc = r"\({}\)".format("".join(factors))
                Dnormfac = Factorization([(q,e) for q,e in zip(badnorms,disc_ords)])
                self.fact_disc_norm = web_latex(Dnormfac)

        j = self.field.parse_NFelt(self.jinv)
        self.j = web_latex(j)
        self.fact_j = None
        # See issue 1258: some j factorizations work but take too long
        # (e.g. EllipticCurve/6.6.371293.1/1.1/a/1).  Note that we do
        # store the factorization of the denominator of j and display
        # that, which is the most interesting part.

        # The equation is stored in the database as a latex string.
        # Some of these have extraneous double quotes at beginning and
        # end, shich we fix here.  We also strip out initial \( and \)
        # (if present) which are added in the template.
        self.equation = self.equation.replace('"','').replace('\\(','').replace('\\)','')

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
        self.End = r"\(\Z\)"
        if self.cm:
            # When we switch to storing rational cm by having |D| in
            # the column, change the following lines:
            if self.cm>0:
                self.rational_cm = True
                self.cm = -self.cm
            else:
                self.rational_cm = K(self.cm).is_square()
            self.cm_sqf = ZZ(self.cm).squarefree_part()
            self.cm_bool = r"yes (\(%s\))" % self.cm
            if self.cm % 4 == 0:
                d4 = ZZ(self.cm) // 4
                self.End = r"\(\Z[\sqrt{%s}]\)" % (d4)
            else:
                self.End = r"\(\Z[(1+\sqrt{%s})/2]\)" % self.cm

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

        # Torsion
        self.ntors = web_latex(self.torsion_order)
        self.tr = len(self.torsion_structure)
        if self.tr == 0:
            self.tor_struct_pretty = "trivial"
        if self.tr == 1:
            self.tor_struct_pretty = r"\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr == 2:
            self.tor_struct_pretty = r"\(\Z/%s\Z\times\Z/%s\Z\)" % tuple(self.torsion_structure)

        self.torsion_gens = [web_point(parse_point(K,P)) for P in self.torsion_gens]

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
        assert self.rk=="not available" or (self.rk_lb==self.rank          and self.rank         ==self.rk_ub)
        assert self.ar=="not available" or (self.rk_lb<=self.analytic_rank and self.analytic_rank<=self.rk_ub)

        self.bsd_status = "incomplete"
        if self.analytic_rank != None:
            if self.rk_lb==self.rk_ub:
                self.bsd_status = "unconditional"
            elif self.rk_lb==self.analytic_rank:
                self.bsd_status = "conditional"
            else:
                self.bsd_status = "missing_gens"


        # Regulator only in conditional/unconditional cases, or when we know the rank:
        if self.bsd_status in ["conditional", "unconditional"]:
            if self.ar == 0:
                self.reg = web_latex(1)  # otherwise we only get 1.00000...
            else:
                try:
                    self.reg = web_latex(self.reg)
                except AttributeError:
                    self.reg = "not available"
        elif self.rk != "not available":
            self.reg = web_latex(self.reg) if self.rank else web_latex(1)
        else:
            self.reg = "not available"

        # Generators
        try:
            self.gens = [web_point(parse_point(K, P)) for P in self.gens]
        except AttributeError:
            self.gens = []

        # Global period
        try:
            self.omega = web_latex(self.omega)
        except AttributeError:
            self.omega = "not available"

        # L-value
        try:
            r = int(self.analytic_rank)
            # lhs = "L(E,1) = " if r==0 else "L'(E,1) = " if r==1 else "L^{{({})}}(E,1)/{}! = ".format(r,r)
            self.Lvalue = "\\(" + str(self.Lvalue) + "\\)" 
        except (TypeError, AttributeError):
            self.Lvalue = "not available"
            
        # Tamagawa product
        tamagawa_numbers = [ZZ(_ld['cp']) for _ld in self.local_data]
        cp_fac = [cp.factor() for cp in tamagawa_numbers]
        cp_fac = [latex(cp) if len(cp)<2 else '('+latex(cp)+')' for cp in cp_fac]
        if len(cp_fac)>1:
            self.tamagawa_factors = r'\cdot'.join(cp_fac)
        else:
            self.tamagawa_factors = None
        self.tamagawa_product = web_latex(prod(tamagawa_numbers,1))

        # Analytic Sha
        try:
            self.sha = web_latex(self.sha) + " (rounded)"
        except AttributeError:
            self.sha = "not available"
            
        
        # Local data

        # Fix for Kodaira symbols, which in the database start and end
        # with \( and \) and may have multiple backslashes.  Note that
        # to put a single backslash into a python string you have to
        # use '\\' which will display as '\\' but only counts as one
        # character in the string.  which are added in the template.
        def tidy_kod(kod):
            while '\\\\' in kod:
                kod = kod.replace('\\\\', '\\')
            kod = kod.replace('\\(','').replace('\\)','')
            return kod

        for P,NP,ld in zip(badprimes, badnorms, local_data):
            ld['p'] = P
            ld['norm'] = NP
            ld['kod'] = tidy_kod(ld['kod'])

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
        isodegs = [str(d) for d in self.isodeg if d>1]
        if len(isodegs)<3:
            self.isodeg = " and ".join(isodegs)
        else:
            self.isodeg = " and ".join([", ".join(isodegs[:-1]),isodegs[-1]])


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
        if totally_real and not 'Lfunction' in self.urls:
            self.friends += [('Hilbert modular form ' + self.hmf_label, self.urls['hmf'])]

        if imag_quadratic:
            if "CM" in self.label:
                self.friends += [('Bianchi modular form is not cuspidal', '')]
            elif not 'Lfunction' in self.urls:
                if db.bmf_forms.label_exists(self.bmf_label):
                    self.friends += [('Bianchi modular form %s' % self.bmf_label, self.bmf_url)]
                else:
                    self.friends += [('(Bianchi modular form %s)' % self.bmf_label, '')]


        self.properties = [('Label', self.label)]

        # Plot
        if K.signature()[0]:
            self.plot = encode_plot(EC_nf_plot(K,self.ainvs, self.field.generator_name()))
            self.plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)
            self.properties += [(None, self.plot_link)]
        self.properties += [('Base field', self.field.field_pretty())]

        self.properties += [
            ('Conductor', self.cond),
            ('Conductor norm', self.cond_norm),
            # See issue #796 for why this is hidden (can be very large)
            # ('j-invariant', self.j),
            ('CM', self.cm_bool)]

        if self.base_change:
            self.properties += [('Base change', 'yes: %s' % ','.join([str(lab) for lab in self.base_change]))]
        else:
            self.base_change = []  # in case it was False instead of []
            self.properties += [('Base change', 'no')]
        self.properties += [('Q-curve', self.qc)]

        r = self.rk
        if r == "?":
            r = self.rk_bnds
        self.properties += [
            ('Torsion order', self.ntors),
            ('Rank', r),
        ]

        for E0 in self.base_change:
            self.friends += [(r'Base change of %s /\(\Q\)' % E0, url_for("ec.by_ec_label", label=E0))]

        self._code = None # will be set if needed by get_code()

        self.downloads = [('All stored data to text', url_for(".download_ECNF_all", nf=self.field_label, conductor_label=quote(self.conductor_label), class_label=self.iso_label, number=self.number))]
        for lang in [["Magma","magma"], ["SageMath","sage"], ["GP", "gp"]]:
            self.downloads.append(('Code to {}'.format(lang[0]),
                                   url_for(".ecnf_code_download", nf=self.field_label, conductor_label=quote(self.conductor_label),
                                           class_label=self.iso_label, number=self.number, download_type=lang[1])))


        if 'Lfunction' in self.urls:
            Lfun = get_lfunction_by_url(self.urls['Lfunction'].lstrip('/L').rstrip('/'), projection=['degree', 'trace_hash', 'Lhash'])
            if Lfun is None:
                self.friends += [('L-function not available', "")]
            else:
                instances = get_instances_by_Lhash_and_trace_hash(
                    Lfun['Lhash'],
                    Lfun['degree'],
                    Lfun.get('trace_hash'))
                exclude={elt[1].rstrip('/').lstrip('/') for elt in self.friends
                         if elt[1]}
                self.friends += names_and_urls(instances, exclude=exclude)
                self.friends += [('L-function', self.urls['Lfunction'])]
        else:
            self.friends += [('L-function not available', "")]

    def code(self):
        if self._code is None:
            self.make_code_snippets()
        return self._code

    def make_code_snippets(self):
        # read in code.yaml from current directory:

        _curdir = os.path.dirname(os.path.abspath(__file__))
        self._code =  yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)

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
