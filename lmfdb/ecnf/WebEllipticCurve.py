from flask import url_for
from sage.all import ZZ, var, PolynomialRing, QQ, GCD, RealField, rainbow, implicit_plot, plot, text
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

field_list = {} # cached collection of enhanced WebNumberFields, keyed by label

def FIELD(label):
    nf = WebNumberField(label, gen_name=special_names.get(label, 'a'))
    nf.parse_NFelt = lambda s: nf.K()([QQ(str(c)) for c in s])
    return nf

def make_field(label):
    if label in field_list:
        return field_list[label]
    return FIELD(label)

def EC_R_plot(ainvs,xmin,xmax,ymin,ymax,colour,legend):
   x=var('x')
   y=var('y')
   c=(xmin+xmax)/2
   d=(xmax-xmin)
   return implicit_plot(y**2+ainvs[0]*x*y+ainvs[2]*y-x**3-ainvs[1]*x**2-ainvs[3]*x-ainvs[4],(x,xmin,xmax),(y,ymin,ymax),plot_points=1000,aspect_ratio="automatic",color=colour)+plot(0,xmin=c-1e-5*d,xmax=c+1e-5*d,ymin=ymin,ymax=ymax,aspect_ratio="automatic",color=colour,legend_label=legend) # Add an extra plot outside the visible frame because implicit plots are buggy: their legend does not show (http://trac.sagemath.org/ticket/15903) 

def EC_nf_plot(E,base_field_gen_name):
    K = E.base_field()
    n1 = K.signature()[0]
    if n1 == 0:
        return plot([])
    prec = 53
    maxprec = 10**6
    while prec < maxprec: # Try to base change to R. May fail if resulting curve is almost singular, so increase precision.
        try:
            SR = K.embeddings(RealField(prec))
            X = [E.base_extend(s) for s in SR]
            break
        except ArithmeticError:
            prec *= 2
    if prec >= maxprec:
        return text("Unable to plot",(1,1),fontsize="xx-large")
    X = [e.plot() for e in X]
    xmin = min([x.xmin() for x in X])
    xmax = max([x.xmax() for x in X])
    ymin = min([x.ymin() for x in X])
    ymax = max([x.ymax() for x in X])
    cols = ["blue","red","green","orange","brown"] # Preset colours, because rainbow tends to return too pale ones
    if n1 > len(cols):
        cols = rainbow(n1)
    return sum([EC_R_plot([SR[i](a) for a in E.ainvs()],xmin,xmax,ymin,ymax,cols[i],"$"+base_field_gen_name+" \mapsto$ "+str(SR[i].im_gens()[0].n(20))) for i in range(n1)])

class ECNF(object):
    """
    ECNF Wrapper
    """

    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        #del dbdata["_id"]
        self.__dict__.update(dbdata)
        self.field = make_field(self.field_label)
        self.make_E()

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db_ecnf().find_one({"label" : label})
        if data:
            return ECNF(data)
        print "No such curve in the database: %s" % label

    def make_E(self):
        coeffs = self.ainvs # list of 5 lists of d strings
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
        if N.norm()==1:  # since the factorization of (1) displays as "1"
            self.fact_cond = self.cond
        else:
            self.fact_cond = web_latex_ideal_fact(N.factor())
        self.fact_cond_norm = web_latex(N.norm().factor())

        D = self.field.K().ideal(E.discriminant())
        self.disc = web_latex(D)
        self.disc_norm = web_latex(D.norm())
        if D.norm()==1:  # since the factorization of (1) displays as "1"
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
        self.is_minimal = (len(self.non_min_primes)==0)
        self.has_minimal_model = True
        if not self.is_minimal:
            self.non_min_prime = ','.join([web_latex(P) for P in self.non_min_primes])
            self.has_minimal_model = has_global_minimal_model(E)

        if not self.is_minimal:
            Dmin = minimal_discriminant_ideal(E)
            self.mindisc = web_latex(Dmin)
            self.mindisc_norm = web_latex(Dmin.norm())
            if Dmin.norm()==1:  # since the factorization of (1) displays as "1"
                self.fact_mindisc = self.mindisc
            else:
                self.fact_mindisc = web_latex_ideal_fact(Dmin.factor())
            self.fact_mindisc_norm = web_latex(Dmin.norm().factor())


        j = E.j_invariant()
        if j:
            d = j.denominator()
            n = d*j # numerator exists for quadratic fields only!
            g = GCD(list(n))
            n1 = n/g
            self.j = web_latex(n1)
            if d!=1:
                if n1>1:
                #self.j = "("+self.j+")\(/\)"+web_latex(d)
                    self.j = web_latex(r"\frac{%s}{%s}" % (self.j,d))
                else:
                    self.j = web_latex(d)
                if g>1:
                    if n1>1:
                        self.j = web_latex(g) + self.j
                    else:
                        self.j = web_latex(g)
        self.j = web_latex(j)

        self.fact_j = None
        if j.is_zero():
            self.fact_j = web_latex(j)
        else:
            try:
                self.fact_j = web_latex(j.factor())
            except (ArithmeticError,ValueError): # if not all prime ideal factors principal
                pass

        # CM and End(E)
        self.cm_bool = "no"
        self.End = "\(\Z\)"
        if self.cm:
            self.cm_bool = "yes (\(%s\))" % self.cm
            if self.cm%4==0:
                d4 = ZZ(self.cm)//4
                self.End = "\(\Z[\sqrt{%s}]\)"%(d4)
            else:
                self.End = "\(\Z[(1+\sqrt{%s})/2]\)" % self.cm

        # Q-curve / Base change
        self.qc = "no"
        try:
            if self.q_curve:
                self.qc = "yes"
        except AttributeError: # in case the db entry does not have this field set
            pass

        # Torsion
        self.ntors = web_latex(self.torsion_order)
        self.tr = len(self.torsion_structure)
        if self.tr==0:
            self.tor_struct_pretty = "Trivial"
        if self.tr==1:
            self.tor_struct_pretty = "\(\Z/%s\Z\)" % self.torsion_structure[0]
        if self.tr==2:
            self.tor_struct_pretty = r"\(\Z/%s\Z\times\Z/%s\Z\)" % tuple(self.torsion_structure)
        torsion_gens = [E([self.field.parse_NFelt(x) for x in P])
                        for P in self.torsion_gens]
        self.torsion_gens = ",".join([web_latex(P) for P in torsion_gens])


        # Rank etc
        try:
            self.rk = web_latex(self.rank)
        except AttributeError:
            self.rk = "not recorded"
