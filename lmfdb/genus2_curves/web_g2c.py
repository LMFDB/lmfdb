# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from pymongo import ASCENDING, DESCENDING
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex, encode_plot
from lmfdb.ecnf.main import split_full_label
from lmfdb.genus2_curves.data import group_dict
from lmfdb.number_fields.number_field import field_pretty
from sage.all import latex, ZZ, QQ, CC, PolynomialRing, factor, implicit_plot, real, sqrt, var
from sage.plot.text import text
from itertools import izip
from flask import url_for

###############################################################################
# Database connection
###############################################################################

the_g2cdb = None

def g2cdb():
    global the_g2cdb
    if the_g2cdb is None:
        the_g2cdb = getDBConnection().genus2_curves
    return the_g2cdb

###############################################################################
# Recovering the isogeny class
###############################################################################

def isogeny_class_label(label):
    L = label.split(".")
    return L[0]+ "." + L[1]

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
    poly_tup = [ xpoly_rng(tup) for tup in L ]
    lhs = ypoly_rng([0, poly_tup[1], 1])
    return str(lhs).replace("*","") + " = " + str(poly_tup[0]).replace("*","")

def groupid_to_meaningful(groupid):
    if groupid[0] < 120:
        return group_dict[str(groupid).replace(" ", "")]
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

