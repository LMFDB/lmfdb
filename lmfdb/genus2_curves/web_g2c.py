# -*- coding: utf-8 -*-
import re
import tempfile
import os
from pymongo import ASCENDING, DESCENDING
from lmfdb.base import getDBConnection
from lmfdb.utils import comma, make_logger, web_latex, encode_plot
from lmfdb.ecnf.main import split_full_label
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.data import group_dict
from sage.all import latex, matrix, ZZ, QQ, PolynomialRing, factor, implicit_plot
from lmfdb.hilbert_modular_forms.hilbert_modular_form import teXify_pol
from lmfdb.WebNumberField import *
from itertools import izip
from flask import url_for, make_response

logger = make_logger("g2c")

###############################################################################
# Database connection
###############################################################################

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = getDBConnection().genus2_curves
    return g2cdb

g2endodb = None

def db_g2endo():
    global g2endodb
    if g2endodb is None:
        g2endodb = getDBConnection().genus2_endomorphisms
    return g2endodb

ecdbQQ = None

def db_ecQQ():
    global ecdbQQ
    if ecdbQQ is None:
        ecdbQQ = getDBConnection().elliptic_curves.curves
    return ecdbQQ

###############################################################################
# Recovering the isogeny class
###############################################################################

def isog_label(label):
    L = label.split(".")
    return L[0]+ "." + L[1]

###############################################################################
# Conversion of eliptic curve labels (database stores Cremona labels but we
# want to display LMFDB labels -- see Issue #635)
###############################################################################

def cremona_to_lmfdb(label):
    E = db_ecQQ().find_one({'label':label})
    if E:
        return E['lmfdb_label']
    else:
        return ''

###############################################################################
# Pretty print functions
###############################################################################

def intlist_to_poly(s):
    return latex(PolynomialRing(QQ, 'x')(s))

def strlist_to_nfelt(L, varname):
    La = [ s.encode('ascii') for s in L ]
    return latex(PolynomialRing(QQ, varname)(La))

def list_to_min_eqn(L):
    xpoly_rng = PolynomialRing(QQ,'x')
    ypoly_rng = PolynomialRing(xpoly_rng,'y')
    poly_tup = [xpoly_rng(tup) for tup in L]
    lhs = ypoly_rng([0,poly_tup[1],1])
    return str(lhs).replace("*","") + " = " + str(poly_tup[0]).replace("*","")

def groupid_to_meaningful(groupid):
    if groupid[0] < 120:
        return group_dict[str(groupid).replace(" ","")]
    else:
        return groupid

def url_for_ec(label):
    if not '-' in label:
        return url_for('ec.by_ec_label', label = label)
    else:
        (nf, conductor_label, class_label, number) = split_full_label(label)
        return url_for('ecnf.show_ecnf', nf = nf, conductor_label =
                conductor_label, class_label = class_label, number = number)

def factorsRR_raw_to_pretty(factorsRR):
    if factorsRR == ['RR']:
        return r'\R'
    elif factorsRR == ['CC']:
        return r'\C'
    elif factorsRR == ['RR', 'RR']:
        return r'\R \times \R'
    elif factorsRR == ['RR', 'CC']:
        return r'\R \times \C'
    elif factorsRR == ['CC', 'RR']:
        return r'\R \times \C',
    elif factorsRR == ['CC', 'CC']:
        return r'\C \times \C'
    elif factorsRR == ['HH']:
        return r'\mathbf{H}'
    elif factorsRR == ['M_2(RR)']:
        return r'\mathrm{M}_2 (\R)'
    elif factorsRR == ['M_2(CC)']:
        return r'\mathrm{M}_2 (\C)'

def zfactor(n):
    return factor(n) if n != 0 else 0

