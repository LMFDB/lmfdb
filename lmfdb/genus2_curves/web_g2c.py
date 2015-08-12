# -*- coding: utf-8 -*-
import re
import tempfile
import os
from pymongo import ASCENDING, DESCENDING
from flask import url_for, make_response
import lmfdb.base
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.data import group_dict
#import sage.all
from sage.all import latex, matrix, ZZ, QQ, PolynomialRing, factor, implicit_plot
from lmfdb.hilbert_modular_forms.hilbert_modular_form import teXify_pol
from lmfdb.WebNumberField import *
from itertools import izip

logger = make_logger("g2c")

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves
    return g2cdb

def list_to_min_eqn(L):
    xpoly_rng = PolynomialRing(QQ,'x')
    ypoly_rng = PolynomialRing(xpoly_rng,'y')
    poly_tup = [xpoly_rng(tup) for tup in L]
    lhs = ypoly_rng([0,poly_tup[1],1])
    return str(lhs).replace("*","") + " = " + str(poly_tup[0]).replace("*","")

def inflate_interval(a,b,x=1.5):
    c = (a+b)/2
    d = (b-a)/2
    d *= x
    return (c-d,c+d)

def eqn_list_to_curve_plot(L):
    xpoly_rng = PolynomialRing(QQ,'x')
    poly_tup = [xpoly_rng(tup) for tup in L]
    f = poly_tup[0]
    h = poly_tup[1]
    g = f+h**2/4
    if len(g.real_roots())==0 and g(0)<0:
        return text("$X(\mathbb{R})=\emptyset$",(1,1),fontsize=50)
    X0 = [real(z[0]) for z in g.base_extend(CC).roots()]+[real(z[0]) for z in g.derivative().base_extend(CC).roots()]
    a,b = inflate_interval(min(X0),max(X0),1.5)
    groots = [a]+g.real_roots()+[b]
    if b-a<1e-7:
        a=-3
        b=3
        groots=[a,b]
    ngints = len(groots)-1
    plotzones = []
    npts = 100
    for j in range(ngints):
        c = groots[j]
        d = groots[j+1]
        if g((c+d)/2)<0:
            continue
        (c,d) = inflate_interval(c,d,1.1)
        s = (d-c)/npts
        u = c
        yvals = []
        for i in range(npts+1):
            v = g(u)
            if v>0:
                v = sqrt(v)
                w = -h(u)/2
                yvals.append(w+v)
                yvals.append(w-v)
            u += s
        (m,M) = inflate_interval(min(yvals),max(yvals),1.2)
        plotzones.append((c,d,m,M))
    x = var('x')
    y = var('y')
    return sum(implicit_plot(y**2+y*h(x)-f(x),(x,R[0],R[1]),(y,R[2],R[3]),aspect_ratio='automatic',plot_points=500) for R in plotzones)

# need to come up with a function that deal with the quadratic fields in the dictionary
def end_alg_name(name):
    name_dict = {
        "Z":"\\Z",
        "Q":"\\Q",      
        "Q x Qsqrt-4":"\\Q \\times \\Q(\\sqrt{-1})",
        "Q x Qsqrt-7":"\\Q \\times \\Q(\\sqrt{-7})",
        "Q x Qsqrt-11":"\\Q \\times \\Q(\\sqrt{-11})",
        "Q x Qsqrt-3":"\\Q \\times \\Q(\\sqrt{-3})",
        "Q x Qsqrt-19":"\\Q \\times \\Q(\\sqrt{-19})",
        "Q x Qsqrt-8":"\\Q \\times \\Q(\\sqrt{-2})",
        "Q x Qsqrt-67":"\\Q \\times \\Q(\\sqrt{-67})",
        "R":"\\R",
        "C":"\\C",
        "Q x Q":"\\Q \\times \\Q",
        "R x R":"\\R \\times \\R",
        "C x R":"\\C \\times \\R",
        "C x C":"\\C \\times \\C",
        "M_2(Q)":"\\mathrm{M}_2(\\Q)",
        "M_2(R)":"\\mathrm{M}_2(\\R)",
        "M_2(C)":"\\mathrm{M}_2(\\C)"
    }
    if name in name_dict.keys():
        return name_dict[name]
    else:
        return name

def st0_group_name(name):
    st0_dict = {
        'M_2(C)':'\\mathrm{U}(1)',
        'M_2(R)':'\\mathrm{SU}(2)',
        'C x C':'\\mathrm{U}(1)\\times\\mathrm{U}(1)',
        'C x R':'\\mathrm{U}(1)\\times\\mathrm{SU}(2)',
        'R x R':'\\mathrm{SU}(2)\\times\\mathrm{SU}(2)',
        'R':'\\mathrm{USp}(4)'
        }
    if name in st0_dict.keys():
        return st0_dict[name]
    else:
        return name

