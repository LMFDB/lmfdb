# -*- coding: utf-8 -*-

from ast import literal_eval
from lmfdb.db_backend import db
from lmfdb.utils import web_latex, encode_plot, list_to_factored_poly_otherorder
from lmfdb.ecnf.main import split_full_label
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl
from lmfdb.transitive_group import group_display_knowl
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.genus2_curves import g2c_logger
from sage.all import latex, ZZ, QQ, CC, PolynomialRing, factor, implicit_plot, point, real, sqrt, var,  nth_prime
from sage.plot.text import text
from flask import url_for

###############################################################################
# Pretty print functions
###############################################################################

def bool_pretty(v):
    return 'yes' if v else 'no'

def intlist_to_poly(s):
    return latex(PolynomialRing(QQ, 'x')(s))

def strlist_to_nfelt(L, varname):
    return latex(PolynomialRing(QQ, varname)(L))

def list_to_min_eqn(L):
    xpoly_rng = PolynomialRing(QQ,'x')
    ypoly_rng = PolynomialRing(xpoly_rng,'y')
    poly_tup = [ xpoly_rng(tup) for tup in L ]
    lhs = ypoly_rng([0, poly_tup[1], 1])
    return str(lhs).replace("*","") + " = " + str(poly_tup[0]).replace("*","")

def url_for_ec(label):
    if not '-' in label:
        return url_for('ec.by_ec_label', label = label)
    else:
        (nf, conductor_label, class_label, number) = split_full_label(label)
        url = url_for('ecnf.show_ecnf', nf = nf, conductor_label = conductor_label, class_label = class_label, number = number)
        # fixup conductor norm labels for the form "[a,b,c]" that have been converted to urls to ensure friend matching works
        url.replace("%5B","[")
        url.replace("%2C",".")
        url.replace("%5D","]")
        return url

def url_for_ec_class(ec_label):
    if not '-' in ec_label:
        (cond, iso, num) = split_lmfdb_label(ec_label)
        return url_for('ec.by_double_iso_label', conductor=cond, iso_label=iso)
    else:
        (nf, cond, iso, num) = split_full_label(ec_label)
        return url_for('ecnf.show_ecnf_isoclass', nf=nf, conductor_label=cond, class_label=iso)