#       if rank in self:
#            self.r = web_latex(self.rank)

        # Local data
        self.local_data = []
        for p in N.prime_factors():
            self.local_info = E.local_data(p, algorithm="generic")
            self.local_data.append({'p': web_latex(p),
                               'norm': web_latex(p.norm().factor()),
                               'tamagawa_number': self.local_info.tamagawa_number(),
                               'kodaira_symbol': web_latex(self.local_info.kodaira_symbol()).replace('$', ''),
                               'reduction_type': self.local_info.bad_reduction_type(),
                                'ord_den_j': max(0,-E.j_invariant().valuation(p)),
                                'ord_mindisc': self.local_info.discriminant_valuation(),
                                'ord_cond': self.local_info.conductor_valuation()
                               })

        # URLs of self and related objects:
        self.urls = {}
        self.urls['curve'] = url_for(".show_ecnf", nf = self.field_label, conductor_label=self.conductor_label, class_label = self.iso_label, number = self.number)
        self.urls['class'] = url_for(".show_ecnf_isoclass", nf = self.field_label, conductor_label=self.conductor_label, class_label = self.iso_label)
        self.urls['conductor'] = url_for(".show_ecnf_conductor", nf = self.field_label, conductor_label=self.conductor_label)
        self.urls['field'] = url_for(".show_ecnf1", nf=self.field_label)

        if self.field.is_real_quadratic():
            self.hmf_label = "-".join([self.field.label,self.conductor_label,self.iso_label])
            self.urls['hmf'] = url_for('hmf.render_hmf_webpage', field_label=self.field.label, label=self.hmf_label)

        if self.field.is_imag_quadratic():
            self.bmf_label = "-".join([self.field.label,self.conductor_label,self.iso_label])


        self.friends = []
        self.friends += [('Isogeny class '+self.short_class_label, self.urls['class'])]
        self.friends += [('Twists',url_for('ecnf.index',field_label=self.field_label,jinv=self.jinv))]
        if self.field.is_real_quadratic():
            self.friends += [('Hilbert Modular Form '+self.hmf_label, self.urls['hmf'])]
        if self.field.is_imag_quadratic():
            self.friends += [('Bianchi Modular Form %s not yet available' % self.bmf_label, '')]

        self.properties = [
            ('Base field', self.field.field_pretty()),
            ('Label' , self.label)]

        # Plot
        if E.base_field().signature()[0]:
            self.plot = encode_plot(EC_nf_plot(E,self.field.generator_name()))
            self.plot_link = '<img src="%s" width="200" height="150"/>' % self.plot
            self.properties += [(None, self.plot_link)]

        self.properties += [
            ('Conductor' , self.cond),
            ('Conductor norm' , self.cond_norm),
            ('j-invariant' , self.j),
            ('CM' , self.cm_bool)]

        if self.base_change:
            self.properties += [('base-change', 'yes: %s' % ','.join([str(lab) for lab in self.base_change]))]
        else:
            self.base_change = [] # in case it was False instead of []
            self.properties += [('Q-curve' , self.qc)]

        self.properties += [
            ('Torsion order' , self.ntors),
            ('Rank' , self.rk),
            ]

        for E0 in self.base_change:
            self.friends += [('Base-change of %s /\(\Q\)' % E0 , url_for("ec.by_ec_label", label=E0))]