def st_group_name(name):
    if name == 'USp(4)':
        return '\\mathrm{USp}(4)'
    else:
        return name

def groupid_to_meaningful(groupid):
    if groupid[0] < 120:
        return group_dict[str(groupid).replace(" ","")]
    else:
        return groupid

def isog_label(label):
    #get isog label from full label
    L = label.split(".")
    return L[0]+ "." + L[1]

def igusa_clebsch_to_igusa(I):
    # Conversion from Igusa-Clebsch to Igusa
    J2 = I[0]//8
    J4 = (4*J2**2 - I[1])//96
    J6 = (8*J2**3 - 160*J2*J4 - I[2])//576
    J8 = (J2*J6 - J4**2)//4
    J10 = I[3]//4096
    return [J2,J4,J6,J8,J10]

def igusa_to_g2(J):
    # Conversion from Igusa to G2
    if J[0] != 0:
        return [J[0]**5/J[4], J[0]**3*J[1]/J[4], J[0]**2*J[2]/J[4]]
    elif J[1] != 0:
        return [0, J[1]**5/J[4]**2, J[1]*J[2]/J[4]]
    else:
        return [0,0,J[2]**5/J[4]**3]

def scalar_div(c,P,W):
    # Scalar division in a weighted projective space
    return [p//(c**w) for (p,w) in izip(P,W)]

def normalize_invariants(I,W):
    # Normalizes integral invariants to remove factors
    # Tuple of weights:
    W_b = W
    I_b = I
    l_b = len(W_b)
    # Eliminating elements of the weight with zero entries in W_b
    for n in range(l_b):
        if I_b[n] == 0:
            W_b[n] = 0
    # Smaller invariant tuples obtained by excluding zeroes
    W_s = [W_b[n] for n in range(l_b) if I_b[n] != 0]
    I_s = [I_b[n] for n in range(l_b) if I_b[n] != 0]
    # Finding the normalized weights, both big and small
    dW = gcd(W_s)
    W_bn = [w//dW for w in W_b]
    W_sn = [w//dW for w in W_s]
    # Normalization of the invariants by the appropriate weight
    dI = gcd(I_s)
    if dI == 1:
        return I
    ps = dI.prime_divisors()
    Z = zip(I_s, W_sn)
    c = prod([p**floor(min([ floor(valuation(i,p)/w) for (i,w) in Z ])) for p in ps], 1)
    # Final weighted multiplication
    I_n = scalar_div(c, I,W_bn)
    I_n = [ZZ(i) for i in I_n]
    return I_n
# We may want to preserve some factors in the gcd here to factor the invariants when these get bigger, though currently this is not needed

def zfactor(n):
    return factor(n) if n != 0 else 0


def get_end_data(isogeny_class):
    data = {}
    end_alg_title_dict = {'end_ring': r'\End(J)', 
                          'rat_end_alg': r'\End(J) \otimes \Q',
                          'real_end_alg': r'\End(J) \otimes \R',
                          'geom_end_ring': r'\End(J_{\overline{\Q}})', 
                          'rat_geom_end_alg': r'\End(J_{\overline{\Q}}) \otimes \Q',
                          'real_geom_end_alg':'\End(J_{\overline{\Q}}) \otimes \R'}
    for endalgtype in ['end_ring', 'rat_end_alg', 'real_end_alg', 'geom_end_ring', 'rat_geom_end_alg', 'real_geom_end_alg']:
        if endalgtype in isogeny_class:
            data[endalgtype + '_name'] = [end_alg_title_dict[endalgtype],end_alg_name(isogeny_class[endalgtype])]
        else:
            data[endalgtype + '_name'] = [end_alg_title_dict[endalgtype],'']
        
    data['geom_end_field'] = isogeny_class['geom_end_field']
    if data['geom_end_field'] <> '':
        data['geom_end_field_name'] = field_pretty(data['geom_end_field'])
    else:
        data['geom_end_field_name'] = ''        

    data['st0_group_name'] = st0_group_name(isogeny_class['real_geom_end_alg'])
    data['st_group_name'] = st_group_name(isogeny_class['st_group'])
    data['isogeny_class'] = isogeny_class
    if isogeny_class['is_gl2_type']:
        data['is_gl2_type_name'] = 'yes' # shows in side
        data['is_gl2_type_display'] = '&#x2713;' # checkmark, shows in search results
        gl2_statement = 'of \(\GL_2\)-type'
    else:
        data['is_gl2_type_name'] = 'no'  # shows in side
        data['is_gl2_display'] = ''      # shows in search results
        gl2_statement = 'not of \(\GL_2\)-type'

    if 'is_simple' in isogeny_class and 'is_geom_simple' in isogeny_class:
        if isogeny_class['is_geom_simple']:
            simple_statement = "simple over \(\overline{\Q}\), "
        elif isogeny_class['is_simple']:
            simple_statement = "simple over \(\Q\) but not simple over \(\overline{\Q}\), "
        else:
            simple_statement = "not simple over \(\Q\), "
    else:
        simple_statement = ""  # leave empty since not computed.
    data['endomorphism_statement'] = simple_statement + gl2_statement
    return data

class WebG2C(object):
    """
    Class for a genus 2 curve over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        #logger.debug("Constructing an instance of G2Cisog_class")
        self.__dict__.update(dbdata)
        self.make_curve()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific elliptic curve in the curves
        collection by its label, which can be either in LMFDB or
        Cremona format.
        label is string separated by "."
        """
        try:
            print label
            data = db_g2c().curves.find_one({"label" : label})
            
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error

        if data:
            return WebG2C(data)
        return "Curve not found" # caller must catch this and raise an error

    def make_curve(self):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these, construct the
        # and compute some further (easy) data about it.
        #

        # Weierstrass equation

        data = self.data = {}

        disc = ZZ(self.disc_sign) * ZZ(self.disc_key[3:]) 
        # to deal with disc_key, uncomment line above and remove line below
        #disc = ZZ(self.disc_sign) * ZZ(self.abs_disc)
        data['disc'] = disc
        data['cond'] = ZZ(self.cond)
        data['min_eqn'] = self.min_eqn
        data['min_eqn_display'] = list_to_min_eqn(self.min_eqn)
        data['disc_factor_latex'] = web_latex(factor(data['disc']))
        data['cond_factor_latex'] = web_latex(factor(int(self.cond)))
        data['aut_grp'] = groupid_to_meaningful(self.aut_grp)
        data['geom_aut_grp'] = groupid_to_meaningful(self.geom_aut_grp)
        data['igusa_clebsch'] = [ZZ(a) for a in self.igusa_clebsch]
        data['igusa'] = igusa_clebsch_to_igusa(data['igusa_clebsch'])
        data['g2'] = igusa_to_g2(data['igusa'])
        data['ic_norm'] = normalize_invariants(data['igusa_clebsch'],[1,2,3,5])
        data['igusa_norm'] = normalize_invariants(data['igusa'],[1,2,3,4,5])
        data['ic_norm_factor_latex'] = [web_latex(zfactor(i)) for i in data['ic_norm']]
        data['igusa_norm_factor_latex'] = [web_latex(zfactor(j)) for j in data['igusa_norm']]
        data['num_rat_wpts'] = ZZ(self.num_rat_wpts)
        data['two_selmer_rank'] = ZZ(self.two_selmer_rank)
        if len(self.torsion) == 0:
            data['tor_struct'] = '\mathrm{trivial}'
        else:
            tor_struct = [ZZ(a)  for a in self.torsion]
            data['tor_struct'] = ' \\times '.join(['\Z/{%s}\Z' % n for n in tor_struct])
        isogeny_class = db_g2c().isogeny_classes.find_one({'label' : isog_label(self.label)})
        end_data = get_end_data(isogeny_class)
        for key in end_data.keys():
            data[key] = end_data[key]
        x = self.label.split('.')[1]

        self.make_code_snippets()

        self.friends = [
            ('Isogeny class %s' % isog_label(self.label), url_for(".by_double_iso_label", conductor = self.cond, iso_label = x)),
            ('L-function', url_for("l_functions.l_function_genus2_page", cond=self.cond,x=x)),
            
            ('Twists',url_for(".index_Q", ic0 = self.igusa_clebsch[0], ic1 = self.igusa_clebsch[1],ic2 = self.igusa_clebsch[2],ic3 = self.igusa_clebsch[3])),
            #('Twists2',url_for(".index_Q", igusa_clebsch = str(self.igusa_clebsch)))  #doesn't work.
            #('Siegel modular form someday', '.')
            ]
        self.downloads = [
             ('Download all stored data', '.')]
        iso = self.label.split('.')[1]
        num = '.'.join(self.label.split('.')[2:4])
        self.plot = encode_plot(eqn_list_to_curve_plot(self.min_eqn))
        self.plot_link = '<img src="%s" width="200" height="150"/>' % self.plot
        self.properties = [('Label', self.label),
                           (None, self.plot_link),
                           ('Conductor','%s' % self.cond),
                           ('Discriminant', '%s' % data['disc']),
                           ('Invariants', '%s </br> %s </br> %s </br> %s'% tuple(data['ic_norm'])), 
                           ('Sato-Tate group', '\(%s\)' % data['st_group_name']), 
                           ('\(%s\)' % data['real_geom_end_alg_name'][0],'\(%s\)' % data['real_geom_end_alg_name'][1]),
                           ('\(\mathrm{GL}_2\)-type','%s' % data['is_gl2_type_name'])]
        self.title = "Genus 2 Curve %s" % (self.label)
        self.bread = [
             ('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('%s' % self.cond, url_for(".by_conductor", conductor=self.cond)),
             ('%s' % iso, url_for(".by_double_iso_label", conductor=self.cond, iso_label=iso)),
             ('Genus 2 curve %s' % num, url_for(".by_g2c_label", label=self.label))]

    def make_code_snippets(self):
        sagecode = dict()
        gpcode = dict()
        magmacode = dict()

        #utility function to save typing!

        def set_code(key, s, g, m):
            sagecode[key] = s
            gpcode[key] = g
            magmacode[key] = m
        sage_not_implemented = '# (not yet implemented)'
        pari_not_implemented = '\\\\ (not yet implemented)'
        magma_not_implemented = '// (not yet implemented)'

        # prompt
        set_code('prompt',
                 'sage:',
                 'gp:',
                 'magma:')

        # logo
        set_code('logo',
                 '<img src ="http://www.sagemath.org/pix/sage_logo_new.png" width = "50px">',
                 '<img src = "http://pari.math.u-bordeaux.fr/logo/Logo%20Couleurs/Logo_PARI-GP_Couleurs_L150px.png" width="50px">',
                 '<img src = "http://i.stack.imgur.com/0468s.png" width="50px">')
        # overwrite the above until we get something which looks reasonable
        set_code('logo', '', '', '')

        # curve
        set_code('curve',
                 'R.<x> = PolynomialRing(QQ); C = HyperellipticCurve(R(%s), R(%s))'   % (self.data['min_eqn'][0],self.data['min_eqn'][1]),
                 pari_not_implemented, # pari code goes here
                 'R<x> := PolynomialRing(Rationals()); C := HyperellipticCurve(R!%s, R!%s);'   % (self.data['min_eqn'][0],self.data['min_eqn'][1]) 
                 )
        if self.data['disc'] % 4096 == 0:
            ind2 = [a[0] for a in self.data['isogeny_class']['bad_lfactors']].index(2)
            bad2 = self.data['isogeny_class']['bad_lfactors'][ind2][1]
            magma_cond_option = ': ExcFactors:=[*<2,Valuation('+str(self.data['cond'])+',2),R!'+str(bad2)+'>*]'
        else:
            magma_cond_option = ''
        set_code('cond',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'Conductor(LSeries(C%s)); Factorization($1);' % magma_cond_option
                 )
        set_code('disc',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'Discriminant(C); Factorization(Integers()!$1);'
                 )
        set_code('igusa_clebsch',
                 'C.igusa_clebsch_invariants(); [factor(a) for a in _]',
                 pari_not_implemented, # pari code goes here
                 'IgusaClebschInvariants(C); [Factorization(Integers()!a): a in $1];'
                 )
        set_code('igusa',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'IgusaInvariants(C); [Factorization(Integers()!a): a in $1];'
                 )
        set_code('g2',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'G2Invariants(C);'
                 )
        set_code('aut',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'AutomorphismGroup(C); IdentifyGroup($1);'
                 )
        set_code('autQbar',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'AutomorphismGroup(ChangeRing(C,AlgebraicClosure(Rationals()))); IdentifyGroup($1);'
                 )
        set_code('num_rat_wpts',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 '#Roots(HyperellipticPolynomials(SimplifiedModel(C)));'
                 )
        set_code('two_selmer',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'TwoSelmerGroup(Jacobian(C)); NumberOfGenerators($1);'
                 )
        set_code('tor_struct',
                 sage_not_implemented, # sage code goes here
                 pari_not_implemented, # pari code goes here
                 'TorsionSubgroup(Jacobian(SimplifiedModel(C))); AbelianInvariants($1);'
                 )


        self.code = {'sage': sagecode, 'pari': gpcode, 'magma': magmacode}