def ec_label_class(ec_label):
    x = ec_label
    while x[-1].isdigit():
        x = x[:-1]
    return x

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
        return r'\Z [' + (str(f//2) if f != 2 else "") + r'\sqrt{' + str(D) + r'}]'
    return r'\Z [\frac{1 +' + str(f) + r'\sqrt{' + str(D) + r'}}{2}]'


def QpName(p):
    if p==0:
        return "$\\R$"
    return "$\\Q_{"+str(p)+"}$"

###############################################################################
# Plot functions
###############################################################################

def inflate_interval(a,b,x=1.5):
    c = (a+b)/2
    d = (b-a)/2
    d *= x
    return (c-d,c+d)

def eqn_list_to_curve_plot(L,rat_pts):
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
    plot=sum(implicit_plot(y**2 + y*h(x) - f(x), (x,R[0],R[1]),(y,R[2],R[3]), aspect_ratio='automatic', plot_points=500, zorder=1) for R in plotzones)
    xmin=min([R[0] for R in plotzones])
    xmax=max([R[1] for R in plotzones])
    ymin=min([R[2] for R in plotzones])
    ymax=max([R[3] for R in plotzones])
    for P in rat_pts:
    	(x,y,z)=eval(P.replace(':',','))
        z=ZZ(z)
     	if z: # Do not attempt to plot points at infinity
      		x=ZZ(x)/z
      		y=ZZ(y)/z**3
      		if x >= xmin and x <= xmax and y >= ymin and y <= ymax:
       			plot += point((x,y),color='red',size=40,zorder=2)
    return plot

###############################################################################
# Name conversions for the Sato-Tate and real endomorphism algebras
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

###############################################################################
# Statement functions for displaying formatted endomorphism data
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

def end_statement(factorsQQ, factorsRR, field='', ring=None):
    # field is a latex string describing the basechange field (default is empty)
    # ring is optional, if unspecified only endomorphism algebra is described
    statement = """<table class="g2">"""
    factorsQQ_number = len(factorsQQ)
    factorsQQ_pretty = [ field_pretty(fac[0]) for fac in factorsQQ if fac[0] ]

    # endomorphism ring is an invariant of the curve but not the isogeny class, so we make it optional
    if ring:
        # First row: description of the endomorphism ring as an order in the endomorphism algebra
        statement += """<tr><td>\(\End (J_{%s})\)</td><td>\(\simeq\)</td><td>""" % field
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
                        statement += """the maximal order of \(\End (J_{%s}) \otimes \Q\)""" % field
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
                        statement += """a maximal order of \(\End (J_{%s}) \otimes \Q\)""" % field
            # If there are two factors, then they are both at most quadratic
            # and we can prettify them
            else:
                statement += r'\(' + ' \\times '.join([ ring_pretty(factorQQ[1], 1) for factorQQ in factorsQQ ]) + r'\)'
        # Then the case where there is still a single factor:
        elif factorsQQ_number == 1:
            # Number field case:
            if factorsQQ[0][2] == -1:
                # Prettify in quadratic case:
                if len(factorsQQ[0][1]) in [2, 3]:
                    statement += """\(%s\)""" % ring_pretty(factorsQQ[0][1], ring[0])
                else:
                    statement += """an order of conductor of norm \(%s\) in \(\End (J_{%s}) \otimes \Q\)""" % (ring[0], field)
            # Otherwise mention whether the order is Eichler:
            elif ring[1] == 1:
                statement += """an Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)""" % (ring[0], field)
            else:
                statement += """a non-Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)""" % (ring[0], field)
        # Finally the case of two factors. We can prettify to some extent, since we
        # can describe the maximal order here
        else:
            statement += """an order of index \(%s\) in \(%s\)""" % (ring[0], ' \\times '.join([ ring_pretty(factorQQ[1], 1) for factorQQ in factorsQQ ]))
        # End of first row:
        statement += """</td></tr>"""

    # Second row: description of endomorphism algebra factors (this is the first row if ring=None)
    statement += """<tr><td>\(\End (J_{%s}) \otimes \Q \)</td><td>\(\simeq\)</td><td>""" % field
    # In the case of only one factor we either get a number field or a
    # quaternion algebra:
    if factorsQQ_number == 1:
        # First we deal with the number field case,
        # in which we have set the discriminant to be -1
        if factorsQQ[0][2] == -1:
            # Prettify if labels available, otherwise return defining polynomial:
            if factorsQQ_pretty:
                statement += """<a href=%s>%s</a>""" % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0])
            else:
                statement += """the number field with defining polynomial \(%s\)""" % intlist_to_poly(factorsQQ[0][1])
            # Detect CM by presence of a quartic polynomial:
            if len(factorsQQ[0][1]) == 5:
                statement += """ (CM)"""
                # TODO: Get the following line to work
                #statement += """ ({{ KNOWL('ag.complex_multiplication', title='CM') }})"""
        # Up next is the case of a matrix ring (trivial disciminant), with
        # labels and full prettification always available:
        elif factorsQQ[0][2] == 1:
            statement += """\(\mathrm{M}_2(\)<a href=%s>%s</a>\()\)""" % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0])
        # And finally we deal with quaternion algebras over the rationals:
        else:
            statement += """the quaternion algebra over <a href=%s>%s</a> of discriminant %s"""\
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0], factorsQQ[0][2])
    # If there are two factors, then we get two at most quadratic fields:
    else:
        statement += """<a href=%s>%s</a> \(\\times\) <a href=%s>%s</a>"""\
            % (url_for("number_fields.by_label", label=factorsQQ[0][0]), 
                factorsQQ_pretty[0], url_for("number_fields.by_label",
                label=factorsQQ[1][0]), factorsQQ_pretty[1])
    # End of second row:
    statement += """</td></tr>"""

    # Third row: description of algebra tensored with RR (this is the second row if ring=None)
    statement += """<tr><td>\(\End (J_{%s}) \otimes \R\)</td><td>\(\simeq\)</td> <td>\(%s\)</td></tr>""" % (field, factorsRR_raw_to_pretty(factorsRR))

    # End of statement:
    statement += """</table>"""
    return statement