def ring_pretty(L, f):
    # Only usable for at most quadratic fields
    # TODO: Generalize, so that we can use it for cyclotomic maximal orders as
    # well. Note that this requires further modification of the code below.
    if len(L) == 2:
        return r'\Z'
    c,b,a = L
    D = b**2 - 4*a*c
    if f == 1:
        if D % 4 == 0:
            return r'\Z [\sqrt{' + str(D//4) + r'}]'
        return r'\Z [\frac{1 + \sqrt{' + str(D) + r'}}{2}]'
    if D % 4 == 0:
        return r'\Z [' + str(f) + r'\sqrt{' + str(D//4) + r'}]'
    if f % 2 == 0:
        return r'\Z [' + str(f//2) + r'\sqrt{' + str(D) + r'}]'
    return r'\Z [\frac{1 +' + str(f) + r'\sqrt{' + str(D) + r'}}{2}]'

def st_group_name(st_group):
    return '\\mathrm{USp}(4)' if st_group == 'USp(4)' else st_group

def url_for_st_group(st_group):
    return url_for('st.by_label', label='1.4.'+st_group)
    
def st_group_href(st_group):
    return '<a href="%s">$%s$</a>' % (url_for_st_group(st_group),st_group_name(st_group))

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
    return [ J2, J4, J6, J8, J10 ]

def igusa_to_g2(J):
    # Conversion from Igusa to G2
    if J[0] != 0:
        return [ J[0]**5/J[4], J[0]**3*J[1]/J[4], J[0]**2*J[2]/J[4] ]
    elif J[1] != 0:
        return [ 0, J[1]**5/J[4]**2, J[1]*J[2]/J[4] ]
    else:
        return [ 0, 0, J[2]**5/J[4]**3 ]

###############################################################################
# Invariant normalization
###############################################################################

def scalar_div(c,P,W):
    # Scalar division in a weighted projective space
    return [ p//(c**w) for (p,w) in izip(P,W) ]

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
    W_s = [ W_b[n] for n in range(l_b) if I_b[n] != 0 ]
    I_s = [ I_b[n] for n in range(l_b) if I_b[n] != 0 ]
    # Finding the normalized weights, both big and small
    dW = gcd(W_s)
    W_bn = [ w//dW for w in W_b ]
    W_sn = [ w//dW for w in W_s ]
    Z_bn = zip(I_b, W_bn)
    Z_sn = zip(I_s, W_sn)
    # Normalization of the invariants by the appropriate weight
    dI = gcd(I_s)
    if dI == 1:
        return I
    ps = dI.prime_divisors()
    c = prod([ p**floor(min([ floor(valuation(i,p)/w) for (i,w) in Z_sn ])) for
            p in ps ], 1)
    # Generalizable sign adjustment: Final odd weight (after normalization of
    # weights) should have a positive sign.
    # We start at the end because this is the most intuitive modification in
    # genus 2: the discriminant then always has positive sign after
    # normalization.
    for (i,w) in Z_bn[::-1]:
        if w % 2 == 1:
            s = i.sign()
            break
    # Final weighted multiplication
    I_n = scalar_div(s*c, I, W_bn)
    I_n = [ ZZ(i) for i in I_n ]
    # NOTE: We may want to preserve some factors in the gcd here to factor the
    # invariants when these get bigger, though currently this is not needed
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

def aut_group_name(name):
    return group_dict[name]

def boolean_name(value):
    return '\\mathrm{True}' if value else '\\mathrm{False}'
    
def globally_solvable_name(value):
    return boolean_name(value) if value in [0,1] else '\\mathrm{unknown}'


###############################################################################
# Data obtained from Sato-Tate invariants
###############################################################################

def get_st_data(isogeny_class):
    # TODO: Some inheritance could help?
    data = {}
    data['isogeny_class'] = isogeny_class
    data['st_group_name'] = st_group_name(isogeny_class['st_group'])
    data['st_group_href'] = st_group_href(isogeny_class['st_group'])
    data['st0_group_name'] = st0_group_name(isogeny_class['real_geom_end_alg'])
    # Later used in Lady Gaga box:
    data['real_geom_end_alg_disp'] = [ r'\End(J_{\overline{\Q}}) \otimes \R',
        end_alg_name(isogeny_class['real_geom_end_alg']) ]
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

def gl2_statement_base(factorsRR, base):
    if factorsRR in [ ['RR', 'RR'], ['CC'] ]:
        return "of \(\GL_2\)-type over " + base
    return "not of \(\GL_2\)-type over " + base

def gl2_simple_statement(factorsQQ, factorsRR):
    if factorsRR in [ ['RR', 'RR'], ['CC'] ]:
        gl2 = "of \(\GL_2\)-type"
    else:
        gl2 = "not of \(\GL_2\)-type"
    if len(factorsQQ) == 1 and factorsQQ[0][2] != 1:
        simple = "simple"
    else:
        simple = "not simple"
    return gl2 + ", " + simple

def endo_statement(factorsQQ, factorsRR, ring, fieldstring):
    statement = """<table class="g2">"""
    factorsQQ_number = len(factorsQQ)
    factorsQQ_pretty = [ field_pretty(fac[0]) for fac in factorsQQ if
        fac[0] ]

    # First row: description of the endomorphism ring as an order in the
    # endomorphism algebra
    statement += """<tr><td>\(\End (J_{%s})\)</td><td>\(\simeq\)</td><td>"""\
        % fieldstring
    # First the case of a maximal order:
    if ring[0] == 1:
        # Single factor:
        if factorsQQ_number == 1:
            # Number field or not:
            if factorsQQ[0][2] == -1:
                # Prettify in quadratic case:
                if len(factorsQQ[0][1]) in [2, 3]:
                    statement += """\(%s\)""" % ring_pretty(factorsQQ[0][1], 1)
                else:
                    statement += """the maximal order of \(\End (J_{%s}) \otimes \Q\)"""\
                        % fieldstring
            else:
                # Use M_2 over integers if this applies:
                if factorsQQ[0][2] == 1 and factorsQQ[0][0] == '1.1.1.1':
                    statement += """\(\mathrm{M}_2 (\Z)\)"""
                # TODO: Add flag that indicates whether we are over a PID, in
                # which case we can use the following lines:
                #if factorsQQ[0][2] == 1:
                #    statement += """\(\mathrm{M}_2 (%s)\)"""\
                #        % ring_pretty(factorsQQ[0][1], 1)
                else:
                    statement += """a maximal order of \(\End (J_{%s}) \otimes \Q\)"""\
                        % fieldstring
        # If there are two factors, then they are both at most quadratic
        # and we can prettify them
        else:
            statement += r'\(' + ' \\times '.join([ ring_pretty(factorQQ[1], 1) for
                factorQQ in factorsQQ ]) + r'\)'
    # Then the case where there is still a single factor:
    elif factorsQQ_number == 1:
        # Number field case:
        if factorsQQ[0][2] == -1:
            # Prettify in quadratic case:
            if len(factorsQQ[0][1]) in [2, 3]:
                statement += """\(%s\)""" % ring_pretty(factorsQQ[0][1], ring[0])
            else:
                statement += """an order of conductor of norm \(%s\) in \(\End (J_{%s}) \otimes \Q\)"""\
                    % (ring[0], fieldstring)
        # Otherwise mention whether the order is Eichler:
        elif ring[1] == 1:
            statement += """an Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)"""\
                % (ring[0], fieldstring)
        else:
            statement += """a non-Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)"""\
                % (ring[0], fieldstring)
    # Finally the case of two factors. We can prettify to some extent, since we
    # can describe the maximal order here
    else:
        statement += """an order of index \(%s\) in \(%s\)"""\
            % (ring[0], ' \\times '.join([ ring_pretty(factorQQ[1], 1) for
               factorQQ in factorsQQ ]))
    # End of first row:
    statement += """</td></tr>"""

    # Second row: description of endomorphism algebra factors
    statement += """<tr><td>\(\End (J_{%s}) \otimes \Q \)</td><td>\(\simeq\)</td><td>"""\
        % fieldstring
    # In the case of only one factor we either get a number field or a
    # quaternion algebra:
    if factorsQQ_number == 1:
        # First we deal with the number field case,
        # in which we have set the discriminant to be -1
        if factorsQQ[0][2] == -1:
            # Prettify if labels available, otherwise return defining polynomial:
            if factorsQQ_pretty:
                statement += """<a href=%s>%s</a>"""\
                    % (url_for("number_fields.by_label",
                       label=factorsQQ[0][0]), factorsQQ_pretty[0])
            else:
                statement += """the number field with defining polynomial \(%s\)"""\
                    % intlist_to_poly(factorsQQ[0][1])
            # Detect CM by presence of a quartic polynomial:
            if len(factorsQQ[0][1]) == 5:
                statement += """ (CM)"""
                # TODO: Get the following line to work instead of the cop-out
                # above:
                #statement += """ ({{ KNOWL('ag.complex_multiplication', title='CM') }})"""
        # Up next is the case of a matrix ring (trivial disciminant), with
        # labels and full prettification always available:
        elif factorsQQ[0][2] == 1:
            statement += """\(\mathrm{M}_2(\)<a href=%s>%s</a>\()\)"""\
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                    factorsQQ_pretty[0])
        # And finally we deal with quaternion algebras over the rationals:
        else:
            statement += """the quaternion algebra over <a href=%s>%s</a> of discriminant %s"""\
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                    factorsQQ_pretty[0], factorsQQ[0][2])
    # If there are two factors, then we get two at most quadratic fields:
    else:
        statement += """<a href=%s>%s</a> \(\\times\) <a href=%s>%s</a>"""\
            % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                factorsQQ_pretty[0], url_for("number_fields.by_label",
                label=factorsQQ[1][0]), factorsQQ_pretty[1])
    # End of second row:
    statement += """</td></tr>"""

    # Third row: description of algebra tensored with RR
    statement += """<tr><td>\(\End (J_{%s}) \otimes \R\)</td><td>\(\simeq\)</td> <td>\(%s\)</td></tr>"""\
        % (fieldstring, factorsRR_raw_to_pretty(factorsRR))

    # End of statement:
    statement += """</table>"""
    return statement

def fod_statement(fod_label, fod_poly):
    if fod_label == '1.1.1.1':
        return """All endomorphisms of the Jacobian are defined over \(\Q\)"""
    elif fod_label != '':
        fod_pretty = field_pretty(fod_label)
        fod_url = url_for("number_fields.by_label", label=fod_label)
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a) \cong \) <a href=%s>%s</a> with defining polynomial \(%s\)"""\
            % (fod_url, fod_pretty, fod_poly)
    else:
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a)\) with defining polynomial \(%s\)"""\
            % fod_poly

def st_group_statement(group):
    return """Sato-Tate group: \(%s\)""" % group

def lattice_statement_preamble():
    return """Remainder of the endomorphism lattice by subfield"""

def lattice_statement(lattice):
    statement = ''
    for ED in lattice:
        if ED[0][0]:
            # Add link and prettify if available:
            statement += """Over subfield \(F \cong\) <a href=%s>%s</a> with generator \(%s\) with minimal polynomial \(%s\)"""\
                % (url_for("number_fields.by_label", label=ED[0][0]),
                   field_pretty(ED[0][0]), strlist_to_nfelt(ED[0][2], 'a'),
                   intlist_to_poly(ED[0][1]))
        else:
            statement += """Over subfield \(F\) with generator \(%s\) with minimal polynomial \(%s\)"""\
                % (strlist_to_nfelt(ED[0][2], 'a'), intlist_to_poly(ED[0][1]))
        statement += """:<br>"""
        statement += endo_statement(ED[1], ED[2], ED[3], r'F')
        statement += st_group_statement(ED[4])
        statement += """<br>"""
        statement += gl2_simple_statement(ED[1], ED[2])
        statement += """<p></p>"""
    return statement

def spl_fod_statement(is_simple_geom, spl_fod_label, spl_fod_poly):
    if is_simple_geom:
        return """simple over \(\overline{\Q}\)"""
    elif spl_fod_label == '1.1.1.1':
        return """splits over \(\Q\)"""
    elif spl_fod_label != '':
        spl_fod_pretty =  field_pretty(spl_fod_label)
        spl_fod_url = url_for("number_fields.by_label", label=spl_fod_label)
        return """Field of minimal degree over which decomposition occurs:<br>\
        number field \(\Q (b) \cong \) <a href=%s>%s</a> with defining polynomial \(%s\)"""\
            % (spl_fod_url, spl_fod_pretty, spl_fod_poly)
    else:
        return """Field of minimal degree over which decomposition occurs:<br>\
        number field \(\Q (b)\) with defining polynomial %s"""\
            % spl_fod_poly

def spl_statement(coeffss, lmfdb_labels, condnorms):
    if len(coeffss) == 1:
        statement = """Decomposes up to isogeny as the square of an elliptic curve</p>\
        <p>Elliptic curve isogeny class representative that admits a low degree isogeny:"""
    else:
        statement = """Decomposes up to isogeny into two non-isogenous elliptic curves</p>\
        <p>Elliptic curve isogeny class representatives that admit low degree isogenies:"""
    for n in range(len(coeffss)):
        # Use labels when possible:
        lmfdb_label = lmfdb_labels[n]
        if lmfdb_label:
            statement += """<br>&nbsp;&nbsp;Elliptic curve <a href=%s>%s</a>"""\
                % (url_for_ec(lmfdb_label), lmfdb_label)
        # Otherwise give defining equation:
        else:
            statement += """<br>&nbsp;&nbsp;\(y^2 = x^3 - g_4 / 48 x - g_6 / 864\) with<br>\
            \(g_4 = %s\)<br>\
            \(g_6 = %s\)<br>\
            Conductor norm: %s"""\
                % (strlist_to_nfelt(coeffss[n][0], 'b'),
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
        self.__dict__.update(dbdata)
        self.__dict__.update(endodbdata)
        self.make_curve()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific genus 2 curve in the curves collection by its label
        """
        try:
            data = g2cdb().curves.find_one({"label" : label})
            endodata = g2cdb().endomorphisms.find_one({"label" : label})
        except AttributeError:
            return "Invalid label" # caller must catch this and raise an error
        if data:
            if endodata:
                return WebG2C(data, endodata)
            else:
                return "No genus 2 endomorphism data found for label"
        return "No genus 2 curve data found for label" # caller must catch this and raise an error

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
        data['abs_disc'] = ZZ(self.disc_key[3:])
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
        data['ic_norm'] = data['igusa_clebsch']
        data['igusa_norm'] = data['igusa']
        # Should we ever want to normalize the invariants further, then
        # uncomment the following lines:
        #data['ic_norm'] = normalize_invariants(data['igusa_clebsch'], [2, 4, 6,
        #    10])
        #data['igusa_norm'] = normalize_invariants(data['igusa'], [2, 4, 6, 8,
        #    10])
        data['ic_norm_factor_latex'] = [web_latex(zfactor(i)) for i in data['ic_norm']]
        data['igusa_norm_factor_latex'] = [ web_latex(zfactor(j)) for j in data['igusa_norm'] ]
        data['num_rat_wpts'] = ZZ(self.num_rat_wpts)
        data['two_selmer_rank'] = ZZ(self.two_selmer_rank)
        data['analytic_rank'] = ZZ(self.analytic_rank)
        data['has_square_sha'] = "square" if self.has_square_sha else "twice a square"
        data['locally_solvable'] = "yes" if self.locally_solvable else "no"
        if len(self.torsion) == 0:
            data['tor_struct'] = '\mathrm{trivial}'
        else:
            tor_struct = [ ZZ(a) for a in self.torsion ]
            data['tor_struct'] = ' \\times '.join([ '\Z/{%s}\Z' % n for n in tor_struct ])

        # Data derived from Sato-Tate group:
        isogeny_class = g2cdb().isogeny_classes.find_one({'label' : isogeny_class_label(self.label)})
        st_data = get_st_data(isogeny_class)
        for key in st_data.keys():
            data[key] = st_data[key]

        # GL_2 statement over the base field
        endodata['gl2_statement_base'] = \
            gl2_statement_base(self.factorsRR_base, r'\(\Q\)')

        # NOTE: In what follows there is some copying of code and data that is
        # stupid from the point of view of efficiency but likely better from
        # that of maintenance.

        # Endomorphism data over QQ:
        endodata['factorsQQ_base'] = self.factorsQQ_base
        endodata['factorsRR_base'] = self.factorsRR_base
        endodata['ring_base'] = self.ring_base
        endodata['endo_statement_base'] = \
            """Endomorphism ring over \(\Q\):""" + \
            endo_statement(endodata['factorsQQ_base'],
                endodata['factorsRR_base'], endodata['ring_base'], r'')
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
            endodata['gl2_statement_geom'] = \
                gl2_statement_base(self.factorsRR_geom, r'\(\overline{\Q}\)')
            endodata['endo_statement_geom'] = \
                """Endomorphism ring over \(\overline{\Q}\):""" + \
                endo_statement(
                    endodata['factorsQQ_geom'],
                    endodata['factorsRR_geom'],
                    endodata['ring_geom'],
                    r'\overline{\Q}')

        # Full endomorphism lattice minus entries already treated:
        N = len(self.lattice)
        endodata['lattice'] = (self.lattice)[1:N - 1]
        if endodata['lattice']:
            endodata['lattice_statement_preamble'] = lattice_statement_preamble()
            endodata['lattice_statement'] = lattice_statement(endodata['lattice'])

        # Splitting field description:
        #endodata['is_simple_base'] = self.is_simple_base
        endodata['is_simple_geom'] = self.is_simple_geom
        endodata['spl_fod_label'] = self.spl_fod_label
        endodata['spl_fod_poly'] = intlist_to_poly(self.spl_fod_coeffs)
        endodata['spl_fod_statement'] = spl_fod_statement(
            endodata['is_simple_geom'],
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
            endodata['spl_statement'] = spl_statement(
                endodata['spl_facs_coeffs'],
                endodata['spl_facs_labels'],
                endodata['spl_facs_condnorms'])

        # Title
        self.title = "Genus 2 Curve %s" % (self.label)

        alpha = self.label.split('.')[1]
        num = self.label.split('.')[3]

        # Lady Gaga box
        self.plot = encode_plot(eqn_list_to_curve_plot(self.min_eqn))
        self.plot_link = '<img src="%s" width="200" height="150"/>' % self.plot
        self.properties = (
            ('Label', self.label),
            (None, self.plot_link),
            ('Conductor','%s' % self.cond),
            ('Discriminant', '%s' % data['disc']),
            ('Invariants', '%s </br> %s </br> %s </br> %s' % tuple(data['ic_norm'])),
            ('Sato-Tate group', data['st_group_href']),
            ('\(%s\)' % data['real_geom_end_alg_disp'][0],
             '\(%s\)' % data['real_geom_end_alg_disp'][1]),
            ('\(\mathrm{GL}_2\)-type','%s' % data['is_gl2_type_name'])
            )
        self.friends = [
            ('Isogeny class %s' % isogeny_class_label(self.label),
             url_for(".by_url_isogeny_class_label", cond = self.cond,alpha =alpha)),
            ('L-function', url_for("l_functions.l_function_genus2_page", cond=self.cond,x=alpha)),
            ('Twists', url_for(".index_Q", g20 = self.g2inv[0], g21 = self.g2inv[1], g22 = self.g2inv[2]))
            #('Siegel modular form someday', '.')
            ]

        if not endodata['is_simple_geom']:
            self.friends += [('Elliptic curve %s' % lab,url_for_ec(lab)) for lab in endodata['spl_facs_labels'] if lab != '']
        #self.downloads = [('Download all stored data', '.')]

        # Breadcrumbs
        self.bread = (
             ('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('%s' % self.cond, url_for(".by_conductor", cond=self.cond)),
             ('%s' % alpha, url_for(".by_url_isogeny_class_label", cond=self.cond, alpha=alpha)),
             ('%s' % self.abs_disc, url_for(".by_url_isogeny_class_discriminant", cond=self.cond, alpha=alpha, disc=self.abs_disc)),
             ('%s' % num, url_for(".by_url_curve_label", cond=self.cond, alpha=alpha, disc=self.abs_disc, num=num))
             )

        # Make code that is used on the page:
        self.code = {}
        self.code['show'] = {'sage':'','magma':''} # use default show names
        self.code['curve'] = {'sage':'R.<x> = PolynomialRing(QQ); C = HyperellipticCurve(R(%s), R(%s))'%(self.data['min_eqn'][0],self.data['min_eqn'][1]),
                              'magma':'R<x> := PolynomialRing(Rationals()); C := HyperellipticCurve(R!%s, R!%s);'%(self.data['min_eqn'][0],self.data['min_eqn'][1])}
        if self.data['disc'] % 4096 == 0:
            ind2 = [a[0] for a in self.data['isogeny_class']['bad_lfactors']].index(2)
            bad2 = self.data['isogeny_class']['bad_lfactors'][ind2][1]
            magma_cond_option = ': ExcFactors:=[*<2,Valuation('+str(self.data['cond'])+',2),R!'+str(bad2)+'>*]'
        else:
            magma_cond_option = ''
        self.code['cond'] = {'magma': 'Conductor(LSeries(C%s)); Factorization($1);'% magma_cond_option}
        self.code['disc'] = {'magma':'Discriminant(C); Factorization(Integers()!$1);'}
        self.code['igusa_clebsch'] = {'sage':'C.igusa_clebsch_invariants(); [factor(a) for a in _]',
                                      'magma':'IgusaClebschInvariants(C); [Factorization(Integers()!a): a in $1];'}
        self.code['igusa'] = {'magma':'IgusaInvariants(C); [Factorization(Integers()!a): a in $1];'}
        self.code['g2'] = {'magma':'G2Invariants(C);'}
        self.code['aut'] = {'magma':'AutomorphismGroup(C); IdentifyGroup($1);'}
        self.code['autQbar'] = {'magma':'AutomorphismGroup(ChangeRing(C,AlgebraicClosure(Rationals()))); IdentifyGroup($1);'}
        self.code['num_rat_wpts'] = {'magma':'#Roots(HyperellipticPolynomials(SimplifiedModel(C)));'}
        self.code['two_selmer'] = {'magma':'TwoSelmerGroup(Jacobian(C)); NumberOfGenerators($1);'}
        self.code['has_square_sha'] = {'magma':'HasSquareSha(Jacobian(C));'}
        self.code['locally_solvable'] = {'magma':'f,h:=HyperellipticPolynomials(C); g:=4*f+h^2; HasPointsLocallyEverywhere(g,2) and (#Roots(ChangeRing(g,RealField())) gt 0 or LeadingCoefficient(g) gt 0);'}
        self.code['tor_struct'] = {'magma':'TorsionSubgroup(Jacobian(SimplifiedModel(C))); AbelianInvariants($1);'}