###############################################################################
# Plot functions
###############################################################################

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
    X0 = [real(z[0]) for z in g.base_extend(CC).roots()]+[real(z[0]) for z in
            g.derivative().base_extend(CC).roots()]
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
    return sum(implicit_plot(y**2 + y*h(x) - f(x), (x,R[0],R[1]),
        (y,R[2],R[3]), aspect_ratio='automatic', plot_points=500) for R in
        plotzones)

###############################################################################
# Invariant conversion (now redundant)
###############################################################################

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
    c = prod([p**floor(min([ floor(valuation(i,p)/w) for (i,w) in Z ])) for p
        in ps], 1)
    # Final weighted multiplication
    I_n = scalar_div(c, I,W_bn)
    I_n = [ZZ(i) for i in I_n]
    # Endnote: We may want to preserve some factors in the gcd here to factor
    # the invariants when these get bigger, though currently this is not needed
    return I_n

###############################################################################
# Name conversions for the Sato-Tate and old endomorphism functionality
###############################################################################

def end_alg_name(name):
    name_dict = {
        "R":"\\R",
        "C":"\\C",
        "R x R":"\\R \\times \\R",
        "C x R":"\\C \\times \\R",
        "C x C":"\\C \\times \\C",
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

###############################################################################
# Data obtained from Sato-Tate invariants
###############################################################################

def get_st_data(isogeny_class):
    # TODO: Some inheritance could help?
    data = {}
    data['isogeny_class'] = isogeny_class
    data['st_group_name'] = st_group_name(isogeny_class['st_group'])
    data['st0_group_name'] = st0_group_name(isogeny_class['real_geom_end_alg'])
    # Later used in Lady Gaga box:
    data['real_geom_end_alg_disp'] = [r'\End(J_{\overline{\Q}}) \otimes \R',
                end_alg_name(isogeny_class['real_geom_end_alg'])]
    # Adding data that show in sidebar respectively search results:
    if isogeny_class['is_gl2_type']:
        data['is_gl2_type_name'] = 'yes'
        data['is_gl2_type_display'] = '&#x2713;'
    else:
        data['is_gl2_type_name'] = 'no'
        data['is_gl2_display'] = ''
    return data

###############################################################################
# Statement functions for endomorphism functionality
###############################################################################

def gl2_statement(factorsRR, base):
    if factorsRR in [['RR', 'RR'], ['CC']]:
        return "The Jacobian is of \(\GL_2\)-type over " + base
    return "The Jacobian is not of \(\GL_2\)-type over " + base

def endo_statement(factorsQQ, factorsRR, ring, fieldstring):
    statement = """<table>"""
    # First row: description of endomorphism algebra factors
    statement += """<tr><td>\(\End (J_{%s}) \otimes \Q\
    \)</td><td>\(\simeq\)</td><td>""" % fieldstring
    factorsQQ_number = len(factorsQQ)
    factorsQQ_pretty = [ field_pretty(fac[0]) for fac in factorsQQ if
            fac[0] ]
    # In the case of only one factor we either get a number field or a
    # quaternion algebra:
    if factorsQQ_number == 1:
        # First we deal with the number field case:
        if factorsQQ[0][2] == -1:
            # Prettify if labels available, otherwise return defining polynomial:
            if factorsQQ_pretty:
                statement += """<a href=%s>%s</a>""" % \
                (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                factorsQQ_pretty[0])
            else:
                statement += """number field with defining polynomial \
                \(%s\)""" % intlist_to_poly(factorsQQ[0][1])
            if len(factorsQQ[0][1]) == 5:
                statement += """(CM)"""
        # Up next is the case of a matrix ring, with labels and full
        # prettification always available:
        elif factorsQQ[0][2] == 1:
            statement += """\(\mathrm{M}_2(\)<a href=%s>%s</a>\()\)""" % \
            (url_for("number_fields.by_label", label=factorsQQ[0][0]),
            factorsQQ_pretty[0])
        # And finally we deal with quaternion algebras over the rationals:
        else:
            statement += """quaternion algebra over <a href=%s>%s</a> of \
            discriminant %s""" % \
            (url_for("number_fields.by_label", label=factorsQQ[0][0]),
            factorsQQ_pretty[0], factorsQQ[0][2])
    # If there are two factors, then we get two at most quadratic fields:
    else:
        statement += """<a href=%s>%s</a> \(\\times\) <a href=%s>%s</a>""" % \
        (url_for("number_fields.by_label", label=factorsQQ[0][0]),
        factorsQQ_pretty[0],
        url_for("number_fields.by_label", label=factorsQQ[1][0]),
        factorsQQ_pretty[1])
    # End of first row:
    statement += """</td></tr>"""
    # Second row: description of algebra tensored with RR
    statement += """<tr><td>\(\End (J_{%s}) \otimes\
    \R\)</td><td>\(\simeq\)</td> <td>\(%s\)</td></tr>""" % \
    (fieldstring, factorsRR_raw_to_pretty(factorsRR))
    # Third row: description of the endomorphism ring as an order in the
    # endomorphism algebra
    statement += """<tr><td>\(\End (J_{%s})\)</td><td>\(\simeq\)</td><td>""" \
            % fieldstring
    # First the case of a maximal order:
    if ring[0] == 1:
        if factorsQQ[0][0] == '1.1.1.1':
            statement += """\(\Z\)"""
        else:
            statement += """a maximal order in \(\End (J_{%s}) \otimes \Q\)"""\
            % fieldstring
    # Then the case where there is still a single factor:
    elif factorsQQ_number == 1:
        # Number field case:
        if factorsQQ[0][2] == -1:
            statement += """an order of conductor of norm \(%s\) in \(\End\
            (J_{%s}) \otimes \Q\)""" % (ring[0], fieldstring)
        # Otherwise mention whether the order is Eichler:
        elif ring[1] == 1:
            statement += """an Eichler order of index \(%s\) in \(\End\
            (J_{%s}) \otimes \Q\)""" % (ring[0], fieldstring)
        else:
            statement += """a non-Eichler order of index \(%s\) in \(\End\
            (J_{%s}) \otimes \Q\)""" % (ring[0], fieldstring)
    # Finally the most generic case:
    else:
        statement += "an order of index \(%s\) in \(\End (J_{%s}) \otimes \
        \Q\)""" % (ring[0], fieldstring)
    # End of third row, and with it, of the statement:
    statement += """</td></tr>"""
    statement += """</table>"""
    return statement

def fod_statement(fod_label, fod_poly):
    if fod_label == '1.1.1.1':
        return """All endomorphisms of the Jacobian are defined over \(\Q\)"""
    elif fod_label != '':
        fod_pretty = field_pretty(fod_label)
        fod_url = url_for("number_fields.by_label", label=fod_label)
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(L = \Q (a)\) with defining polynomial \(%s\) (<a\
        href=%s">%s)</a>""" % (fod_poly, fod_url, fod_pretty)
    else:
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(L = \Q (a)\) with defining polynomial \(%s\)"""\
        % fod_poly

def st_group_statement(group, fieldstring):
    return """Sato-Tate group over \(%s\): \(%s\)""" % (fieldstring, group)

def lattice_statement_preamble():
    return """Remainder of the endomorphism lattice by subfield"""

def lattice_statement(lattice):
    statement = ''
    for ED in lattice:
        statement += """<p>"""
        statement += """Over subfield \(K\) with generator \(%s\) with \
        minimal polynomial \(%s\)""" % \
        (strlist_to_nfelt(ED[0][2], 'a'), intlist_to_poly(ED[0][1]))
        # Add link and prettify if available:
        if ED[0][0]:
            statement += """ (<a href=%s>%s</a>)""" % \
            (url_for("number_fields.by_label", label=ED[0][0]),
            field_pretty(ED[0][0]))
        statement += """:<br>"""
        statement += endo_statement(ED[1], ED[2], ED[3], r'K')
        #statement += """<br>"""
        statement += st_group_statement(ED[4], r'K')
        statement += """</p>"""
    return statement

def spl_fod_statement(is_simple_geom, spl_fod_label, spl_fod_poly):
    if is_simple_geom:
        return """The Jacobian is simple over \(\overline{\Q}\)"""
    elif spl_fod_label == '1.1.1.1':
        return """The Jacobian splits over \(\Q\)"""
    elif spl_fod_label != '':
        spl_fod_pretty =  field_pretty(spl_fod_label)
        spl_fod_url = url_for("number_fields.by_label", label=spl_fod_label)
        return """Field of minimal degree over which the Jacobian splits:<br>\
        number field \(M = \Q (b)\) with defining polynomial \(%s\) \
        (<a href=%s>%s)</a>""" % (spl_fod_poly, spl_fod_url, spl_fod_pretty)
    else:
        return """Field of minimal degree over which the Jacobian splits:<br>\
        number field \(M = \Q (b)\) with defining polynomial %s""" % \
        spl_fod_poly

def spl_statement(coeffss, labels, condnorms):
    if len(coeffss) == 1:
        statement = """The Jacobian decomposes up to isogeny as the square of
        an elliptic curve</p>\
        <p>Elliptic curve that admits a small isogeny:"""
    else:
        statement = """The Jacobian admits two distinct elliptic curve factors
        up to isogeny</p>\
        <p>Elliptic curves that represent these factors and admit small
        isogenies are:"""
    for n in range(len(coeffss)):
        # Use labels when possible:
        label = labels[n]
        if label:
            # TODO: Next statement can be removed by a database update
            if not '-' in label:
               lmfdb_label = cremona_to_lmfdb(label)
            statement += """<br>Elliptic curve with label <a href=%s>%s</a>"""\
            % (url_for_ec(lmfdb_label), lmfdb_label)
        # Otherwise give defining equation:
        else:
            statement += """<br>\(4 y^2 = x^3 - (g_4 / 48) x - (g_6 / 864)\),
            with<br>\
            \(g_4 = %s\)<br>\
            \(g_6 = %s\)<br>\
            Conductor norm: %s""" % \
            (strlist_to_nfelt(coeffss[n][0], 'b'),
            strlist_to_nfelt(coeffss[n][1], 'b'),
            condnorms[n])
    return statement

###############################################################################
# The actual class definition
###############################################################################

class WebG2C(object):
    """
    Class for a genus 2 curve over Q
    """
    def __init__(self, dbdata, endodbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        #logger.debug("Constructing an instance of G2Cisog_class")
        self.__dict__.update(dbdata)
        self.__dict__.update(endodbdata)
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
            endodata = db_g2endo().bycurve.find_one({"label" : label})
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error
        if data:
            if endodata:
                return WebG2C(data, endodata)
            else:
                return "Endomorphism data for curve not found"
        return "Data for curve not found" # caller must catch this and raise an error

    ###########################################################################
    # Main data creation for individual curves
    ###########################################################################

    def make_curve(self):
        # To start with the data fields of self are just those from the
        # databases.  We reformat these, while computing some further (easy)
        # data about the curve on the fly.

        # Initialize data:
        data = self.data = {}
        endodata = self.endodata = {}

        # Polish data from database before putting it into the data dictionary:
        disc = ZZ(self.disc_sign) * ZZ(self.disc_key[3:])
        # to deal with disc_key, uncomment line above and comment line below
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
        data['igusa'] = [ZZ(a) for a in self.igusa]
        data['g2'] = self.g2inv
        data['ic_norm'] = normalize_invariants(data['igusa_clebsch'],[1,2,3,5])
        data['igusa_norm'] = normalize_invariants(data['igusa'],[1,2,3,4,5])
        data['ic_norm_factor_latex'] = [web_latex(zfactor(i)) for i in
                data['ic_norm']]
        data['igusa_norm_factor_latex'] = [web_latex(zfactor(j)) for j in
                data['igusa_norm']]
        data['num_rat_wpts'] = ZZ(self.num_rat_wpts)
        data['two_selmer_rank'] = ZZ(self.two_selmer_rank)
        if len(self.torsion) == 0:
            data['tor_struct'] = '\mathrm{trivial}'
        else:
            tor_struct = [ZZ(a)  for a in self.torsion]
            data['tor_struct'] = ' \\times '.join(['\Z/{%s}\Z' % n for n in
                tor_struct])

        # Data derived from Sato-Tate group:
        isogeny_class = db_g2c().isogeny_classes.find_one({'label' :
            isog_label(self.label)})
        st_data = get_st_data(isogeny_class)
        for key in st_data.keys():
            data[key] = st_data[key]

        # GL_2 statement over the base field
        endodata['gl2_statement_base'] = gl2_statement(self.factorsRR_base,
                r'\(\Q\)')

        # NOTE: In what follows there is some copying of code and data that is
        # stupid from the point of view of efficiency but likely better from
        # that of maintenance.

        # Endomorphism data over QQ:
        endodata['factorsQQ_base'] = self.factorsQQ_base
        endodata['factorsRR_base'] = self.factorsRR_base
        endodata['ring_base'] = self.ring_base
        endodata['endo_statement_base'] = \
        """Endomorphism ring over \(\Q\):<br>""" + \
        endo_statement(endodata['factorsQQ_base'], endodata['factorsRR_base'],
                endodata['ring_base'], r'')
        # Field of definition data:
        endodata['fod_label'] = self.fod_label
        endodata['fod_poly'] = intlist_to_poly(self.fod_coeffs)
        endodata['fod_statement'] = fod_statement(endodata['fod_label'],
                endodata['fod_poly'])
        # Endomorphism data over QQbar:
        endodata['factorsQQ_geom'] = self.factorsQQ_geom
        endodata['factorsRR_geom'] = self.factorsRR_geom
        endodata['ring_geom'] = self.ring_geom
        if self.fod_label != '1.1.1.1':
            endodata['endo_statement_geom'] = \
            """Endomorphism ring over \(\overline{\Q}\):<br>""" + \
            endo_statement(endodata['factorsQQ_geom'],
                    endodata['factorsRR_geom'], endodata['ring_geom'],
                    r'\overline{\Q}')

        # Full endomorphism lattice:
        endodata['lattice'] = self.lattice[1:len(self.lattice) - 1]
        if endodata['lattice']:
            endodata['lattice_statement_preamble'] = \
            lattice_statement_preamble()
            endodata['lattice_statement'] = \
            lattice_statement(endodata['lattice'])

        # Splitting field description:
        #endodata['is_simple_base'] = self.is_simple_base
        endodata['is_simple_geom'] = self.is_simple_geom
        endodata['spl_fod_label'] = self.spl_fod_label
        endodata['spl_fod_poly'] = intlist_to_poly(self.spl_fod_coeffs)
        endodata['spl_fod_statement'] = \
        spl_fod_statement(endodata['is_simple_geom'],
                endodata['spl_fod_label'], endodata['spl_fod_poly'])

        # Isogeny factors:
        if not endodata['is_simple_geom']:
            endodata['spl_facs_coeffs'] = self.spl_facs_coeffs
            # This could be done non-uniformly as well... later.
            if len(self.spl_facs_labels) == len(self.spl_facs_coeffs):
                endodata['spl_facs_labels'] = self.spl_facs_labels
            else:
                endodata['spl_facs_labels'] = ['' for coeffs in
                        self.spl_facs_coeffs]
            endodata['spl_facs_condnorms'] = self.spl_facs_condnorms
            endodata['spl_statement'] = \
            spl_statement(endodata['spl_facs_coeffs'],
                    endodata['spl_facs_labels'],
                    endodata['spl_facs_condnorms'])

        # Title
        self.title = "Genus 2 Curve %s" % (self.label)

        # Lady Gaga box
        self.plot = encode_plot(eqn_list_to_curve_plot(self.min_eqn))
        self.plot_link = '<img src="%s" width="200" height="150"/>' % self.plot
        self.properties = [
                ('Label', self.label),
               (None, self.plot_link),
               ('Conductor','%s' % self.cond),
               ('Discriminant', '%s' % data['disc']),
               ('Invariants', '%s </br> %s </br> %s </br> %s' % tuple(data['ic_norm'])),
               ('Sato-Tate group', '\(%s\)' % data['st_group_name']),
               ('\(%s\)' % data['real_geom_end_alg_disp'][0],
                '\(%s\)' % data['real_geom_end_alg_disp'][1]),
               ('\(\mathrm{GL}_2\)-type','%s' % data['is_gl2_type_name'])]
        x = self.label.split('.')[1]
        self.friends = [
            ('Isogeny class %s' % isog_label(self.label),
                url_for(".by_double_iso_label",
                    conductor = self.cond,
                    iso_label = x)),
            ('L-function',
                url_for("l_functions.l_function_genus2_page",
                    cond=self.cond,x=x)),
            ('Twists',
                url_for(".index_Q",
                    g20 = self.g2inv[0],
                    g21 = self.g2inv[1],
                    g22 = self.g2inv[2]))
            #('Twists2',
            #   url_for(".index_Q",
            #       igusa_clebsch = str(self.igusa_clebsch)))  #doesn't work.
            #('Siegel modular form someday', '.')
            ]
        self.downloads = [('Download all stored data', '.')]

        # Breadcrumbs
        iso = self.label.split('.')[1]
        num = '.'.join(self.label.split('.')[2:4])
        self.bread = [
             ('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('%s' % self.cond, url_for(".by_conductor", conductor=self.cond)),
             ('%s' % iso, url_for(".by_double_iso_label", conductor=self.cond,
                 iso_label=iso)),
             ('Genus 2 curve %s' % num, url_for(".by_g2c_label",
                 label=self.label))
             ]

        # Make code that is used on the page:
        self.make_code_snippets()

    def make_code_snippets(self):
        sagecode = dict()
        gpcode = dict()
        magmacode = dict()

        # Utility function to save typing!
        def set_code(key, s, g, m):
            sagecode[key] = s
            gpcode[key] = g
            magmacode[key] = m
        sage_not_implemented = '# (not yet implemented)'
        pari_not_implemented = '\\\\ (not yet implemented)'
        magma_not_implemented = '// (not yet implemented)'

        # Prompt
        set_code('prompt',
                 'sage:',
                 'gp:',
                 'magma:')

        # Logo
        set_code('logo',
                 '<img src ="http://www.sagemath.org/pix/sage_logo_new.png" width = "50px">',
                 '<img src = "http://pari.math.u-bordeaux.fr/logo/Logo%20Couleurs/Logo_PARI-GP_Couleurs_L150px.png" width="50px">',
                 '<img src = "http://i.stack.imgur.com/0468s.png" width="50px">')
        # Overwrite the above until we get something which looks reasonable
        set_code('logo', '', '', '')

        # Curve
        set_code('curve',
                 'R.<x> = PolynomialRing(QQ); C = HyperellipticCurve(R(%s), R(%s))'
                 % (self.data['min_eqn'][0],self.data['min_eqn'][1]),
                 pari_not_implemented, # pari code goes here
                 'R<x> := PolynomialRing(Rationals()); C := HyperellipticCurve(R!%s, R!%s);'
                 % (self.data['min_eqn'][0],self.data['min_eqn'][1])
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
                 'Conductor(LSeries(C%s)); Factorization($1);'
                 % magma_cond_option
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