def end_field_statement(field_label, poly):
    if field_label == '1.1.1.1':
        return """All endomorphisms of the Jacobian are defined over \(\Q\)"""
    elif field_label != '':
        pretty = field_pretty(field_label)
        url = url_for("number_fields.by_label", label=field_label)
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a) \simeq \) <a href=%s>%s</a> with defining polynomial \(%s\)""" % (url, pretty, poly)
    else:
        return """Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a)\) with defining polynomial \(%s\)""" % poly

def end_lattice_statement(lattice):
    statement = ''
    for ED in lattice:
        if ED[0][0]:
            # Add link and prettify if available:
            statement += """Over subfield \(F \simeq \) <a href=%s>%s</a> with generator \(%s\) with minimal polynomial \(%s\)"""\
                % (url_for("number_fields.by_label", label=ED[0][0]),
                   field_pretty(ED[0][0]), strlist_to_nfelt(ED[0][2], 'a'),
                   intlist_to_poly(ED[0][1]))
        else:
            statement += """Over subfield \(F\) with generator \(%s\) with minimal polynomial \(%s\)"""\
                % (strlist_to_nfelt(ED[0][2], 'a'), intlist_to_poly(ED[0][1]))
        statement += """:<br>"""
        statement += end_statement(ED[1], ED[2], field=r'F', ring=ED[3])
        statement += """Sato Tate group: %s""" % st_link_by_name(1,4,ED[4])
        statement += """<br>"""
        statement += gl2_simple_statement(ED[1], ED[2])
        statement += """<p></p>"""
    return statement

def split_field_statement(is_simple_geom, field_label, poly):
    if is_simple_geom:
        return """Simple over \(\overline{\Q}\)"""
    elif field_label == '1.1.1.1':
        return """Splits over \(\Q\)"""
    elif field_label != '':
        pretty =  field_pretty(field_label)
        url = url_for("number_fields.by_label", label=field_label)
        return """Splits over the number field \(\Q (b) \simeq \) <a href=%s>%s</a> with defining polynomial:<br>&nbsp;&nbsp;\(%s\)"""\
            % (url, pretty, poly)
    else:
        return """Splits over the number field \(\Q (b)\) with defining polynomial:<br>&nbsp;&nbsp;\(%s\)""" % poly

def split_statement(coeffs, labels, condnorms):
    if len(coeffs) == 1:
        statement = """Decomposes up to isogeny as the square of the elliptic curve:"""
    else:
        statement = """Decomposes up to isogeny as the product of the non-isogenous elliptic curves:"""
    for n in range(len(coeffs)):
        # Use labels when possible:
        label = labels[n] if labels else ''
        if label:
            statement += """<br>&nbsp;&nbsp;Elliptic curve <a href=%s>%s</a>""" % (url_for_ec(label), label)
        # Otherwise give defining equation:
        else:
            statement += """<br>&nbsp;&nbsp;\(y^2 = x^3 - g_4 / 48 x - g_6 / 864\) with<br>\
            \(g_4 = %s\)<br>\
            \(g_6 = %s\)<br>\
            Conductor norm: %s""" \
            % (strlist_to_nfelt(coeffs[n][0], 'b'), strlist_to_nfelt(coeffs[n][1], 'b'), condnorms[n])
    return statement

# create friend entry from url (typically coming from lfunc_instances)
def lfunction_friend_from_url(url):
    if url[0] == '/':
        url = url[1:]
    parts = url.split("/")
    if parts[0] == "Genus2Curve" and parts[1] == "Q":
        label = parts[2] + "." + parts[3]
        return ("Isogeny class " + label, "/" + url)
    if parts[0] == "EllipticCurve" and parts[1] == "Q":
        label = parts[2] + "." + parts[3]
        return ("EC isogeny class " + label, "/" + url)
    if parts[0] == "EllipticCurve":
        label = parts[1] + "-" + parts[2] + "-" + parts[3]
        return ("EC isogeny class " + label, "/" + url)
    if parts[0] == "ModularForm" and parts[1] == "GL2" and parts[2] == "TotallyReal" and parts[4] == "holomorphic":
        label = parts[5]
        return ("Hilbert MF " + label, "/" + url)
    return (url, "/" + url)

# add new friend to list of friends, but only if really new (e.g. don't add an elliptic curve and its isogeny class)
def add_friend(friends,friend):
    for oldfriend in friends:
        if oldfriend[0] == friend[0] or oldfriend[1] in friend[1] or friend[1] in oldfriend[1]:
            return
    friends.append(friend)

###############################################################################
# Genus 2 curve class definition
###############################################################################

class WebG2C(object):
    """
    Class for a genus 2 curve (or isogeny class) over Q.  Attributes include:
        data -- information about the curve and its Jacobian to be displayed (taken from db and polished)
        plot -- (possibly empty) plot of the curve over R (omitted for isogeny classes)
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels of related objects (e.g. L-function, Jacobian factors, etc...)
        code -- code snippets for relevant attributes in data
        bread -- bread crumbs for home page (conductor, isogeny class id, discriminant, curve id)
        title -- title to display on home page
    """
    def __init__(self, curve, endo, tama, ratpts, is_curve=True):
        self.make_object(curve, endo, tama, ratpts, is_curve)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific genus 2 curve or isogeny class in the curves collection by its label.
        It label is an isogeny class label, constructs an object for an arbitrarily chosen curve in the isogeny class
        Constructs the WebG2C object if the curve is found, raises an error otherwise
        """
        try:
            slabel = label.split(".")
            if len(slabel) == 2:
                curve = db.g2c_curves.lucky({"class" : label})
            elif len(slabel) == 4:
                curve = db.g2c_curves.lookup(label)
            else:
                raise ValueError("Invalid genus 2 label %s." % label)
        except AttributeError:
            raise ValueError("Invalid genus 2 label %s." % label)
        if not curve:
            if len(slabel) == 2:
                raise KeyError("Genus 2 isogeny class %s not found in the database." % label)
            else:
                raise KeyError("Genus 2 curve %s not found in database." % label)
        endo = db.g2c_endomorphisms.lookup(curve['label'])
        if not endo:
            g2c_logger.error("Endomorphism data for genus 2 curve %s not found in database." % label)
            raise KeyError("Endomorphism data for genus 2 curve %s not found in database." % label)
        tama = list(db.g2c_tamagawa.search({"label": curve['label']}))
        if len(tama) == 0:
            g2c_logger.error("Tamagawa number data for genus 2 curve %s not found in database." % label)
            raise KeyError("Tamagawa number data for genus 2 curve %s not found in database." % label)
        if len(slabel)==4:
            ratpts = db.g2c_ratpts.lookup(curve['label'])
            if not ratpts:
                g2c_logger.warning("No rational points data for genus 2 curve %s found in database." % label)
        else:
            ratpts = {}
        return WebG2C(curve, endo, tama, ratpts, is_curve=(len(slabel)==4))

    def make_object(self, curve, endo, tama, ratpts, is_curve):
        from lmfdb.genus2_curves.main import url_for_curve_label

        # all information about the curve, its Jacobian, isogeny class, and endomorphisms goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        data['label'] = curve['label'] if is_curve else curve['class']
        data['slabel'] = data['label'].split('.')

        # set attributes common to curves and isogeny classes here
        data['Lhash'] = str(curve['Lhash'])
        data['cond'] = ZZ(curve['cond'])
        data['cond_factor_latex'] = web_latex(factor(int(data['cond'])))
        data['analytic_rank'] = ZZ(curve['analytic_rank'])
        data['st_group'] = curve['st_group']
        data['st_group_link'] = st_link_by_name(1,4,data['st_group'])
        data['st0_group_name'] = st0_group_name(curve['real_geom_end_alg'])
        data['is_gl2_type'] = curve['is_gl2_type']
        data['root_number'] = ZZ(curve['root_number'])
        data['lfunc_url'] = url_for("l_functions.l_function_genus2_page", cond=data['slabel'][0], x=data['slabel'][1])
        data['bad_lfactors'] = literal_eval(curve['bad_lfactors'])
        data['bad_lfactors_pretty'] = [ (c[0], list_to_factored_poly_otherorder(c[1])) for c in data['bad_lfactors']]

        if is_curve:
            # invariants specific to curve
            data['class'] = curve['class']
            data['abs_disc'] = ZZ(curve['abs_disc'])
            data['disc'] = curve['disc_sign'] * data['abs_disc']
            data['min_eqn'] = literal_eval(curve['eqn'])
            data['min_eqn_display'] = list_to_min_eqn(data['min_eqn'])
            data['disc_factor_latex'] = web_latex(factor(data['disc']))
            data['igusa_clebsch'] = [ZZ(a) for a in literal_eval(curve['igusa_clebsch_inv'])]
            data['igusa'] = [ZZ(a) for a in literal_eval(curve['igusa_inv'])]
            data['g2'] = [QQ(a) for a in literal_eval(curve['g2_inv'])]
            data['igusa_clebsch_factor_latex'] = [web_latex(zfactor(i)) for i in data['igusa_clebsch']]
            data['igusa_factor_latex'] = [ web_latex(zfactor(j)) for j in data['igusa'] ]
            data['aut_grp_id'] = curve['aut_grp_id']
            data['geom_aut_grp_id'] = curve['geom_aut_grp_id']
            data['num_rat_wpts'] = ZZ(curve['num_rat_wpts'])
            data['two_selmer_rank'] = ZZ(curve['two_selmer_rank'])
            data['has_square_sha'] = "square" if curve['has_square_sha'] else "twice a square"
            P = curve['non_solvable_places']
            if len(P):
                sz = "except over "
                sz += ", ".join([QpName(p) for p in P])
                last = " and"
                if len(P) > 2:
                    last = ", and"
                sz = last.join(sz.rsplit(",",1))
            else:
                sz = "everywhere"
            data['non_solvable_places'] = sz
            data['torsion_order'] = curve['torsion_order']
            data['torsion_factors'] = [ ZZ(a) for a in literal_eval(curve['torsion_subgroup']) ]
            if len(data['torsion_factors']) == 0:
                data['torsion_subgroup'] = '\mathrm{trivial}'
            else:
                data['torsion_subgroup'] = ' \\times '.join([ '\Z/{%s}\Z' % n for n in data['torsion_factors'] ])
            data['end_ring_base'] = endo['ring_base']
            data['end_ring_geom'] = endo['ring_geom']
            data['tama'] = ''
            for item in tama:
            	if item['tamagawa_number'] > 0:
            	    tamgwnr = str(item['tamagawa_number'])
            	else:
            	    tamgwnr = 'N/A'
            	data['tama'] += tamgwnr + ' (p = ' + str(item['p']) + '), '
            data['tama'] = data['tama'][:-2] # trim last ", "
            if ratpts:
                if len(ratpts['rat_pts']):
                    data['rat_pts'] = ',  '.join(web_latex('(' +' : '.join(map(str, P)) + ')') for P in ratpts['rat_pts'])
                data['rat_pts_v'] =  2 if ratpts['rat_pts_v'] else 1
                # data['mw_rank'] = ratpts['mw_rank']
                # data['mw_rank_v'] = ratpts['mw_rank_v']
            else:
                data['rat_pts_v'] = 0
            if curve['two_torsion_field'][0]:
                data['two_torsion_field_knowl'] = nf_display_knowl (curve['two_torsion_field'][0], field_pretty(curve['two_torsion_field'][0]))
            else:
                t = curve['two_torsion_field']
                data['two_torsion_field_knowl'] = """splitting field of \(%s\) with Galois group %s"""%(intlist_to_poly(t[1]),group_display_knowl(t[2][0],t[2][1]))
        else:
            # invariants specific to isogeny class
            curves_data = list(db.g2c_curves.search({"class" : curve['class']}, ['label','eqn']))
            if not curves_data:
                raise KeyError("No curves found in database for isogeny class %s of genus 2 curve %s." %(curve['class'],curve['label']))
            data['curves'] = [ {"label" : c['label'], "equation_formatted" : list_to_min_eqn(literal_eval(c['eqn'])), "url": url_for_curve_label(c['label'])} for c in curves_data ]
            lfunc_data = db.lfunc_lfunctions.lucky({'Lhash':str(curve['Lhash'])})
            if not lfunc_data:
                raise KeyError("No Lfunction found in database for isogeny class of genus 2 curve %s." %curve['label'])
            if lfunc_data and lfunc_data.get('euler_factors'):
                data['good_lfactors'] = [[nth_prime(n+1),lfunc_data['euler_factors'][n]] for n in range(len(lfunc_data['euler_factors'])) if nth_prime(n+1) < 30 and (data['cond'] % nth_prime(n+1))]
                data['good_lfactors_pretty'] = [ (c[0], list_to_factored_poly_otherorder(c[1])) for c in data['good_lfactors']]
        # Endomorphism data over QQ:
        data['gl2_statement_base'] = gl2_statement_base(endo['factorsRR_base'], r'\(\Q\)')
        data['factorsQQ_base'] = endo['factorsQQ_base']
        data['factorsRR_base'] = endo['factorsRR_base']
        data['end_statement_base'] = """Endomorphism %s over \(\Q\):<br>""" %("ring" if is_curve else "algebra") + \
            end_statement(data['factorsQQ_base'], endo['factorsRR_base'], ring=data['end_ring_base'] if is_curve else None)

        # Field over which all endomorphisms are defined
        data['end_field_label'] = endo['fod_label']
        data['end_field_poly'] = intlist_to_poly(endo['fod_coeffs'])
        data['end_field_statement'] = end_field_statement(data['end_field_label'], data['end_field_poly'])
        
        # Endomorphism data over QQbar:
        data['factorsQQ_geom'] = endo['factorsQQ_geom']
        data['factorsRR_geom'] = endo['factorsRR_geom']
        if data['end_field_label'] != '1.1.1.1':
            data['gl2_statement_geom'] = gl2_statement_base(data['factorsRR_geom'], r'\(\overline{\Q}\)')
            data['end_statement_geom'] = """Endomorphism %s over \(\overline{\Q}\):""" %("ring" if is_curve else "algebra") + \
                end_statement(data['factorsQQ_geom'], data['factorsRR_geom'], field=r'\overline{\Q}', ring=data['end_ring_geom'] if is_curve else None)
        data['real_geom_end_alg_name'] = end_alg_name(curve['real_geom_end_alg'])

        # Endomorphism data over intermediate fields not already treated (only for curves, not necessarily isogeny invariant):
        if is_curve:
            data['end_lattice'] = (endo['lattice'])[1:-1]
            if data['end_lattice']:
                data['end_lattice_statement'] = end_lattice_statement(data['end_lattice'])

        # Field over which the Jacobian decomposes (base field if Jacobian is geometrically simple)
        data['is_simple_geom'] = endo['is_simple_geom']
        data['split_field_label'] = endo['spl_fod_label']
        data['split_field_poly'] = intlist_to_poly(endo['spl_fod_coeffs'])
        data['split_field_statement'] = split_field_statement(data['is_simple_geom'], data['split_field_label'], data['split_field_poly'])

        # Elliptic curve factors for non-simple Jacobians
        if not data['is_simple_geom']:
            data['split_coeffs'] = endo['spl_facs_coeffs']
            if 'spl_facs_labels' in endo and len(endo['spl_facs_labels']) == len(endo['spl_facs_coeffs']):
                data['split_labels'] = endo['spl_facs_labels']
            data['split_condnorms'] = endo['spl_facs_condnorms']
            data['split_statement'] = split_statement(data['split_coeffs'], data.get('split_labels'), data['split_condnorms'])

        # Properties
        self.properties = properties = [('Label', data['label'])]
        if is_curve:
            self.plot = encode_plot(eqn_list_to_curve_plot(data['min_eqn'], data['rat_pts'].split(',') if 'rat_pts' in data else []))
            plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)

            properties += [
                (None, plot_link),
                ('Conductor',str(data['cond'])),
                ('Discriminant', str(data['disc'])),
                ]
        properties += [
            ('Sato-Tate group', data['st_group_link']),
            ('\(\\End(J_{\\overline{\\Q}}) \\otimes \\R\)', '\(%s\)' % data['real_geom_end_alg_name']),
            ('\(\\overline{\\Q}\)-simple', bool_pretty(data['is_simple_geom'])),
            ('\(\mathrm{GL}_2\)-type', bool_pretty(data['is_gl2_type'])),
            ]

        # Friends
        self.friends = friends = [('L-function', data['lfunc_url'])]
        if is_curve:
            friends.append(('Isogeny class %s.%s' % (data['slabel'][0], data['slabel'][1]), url_for(".by_url_isogeny_class_label", cond=data['slabel'][0], alpha=data['slabel'][1])))
        for friend_url in db.lfunc_instances.search({'Lhash':data['Lhash']}, 'url'):
            if '|' in friend_url:
                for url in friend_url.split('|'):
                    add_friend (friends, lfunction_friend_from_url(url))
            else:
                add_friend (friends, lfunction_friend_from_url(friend_url))
        if 'split_labels' in data:
            for friend_label in data['split_labels']:
                if is_curve:
                    add_friend (friends, ("Elliptic curve " + friend_label, url_for_ec(friend_label)))
                else:
                    add_friend (friends, ("EC isogeny class " + ec_label_class(friend_label), url_for_ec_class(friend_label)))
        if is_curve:
            friends.append(('Twists', url_for(".index_Q", g20 = str(data['g2'][0]), g21 = str(data['g2'][1]), g22 = str(data['g2'][2]))))

        # Breadcrumbs
        self.bread = bread = [
             ('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('%s' % data['slabel'][0], url_for(".by_conductor", cond=data['slabel'][0])),
             ('%s' % data['slabel'][1], url_for(".by_url_isogeny_class_label", cond=data['slabel'][0], alpha=data['slabel'][1]))
             ]
        if is_curve:
            bread += [
                ('%s' % data['slabel'][2], url_for(".by_url_isogeny_class_discriminant", cond=data['slabel'][0], alpha=data['slabel'][1], disc=data['slabel'][2])),
                ('%s' % data['slabel'][3], url_for(".by_url_curve_label", cond=data['slabel'][0], alpha=data['slabel'][1], disc=data['slabel'][2], num=data['slabel'][3]))
                ]

        # Title
        self.title = "Genus 2 " + ("Curve " if is_curve else "Isogeny Class ") + data['label']

        # Code snippets (only for curves)
        if not is_curve:
            return
        self.code = code = {}
        code['show'] = {'sage':'','magma':''} # use default show names
        code['curve'] = {'sage':'R.<x> = PolynomialRing(QQ); C = HyperellipticCurve(R(%s), R(%s))'%(data['min_eqn'][0],data['min_eqn'][1]),
                              'magma':'R<x> := PolynomialRing(Rationals()); C := HyperellipticCurve(R!%s, R!%s);'%(data['min_eqn'][0],data['min_eqn'][1])}
        if data['abs_disc'] % 4096 == 0:
            ind2 = [a[0] for a in data['bad_lfactors']].index(2)
            bad2 = data['bad_lfactors'][ind2][1]
            magma_cond_option = ': ExcFactors:=[*<2,Valuation('+str(data['cond'])+',2),R!'+str(bad2)+'>*]'
        else:
            magma_cond_option = ''
        code['cond'] = {'magma': 'Conductor(LSeries(C%s)); Factorization($1);'% magma_cond_option}
        code['disc'] = {'magma':'Discriminant(C); Factorization(Integers()!$1);'}
        code['igusa_clebsch'] = {'sage':'C.igusa_clebsch_invariants(); [factor(a) for a in _]',
                                      'magma':'IgusaClebschInvariants(C); [Factorization(Integers()!a): a in $1];'}
        code['igusa'] = {'magma':'IgusaInvariants(C); [Factorization(Integers()!a): a in $1];'}
        code['g2'] = {'magma':'G2Invariants(C);'}
        code['aut'] = {'magma':'AutomorphismGroup(C); IdentifyGroup($1);'}
        code['autQbar'] = {'magma':'AutomorphismGroup(ChangeRing(C,AlgebraicClosure(Rationals()))); IdentifyGroup($1);'}
        code['num_rat_wpts'] = {'magma':'#Roots(HyperellipticPolynomials(SimplifiedModel(C)));'}
        if ratpts:
            code['rat_pts'] = {'magma': '[' + ','.join(["C![%s,%s,%s]"%(p[0],p[1],p[2]) for p in ratpts['rat_pts']]) + '];' }
        code['two_selmer'] = {'magma':'TwoSelmerGroup(Jacobian(C)); NumberOfGenerators($1);'}
        code['has_square_sha'] = {'magma':'HasSquareSha(Jacobian(C));'}
        code['locally_solvable'] = {'magma':'f,h:=HyperellipticPolynomials(C); g:=4*f+h^2; HasPointsEverywhereLocally(g,2) and (#Roots(ChangeRing(g,RealField())) gt 0 or LeadingCoefficient(g) gt 0);'}
        code['torsion_subgroup'] = {'magma':'TorsionSubgroup(Jacobian(SimplifiedModel(C))); AbelianInvariants($1);'}
