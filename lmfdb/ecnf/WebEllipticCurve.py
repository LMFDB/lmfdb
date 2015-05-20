from flask import url_for
from sage.all import ZZ, var, PolynomialRing, QQ, GCD
from lmfdb.base import app, getDBConnection
from lmfdb.utils import image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from lmfdb.number_fields.number_field import parse_field_string, field_pretty
from lmfdb.WebNumberField import WebNumberField

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
            self.fact_cond = web_latex(N.factor())
        self.fact_cond_norm = web_latex(N.norm().factor())
        D = E.discriminant()
        self.disc = web_latex(D)
        try:
            self.fact_disc = web_latex(D.factor())
        except ValueError: # if not all prime ideal factors principal
            pass
            #self.fact_disc = web_latex(self.field.K.ideal(D).factor())
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

        self.fact_j = self.j
        if j:
            try:
                self.fact_j = web_latex(j.factor())
            except ValueError: # if not all prime ideal factors principal
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
            self.rk = "not known"
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
                               'reduction_type': self.local_info.bad_reduction_type()
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
        if self.field.is_real_quadratic():
            self.friends += [('Hilbert Modular Form '+self.hmf_label, self.urls['hmf'])]
        if self.field.is_imag_quadratic():
            self.friends += [('Bianchi Modular Form %s not yet available' % self.bmf_label, '')]

        self.properties = [
            ('Base field', self.field.field_pretty()),
            ('Label' , self.label),
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

