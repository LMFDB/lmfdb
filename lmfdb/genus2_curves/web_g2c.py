# -*- coding: utf-8 -*-

from ast import literal_eval
import os
import re
import yaml
from lmfdb import db
from lmfdb.utils import (key_for_numerically_sort, encode_plot, prop_int_pretty,
                         list_to_factored_poly_otherorder, make_bigint, names_and_urls,
                         display_knowl, web_latex_factored_integer, integer_squarefree_part, integer_prime_divisors)
from lmfdb.lfunctions.LfunctionDatabase import get_instances_by_Lhash_and_trace_hash
from lmfdb.ecnf.main import split_full_label as split_ecnf_label
from lmfdb.elliptic_curves.web_ec import split_lmfdb_label
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.number_fields.web_number_field import nf_display_knowl
from lmfdb.cluster_pictures.web_cluster_picture import cp_display_knowl
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl
from lmfdb.sato_tate_groups.main import st_display_knowl, st_anchor
from lmfdb.genus2_curves import g2c_logger
from sage.all import latex, ZZ, QQ, CC, lcm, gcd, PolynomialRing, implicit_plot, point, real, sqrt, var,  nth_prime
from sage.plot.text import text
from flask import url_for

###############################################################################
# Pretty print functions
###############################################################################

def decimal_pretty(s,min_chars_before_decimal=1,max_chars_after_decimal=6,max_chars=10):
    m = s.index(".") if "." in s else len(s)
    if m < min_chars_before_decimal:
        s = (min_chars_before_decimal-m)*' ' + s
    n = min(min(max_chars,len(s)),min_chars_before_decimal+max_chars_after_decimal+1)
    # truncate for the moment (as we do elsewhere in the LMFDB, revisit if we switch to rounding
    return s[:n]

def bool_pretty(v):
    return 'yes' if v else 'no'

def intlist_to_poly(s):
    return latex(PolynomialRing(QQ, 'x')(s))

def strlist_to_nfelt(L, varname):
    return latex(PolynomialRing(QQ, varname)(L))

def min_eqn_pretty(fh):
    xR = PolynomialRing(QQ,'x')
    polys = [ xR(tup) for tup in fh ]
    yR = PolynomialRing(xR,'y')
    lhs = yR([0, polys[1], 1])
    return str(lhs).replace("*","") + " = " + str(polys[0]).replace("*","")

def simplify_hyperelliptic(fh):
    xR = PolynomialRing(QQ,'x')
    f = 4*xR(fh[0]) + xR(fh[1])**2
    n = gcd(f.coefficients())
    f = (integer_squarefree_part(n) * f) / n
    return f.coefficients(sparse=False)

def simplify_hyperelliptic_point(fh, pt):
    xR = PolynomialRing(QQ,'x')
    f = 4*xR(fh[0]) + xR(fh[1])**2
    f1 = xR(fh[1])
    n = gcd(f.coefficients())
    xzR = PolynomialRing(QQ,['x','z'])
    z = xzR('z')
    f1 = (xzR(f1)*z**(4-len(fh[1]))).homogenize(z)
    return [pt[0], (2*pt[1] + f1([pt[0],pt[2]])) / n, pt[2]]

def comp_poly(fh):
    xR = PolynomialRing(QQ,'x')
    f = 4*xR(fh[0]) + xR(fh[1])**2
    f1 = xR(fh[1])
    n = gcd(f.coefficients())
    xyzR = PolynomialRing(QQ,['x','y','z'])
    y = xyzR('y')
    z = xyzR('z')
    f1 = (xyzR(f1)*z**(4-len(fh[1]))).homogenize(z)
    return (2*y + f1) / n

def min_eqns_pretty(fh):
    xR = PolynomialRing(QQ,'x')
    polys = [ xR(tup) for tup in fh ]
    yR = PolynomialRing(xR,'y')
    lhs = yR([0, polys[1], 1])
    slist = [str(lhs).replace("*","") + " = " + str(polys[0]).replace("*","")]
    xzR = PolynomialRing(QQ,['x','z'])
    z = xzR('z')
    polys = [x.homogenize(z) for x in [xzR(polys[0])*z**(7-len(fh[0])),
                                       xzR(polys[1])*z**(4-len(fh[1]))]]
    yR = PolynomialRing(xzR,'y')
    lhs = yR([0, polys[1], 1])
    slist.append(str(lhs).replace("*","") + " = " + str(polys[0]).replace("*",""))
    slist.append("y^2 = " + str(xR(simplify_hyperelliptic(fh))).replace("*",""))
    return slist


def url_for_ec(label):
    if '-' not in label:
        return url_for('ec.by_ec_label', label = label)
    else:
        (nf, cond, isog, num) = split_ecnf_label(label)
        url = url_for('ecnf.show_ecnf', nf = nf, conductor_label = cond, class_label = isog, number = num)
        return url

def url_for_ec_class(ec_label):
    if '-' not in ec_label:
        (cond, iso, num) = split_lmfdb_label(ec_label)
        return url_for('ec.by_double_iso_label', conductor=cond, iso_label=iso)
    else:
        (nf, cond, isog, num) = split_ecnf_label(ec_label)
        return url_for('ecnf.show_ecnf_isoclass', nf=nf, conductor_label=cond, class_label=isog)

def ec_label_class(ec_label):
    x = ec_label
    while x[-1].isdigit():
        x = x[:-1]
    return x

def g2c_lmfdb_label(cond, alpha, disc, num):
    return "%s.%s.%s.%s" % (cond, alpha, disc, num)

g2c_lmfdb_label_regex = re.compile(r'(\d+)\.([a-z]+)\.(\d+)\.(\d+)')

def split_g2c_lmfdb_label(lab):
    return g2c_lmfdb_label_regex.match(lab).groups()

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
        return r'\H'
    elif factorsRR == ['M_2(RR)']:
        return r'\mathrm{M}_2 (\R)'
    elif factorsRR == ['M_2(CC)']:
        return r'\mathrm{M}_2 (\C)'

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
        return r"$\R$"
    return r"$\Q_{"+str(p)+"}$"

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
        return text(r"$X(\mathbb{R})=\emptyset$",(1,1),fontsize=50)
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
        (x,y,z)=P
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

def real_geom_end_alg_name(name):
    name_dict = {
        "R":r"\R",
        "C":r"\C",
        "R x R":r"\R \times \R",
        "C x R":r"\C \times \R",
        "C x C":r"\C \times \C",
        "M_2(R)":r"\mathrm{M}_2(\R)",
        "M_2(C)":r"\mathrm{M}_2(\C)"
        }
    if name in name_dict.keys():
        return name_dict[name]
    else:
        return name

def geom_end_alg_name(name):
    name_dict = {
        "Q":r"\Q",
        "RM":r"\mathsf{RM}",
        "Q x Q":r"\Q \times \Q",
        "CM x Q":r"\mathsf{CM} \times \Q",
        "CM":r"\mathsf{CM}",
        "CM x CM":r"\mathsf{CM} \times \mathsf{CM}",
        "QM":r"\mathsf{QM}",
        "M_2(Q)":r"\mathrm{M}_2(\Q)",
        "M_2(CM)":r"\mathrm{M}_2(\mathsf{CM})"
        }
    if name in name_dict.keys():
        return name_dict[name]
    else:
        return name

def end_alg_name(name):
    name_dict = {
        "Q":r"\Q",
        "RM":r"\mathsf{RM}",
        "Q x Q":r"\Q \times \Q",
        "CM":r"\mathsf{CM}",
        "M_2(Q)":r"\mathrm{M}_2(\Q)",
        }
    if name in name_dict.keys():
        return name_dict[name]
    else:
        return name

def st0_group_name(name):
    st0_dict = {
        'M_2(C)':r'\mathrm{U}(1)',
        'M_2(R)':r'\mathrm{SU}(2)',
        'C x C':r'\mathrm{U}(1)\times\mathrm{U}(1)',
        'C x R':r'\mathrm{U}(1)\times\mathrm{SU}(2)',
        'R x R':r'\mathrm{SU}(2)\times\mathrm{SU}(2)',
        'R':r'\mathrm{USp}(4)'
        }
    if name in st0_dict.keys():
        return st0_dict[name]
    else:
        return name

def plot_from_label(label):
    curve = db.g2c_curves.lookup(label)
    ratpts = db.g2c_ratpts.lookup(curve['label'])
    min_eqn = literal_eval(curve['eqn'])
    plot = encode_plot(eqn_list_to_curve_plot(min_eqn, ratpts['rat_pts']))
    return plot

###############################################################################
# Statement functions for displaying formatted endomorphism data
###############################################################################

def gl2_statement_base(factorsRR, base):
    if factorsRR in [ ['RR', 'RR'], ['CC'] ]:
        return r"Of \(\GL_2\)-type over " + base
    return r"Not of \(\GL_2\)-type over " + base

def gl2_simple_statement(factorsQQ, factorsRR):
    if factorsRR in [ ['RR', 'RR'], ['CC'] ]:
        gl2 = r"Of \(\GL_2\)-type"
    else:
        gl2 = r"Not of \(\GL_2\)-type"
    if len(factorsQQ) == 1 and factorsQQ[0][2] != 1:
        simple = "simple"
    else:
        simple = "not simple"
    return gl2 + ", " + simple

def end_statement(factorsQQ, factorsRR, field='', ring=None):
    # field is a latex string describing the basechange field (default is empty)
    # ring is optional, if unspecified only endomorphism algebra is described
    statement = '<table style="margin-left: 10px; margin-top: -12px">'
    factorsQQ_number = len(factorsQQ)
    factorsQQ_pretty = [ field_pretty(fac[0]) for fac in factorsQQ if fac[0] ]

    # endomorphism ring is an invariant of the curve but not the isogeny class, so we make it optional
    if ring:
        # First row: description of the endomorphism ring as an order in the endomorphism algebra
        statement += r"<tr><td>\(\End (J_{%s})\)</td><td>\(\simeq\)</td><td>" % field
        # First the case of a maximal order:
        if ring[0] == 1:
            # Single factor:
            if factorsQQ_number == 1:
                # Number field or not:
                if factorsQQ[0][2] == -1:
                    # Prettify in quadratic case:
                    if len(factorsQQ[0][1]) in [2, 3]:
                        statement += r"\(%s\)" % ring_pretty(factorsQQ[0][1], 1)
                    else:
                        statement += r"the maximal order of \(\End (J_{%s}) \otimes \Q\)" % field
                else:
                    # Use M_2 over integers if this applies:
                    if factorsQQ[0][2] == 1 and factorsQQ[0][0] == '1.1.1.1':
                        statement += r"\(\mathrm{M}_2 (\Z)\)"
                    # TODO: Add flag that indicates whether we are over a PID, in
                    # which case we can use the following lines:
                    #if factorsQQ[0][2] == 1:
                    #    statement += (r"\(\mathrm{M}_2 (%s)\)"
                    #        % ring_pretty(factorsQQ[0][1], 1))
                    else:
                        statement += r"a maximal order of \(\End (J_{%s}) \otimes \Q\)" % field
            # If there are two factors, then they are both at most quadratic
            # and we can prettify them
            else:
                statement += r'\(' + r' \times '.join([ ring_pretty(factorQQ[1], 1) for factorQQ in factorsQQ ]) + r'\)'
        # Then the case where there is still a single factor:
        elif factorsQQ_number == 1:
            # Number field case:
            if factorsQQ[0][2] == -1:
                # Prettify in quadratic case:
                if len(factorsQQ[0][1]) in [2, 3]:
                    statement += r"\(%s\)" % ring_pretty(factorsQQ[0][1], ring[0])
                else:
                    statement += r"an order of conductor of norm \(%s\) in \(\End (J_{%s}) \otimes \Q\)" % (ring[0], field)
            # Otherwise mention whether the order is Eichler:
            elif ring[1] == 1:
                statement += r"an Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)" % (ring[0], field)
            else:
                statement += r"a non-Eichler order of index \(%s\) in a maximal order of \(\End (J_{%s}) \otimes \Q\)" % (ring[0], field)
        # Finally the case of two factors. We can prettify to some extent, since we
        # can describe the maximal order here
        else:
            statement += r"an order of index \(%s\) in \(%s\)" % (ring[0], r' \times '.join([ ring_pretty(factorQQ[1], 1) for factorQQ in factorsQQ ]))
        # End of first row:
        statement += "</td></tr>"

    # Second row: description of endomorphism algebra factors (this is the first row if ring=None)
    statement += r"<tr><td>\(\End (J_{%s}) \otimes \Q \)</td><td>\(\simeq\)</td><td>" % field
    # In the case of only one factor we either get a number field or a
    # quaternion algebra:
    if factorsQQ_number == 1:
        # First we deal with the number field case,
        # in which we have set the discriminant to be -1
        if factorsQQ[0][2] == -1:
            # Prettify if labels available, otherwise return defining polynomial:
            if factorsQQ_pretty:
                statement += "<a href=%s>%s</a>" % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0])
            else:
                statement += r"the number field with defining polynomial \(%s\)" % intlist_to_poly(factorsQQ[0][1])
            # Detect CM by presence of a quartic polynomial:
            if len(factorsQQ[0][1]) == 5:
                statement += " (CM)"
                # TODO: Get the following line to work
                #statement += " ({{ KNOWL('ag.complex_multiplication', title='CM') }})"
        # Up next is the case of a matrix ring (trivial disciminant), with
        # labels and full prettification always available:
        elif factorsQQ[0][2] == 1:
            statement += r"\(\mathrm{M}_2(\)<a href=%s>%s</a>\()\)" % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0])
        # And finally we deal with quaternion algebras over the rationals:
        else:
            statement += ("the quaternion algebra over <a href=%s>%s</a> of discriminant %s"
                % (url_for("number_fields.by_label", label=factorsQQ[0][0]), factorsQQ_pretty[0], factorsQQ[0][2]))
    # If there are two factors, then we get two at most quadratic fields:
    else:
        statement += (r"<a href=%s>%s</a> \(\times\) <a href=%s>%s</a>"
            % (url_for("number_fields.by_label", label=factorsQQ[0][0]),
                factorsQQ_pretty[0], url_for("number_fields.by_label",
                label=factorsQQ[1][0]), factorsQQ_pretty[1]))
    # End of second row:
    statement += "</td></tr>"

    # Third row: description of algebra tensored with RR (this is the second row if ring=None)
    statement += r"<tr><td>\(\End (J_{%s}) \otimes \R\)</td><td>\(\simeq\)</td> <td>\(%s\)</td></tr>" % (field, factorsRR_raw_to_pretty(factorsRR))

    # End of statement:
    statement += "</table>"
    return statement

def end_field_statement(field_label, poly):
    if field_label == '1.1.1.1':
        return r"All \(\overline{\Q}\)-endomorphisms of the Jacobian are defined over \(\Q\)."
    elif field_label != '':
        pretty = field_pretty(field_label)
        url = url_for("number_fields.by_label", label=field_label)
        return r"""Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a) \simeq \) <a href=%s>%s</a> with defining polynomial \(%s\)""" % (url, pretty, poly)
    else:
        return r"""Smallest field over which all endomorphisms are defined:<br>
        Galois number field \(K = \Q (a)\) with defining polynomial \(%s\)""" % poly

def end_lattice_statement(lattice):
    statement = ''
    for ED in lattice:
        statement += "<p>"
        if ED[0][0]:
            # Add link and prettify if available:
            statement += (r"Over subfield \(F \simeq \) <a href=%s>%s</a> with generator \(%s\) with minimal polynomial \(%s\)"
                % (url_for("number_fields.by_label", label=ED[0][0]),
                   field_pretty(ED[0][0]), strlist_to_nfelt(ED[0][2], 'a'),
                   intlist_to_poly(ED[0][1])))
        else:
            statement += (r"Over subfield \(F\) with generator \(%s\) with minimal polynomial \(%s\)"
                % (strlist_to_nfelt(ED[0][2], 'a'), intlist_to_poly(ED[0][1])))
        statement += ":\n"
        statement += end_statement(ED[1], ED[2], field='F', ring=ED[3])
        statement += "&nbsp;&nbsp;Sato Tate group: %s" % st_display_knowl(ED[4])
        statement += "<br>&nbsp;&nbsp;"
        statement += gl2_simple_statement(ED[1], ED[2])
        statement += "</p>\n"
    return statement

def split_field_statement(is_simple_geom, field_label, poly):
    if is_simple_geom:
        return r"Simple over \(\overline{\Q}\)"
    elif field_label == '1.1.1.1':
        return r"Splits over \(\Q\)"
    elif field_label != '':
        pretty =  field_pretty(field_label)
        url = url_for("number_fields.by_label", label=field_label)
        return (r"Splits over the number field \(\Q (b) \simeq \) <a href=%s>%s</a> with defining polynomial:<br>&nbsp;&nbsp;\(%s\)"
            % (url, pretty, poly))
    else:
        return r"Splits over the number field \(\Q (b)\) with defining polynomial:<br>&nbsp;&nbsp;\(%s\)" % poly

def split_statement(coeffs, labels, condnorms):
    if len(coeffs) == 1:
        statement = "Decomposes up to isogeny as the square of the elliptic curve isogeny class:"
    else:
        statement = "Decomposes up to isogeny as the product of the non-isogenous elliptic curve isogeny classes:"
    for n in range(len(coeffs)):
        # Use labels when possible:
        label = labels[n] if labels else ''
        if label:
            statement += "<br>&nbsp;&nbsp;Elliptic curve isogeny class <a href=%s>%s</a>" % (url_for_ec_class(label), ec_label_class(label))
        # Otherwise give defining equation:
        else:
            statement += r"<br>&nbsp;&nbsp;\(y^2 = x^3 - g_4 / 48 x - g_6 / 864\) with"
            statement += r"<br>&nbsp;&nbsp;\(g_4 = %s\)<br>&nbsp;&nbsp;\(g_6 = %s\)" % tuple(map (lambda x: strlist_to_nfelt(x,'b'),coeffs[n]))
            statement += "<br>&nbsp;&nbsp; Conductor norm: %s" % condnorms[n]
    return statement

# function for displaying GSp4 subgroup data
def gsp4_subgroup_data(label):
    try:
        data = db.gps_gsp4zhat.lookup(label)
    except ValueError:
        return "Invalid label for subgroup of GSp(4,Zhat): %s" % label
    row_wrap = lambda cap, val: "<tr><td>%s: </td><td>%s</td></tr>\n" % (cap, val)
    matrix = lambda m: r'$\begin{bmatrix}%s&%s&%s&%s\\%s&%s&%s&%s\\%s&%s&%s&%s\\%s&%s&%s&%s\end{bmatrix}$' % (m[0],m[1],m[2],m[3],m[4],m[5],m[6],m[7],m[8],m[9],m[10],m[11],m[12],m[13],m[14],m[15])
    info = '<table>\n'
    info += row_wrap('Subgroup <b>%s</b>' % (label),  "<small>" + ', '.join([matrix(m) for m in data['generators']]) + "</small>")
    info += "<tr><td></td><td></td></tr>\n"
    info += row_wrap('Level', data['level'])
    info += row_wrap('Index', data['index'])

    info += row_wrap('Contains $-1$', "yes" if data['quadratic_twists'][0] == label else "no")
    N = ZZ(data['level'])
    ell = N.prime_divisors()[0]
    e = N.valuation(ell)
    if e == 1:
        info += row_wrap("(%s,%s)-isogeny field degree" % (ell,ell), min([r[1] for r in data['isogeny_orbits'] if r[0] == ell]))
        info += row_wrap("Cyclic %s-torsion field degree" % (ell), min([r[1] for r in data['orbits'] if r[0] == ell]))
        fulltorsflddeg = ell**4*(ell**4-1)*(ell**2-1)*(ell-1) // data['index']
        info += row_wrap("Full %s-torsion field degree" % (ell), fulltorsflddeg)
    info += "</table>\n"
    return info

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
    if parts[0] == "ModularForm" and parts[1] == "GL2" and parts[2] == "ImaginaryQuadratic":
        label = '.'.join(parts[4:6])
        return ("Bianchi MF " + label, "/" + url)
    if parts[0] == "ModularForm" and parts[1] == "GL2" and parts[2] == "Q" and parts[3] == "holomorphic":
        label = '.'.join(parts[4:8])
        return ("Modular form " + label, "/" + url)
    return (url, "/" + url)

# add new friend to list of friends, but only if really new (don't add an elliptic curve and its isogeny class)
def add_friend(friends, friend):
    for oldfriend in friends:
        if oldfriend[0] == friend[0] or oldfriend[1] in friend[1] or friend[1] in oldfriend[1]:
            return
        # compare again with slashes converted to dots to deal with minor differences in url/label formatting
        olddots = ".".join(oldfriend[1].split("/"))
        newdots = ".".join(friend[1].split("/"))
        if olddots in newdots or newdots in olddots:
            return
    friends.append(friend)

def th_wrap(kwl, title, colspan=1):
    if colspan > 1:
        return ' <th colspan=%s>%s</th>' % (colspan, display_knowl(kwl, title=title))
    else:
        return ' <th>%s</th>' % display_knowl(kwl, title=title)
def td_wrapl(val):
    return r' <td align="left">\(%s\)</td>' % val
def td_wrapr(val):
    return r' <td align="right">\(%s\)</td>' % val
def td_wrapc(val):
    return r' <td align="center">\(%s\)</td>' % val
def td_wrapcn(val):
    return r' <td align="center">%s</td>' % val

def point_string(P):
    return '(' + ' : '.join(map(str, P)) + ')'

def mw_gens_table(invs,gens,hts,pts,comp=PolynomialRing(QQ,['x','y','z'])('y')):
    def divisor_data(P):
        R = PolynomialRing(QQ, ['x','z'])
        x = R('x')
        z = R('z')
        xP, yP = P[0], P[1]
        xden, yden = lcm([r[1] for r in xP]), lcm([r[1] for r in yP])
        xD = sum([ZZ(xden)*ZZ(xP[i][0])/ZZ(xP[i][1])*x**i*z**(len(xP)-i-1) for i in range(len(xP))])
        if str(xD.factor())[:4] == "(-1)":
            xD = -xD
        yD = sum([ZZ(yden)*ZZ(yP[i][0])/ZZ(yP[i][1])*x**i*z**(len(yP)-i-1) for i in range(len(yP))])
        yD = comp(x, yD, z)
        return [make_bigint(elt, 10) for elt in [str(xD.factor()).replace("**","^").replace("*",""), str(yden)+"y" if yden > 1 else "y", str(yD).replace("**","^").replace("*","")]], xD, yD, yden
    if not invs:
        return ''
    gentab = ['<table class="ntdata">', '<thead>', '<tr>',
              th_wrap('g2c.mw_generator', 'Generator'),
              th_wrap('g2c.mw_generator', '$D_0$'), '<th></th>', '<th></th>', '<th></th>', '<th></th>', '<th></th>',
              th_wrap('ag.canonical_height', 'Height'),
              th_wrap('g2c.mw_generator_order', 'Order'),
              '</tr>', '</thead>', '<tbody>']
    for i in range(len(invs)):
        gentab.append('<tr>')
        D,xD,yD,yden = divisor_data(gens[i])
        D0 = [P for P in pts if P[2] and xD(P[0],P[2]) == 0 and yD(P[0],P[2]) == yden*P[1]]
        Dinf = [P for P in pts if P[2] == 0 and not (xD(P[0],P[2]) == 0 and yD(P[0],P[2]) == yden*P[1])]
        div = (r'2 \cdot' + point_string(D0[0]) if len(D0)==1 and len(Dinf)!=1 else ' + '.join([point_string(P) for P in D0])) if D0 else 'D_0'
        div += ' - '
        div += (r'2 \cdot' + point_string(Dinf[0]) if len(Dinf)==1 and len(D0)!=1 else ' - '.join([point_string(P) for P in Dinf])) if Dinf else r'D_\infty'
        gentab.extend([td_wrapl(div), td_wrapr(D[0]),td_wrapc('='),td_wrapl("0,"),td_wrapr(D[1]),td_wrapc("="),td_wrapl(D[2]),
                       td_wrapc(decimal_pretty(str(hts[i]))) if invs[i] == 0 else td_wrapc('0'), td_wrapc(r'\infty') if invs[i]==0 else td_wrapc(invs[i])])
        gentab.append('</tr>')
    gentab.extend(['</tbody>', '</table>'])
    return '\n'.join(gentab)

def mw_gens_simple_table(invs,gens,hts,pts,fh):
    spts = [simplify_hyperelliptic_point(fh,pt) for pt in pts]
    return mw_gens_table(invs,gens,hts,spts,comp=comp_poly(fh))

def local_table(N,D,tama,bad_lpolys,cluster_pics):
    loctab = ['<table class="ntdata">', '<thead>', '<tr>',
              th_wrap('ag.bad_prime', 'Prime'),
              th_wrap('ag.conductor', r'ord(\(N\))'),
              th_wrap('g2c.discriminant', r'ord(\(\Delta\))'),
              th_wrap('g2c.tamagawa', 'Tamagawa'),
              th_wrap('g2c.bad_lfactors', 'L-factor'),
              th_wrap('ag.cluster_picture', 'Cluster picture'),
              '</tr>', '</thead>', '<tbody>']
    for p in integer_prime_divisors(D):
        loctab.append('  <tr>')
        cplist = [r for r in tama if r[0] == p]
        if cplist:
            cp = str(cplist[0][1]) if cplist[0][1] > 0 else '?'
        else:
            cp = '1' if N%p != 0 else '?'
        Lplist = [r for r in bad_lpolys if r[0] == p]
        if Lplist:
            Lp = Lplist[0][1]
        else:
            Lp = '?'
        Cluslist = [r for r in cluster_pics if r[0] == p]
        if Cluslist:
            ClusThmb = '<img src="' + Cluslist[0][2] + '" height=19 style="position: relative; top: 50%; transform: translateY(10%);" />'
            Clus = cp_display_knowl(Cluslist[0][1], img=ClusThmb)
        else:
            Clus = ''
        loctab.extend([td_wrapr(p),td_wrapc(N.ord(p)),td_wrapc(D.ord(p)),td_wrapc(cp),td_wrapl(Lp),td_wrapcn(Clus)])
        loctab.append('  </tr>')
    loctab.extend(['</tbody>', '</table>'])
    return '\n'.join(loctab)

def galrep_table(galrep):
    galtab = ['<table class="ntdata">', '<thead>', '<tr>',
              th_wrap('', r'Prime \(\ell\)'),
              th_wrap('g2c.galois_rep_image', r'mod-\(\ell\) image'),
              '</tr>', '</thead>', '<tbody>']
    for i in range(len(galrep)):
        p = galrep[i]['prime']
        modellimage_lbl = galrep[i]['modell_image']
        galtab.append('  <tr>')
        modellimg = display_knowl('gsp4.subgroup_data', title=modellimage_lbl, kwargs={'label':modellimage_lbl})
        galtab.extend([td_wrapc(p),td_wrapcn(modellimg)])
        galtab.append('  </tr>')
    galtab.extend(['</tbody>', '</table>'])
    return '\n'.join(galtab)

def ratpts_table(pts,pts_v):
    def sorted_points(pts):
        return sorted(pts,key=lambda P:(max([abs(x) for x in P]),sum([abs(x) for x in P])))
    if len(pts) > 1:
        # always put points at infinity first, regardless of height
        pts = sorted_points([P for P in pts if P[2] == 0]) + sorted_points([P for P in pts if P[2] != 0])
    kid = 'g2c.all_rational_points' if pts_v else 'g2c.known_rational_points'
    if len(pts) == 0:
        if pts_v:
            return 'This curve has no %s.' % display_knowl(kid, 'rational points')
        else:
            return 'No %s for this curve.' % display_knowl(kid, 'rational points are known')
    spts = [point_string(P) for P in pts]
    caption = 'All points' if pts_v else 'Known points'
    tabcols = 6
    if len(pts) <= tabcols+1:
        return r'%s: \(%s\)' % (display_knowl(kid,caption),r',\, '.join(spts))
    ptstab = ['<table class="ntdata">', '<thead>', '<tr>', th_wrap(kid, caption, colspan=tabcols)]
    ptstab.extend(['</tr>', '</thead>', '<tbody>'])
    for i in range(0,len(pts),6):
        ptstab.append('<tr>')
        ptstab.extend([td_wrapc(P) for P in spts[i:i+6]])
        if i+6 > len(pts):
            ptstab.extend(['<td></td>' for i in range(i+6-len(pts))]) # pad last line
        ptstab.append('</tr>')
    ptstab.extend(['</tbody>', '</table>'])
    return '\n'.join(ptstab)

def ratpts_simpletable(pts,pts_v,fh):
    spts = [simplify_hyperelliptic_point(fh, pt) for pt in pts]
    return ratpts_table(spts,pts_v)


###############################################################################
# Genus 2 curve class definition
###############################################################################

class WebG2C():
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
    def __init__(self, curve, endo, tama, ratpts, clus, galrep, is_curve=True):
        self.make_object(curve, endo, tama, ratpts, clus, galrep, is_curve)

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
                curve = db.g2c_curves.lucky({"class": label})
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
        clus = []
        for x in tama:
            if x['p'] != 2:
                try:
                    clusentry = db.cluster_pictures.lucky({"label": x['cluster_label']})
                    #clusimg = clusentry['image']
                    clusthmb = clusentry['thumbnail']
                    clus.append([x['p'], x['cluster_label'], clusthmb])
                except Exception:
                    g2c_logger.error("Cluster picture data for genus 2 curve %s not found in database." % label)
                    raise KeyError("Cluster picture data for genus 2 curve %s not found in database." % label)
        galrep = list(db.g2c_galrep.search({'lmfdb_label': curve['label']},['prime', 'modell_image']))
        return WebG2C(curve, endo, tama, ratpts, clus, galrep, is_curve=(len(slabel)==4))

    def make_object(self, curve, endo, tama, ratpts, clus, galrep, is_curve):
        from lmfdb.genus2_curves.main import url_for_curve_label

        # all information about the curve, its Jacobian, isogeny class, and endomorphisms goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        data['label'] = curve['label'] if is_curve else curve['class']
        data['slabel'] = data['label'].split('.')

        # set attributes common to curves and isogeny classes here
        data['Lhash'] = str(curve['Lhash'])
        data['cond'] = ZZ(curve['cond'])
        data['cond_factor_latex'] = web_latex_factored_integer(data['cond'])
        data['analytic_rank'] = ZZ(curve['analytic_rank'])
        data['mw_rank'] = ZZ(0) if curve.get('mw_rank') is None else ZZ(curve['mw_rank']) # 0 will be marked as a lower bound
        data['mw_rank_proved'] = curve['mw_rank_proved']
        data['analytic_rank_proved'] = curve['analytic_rank_proved']
        data['hasse_weil_proved'] = curve['hasse_weil_proved']
        data['st_group'] = curve['st_group']
        data['st_group_link'] = st_display_knowl(curve['st_label'])
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
            data['min_eqn_display'] = min_eqns_pretty(data['min_eqn'])
            data['disc_factor_latex'] = web_latex_factored_integer(data['disc'])
            data['igusa_clebsch'] = [ZZ(a) for a in literal_eval(curve['igusa_clebsch_inv'])]
            data['igusa'] = [ZZ(a) for a in literal_eval(curve['igusa_inv'])]
            data['g2'] = [QQ(a) for a in literal_eval(curve['g2_inv'])]
            data['igusa_clebsch_factor_latex'] = [web_latex_factored_integer(i) for i in data['igusa_clebsch']]
            data['igusa_factor_latex'] = [ web_latex_factored_integer(j) for j in data['igusa'] ]
            data['aut_grp'] = abstract_group_display_knowl(curve['aut_grp_label'], f"${curve['aut_grp_tex']}$")
            data['geom_aut_grp'] = abstract_group_display_knowl(curve['geom_aut_grp_label'], f"${curve['geom_aut_grp_tex']}$")
            data['num_rat_wpts'] = ZZ(curve['num_rat_wpts'])
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
            data['two_selmer_rank'] = ZZ(curve['two_selmer_rank'])
            data['torsion_order'] = curve['torsion_order']

            data['end_ring_base'] = endo['ring_base']
            data['end_ring_geom'] = endo['ring_geom']
            data['real_period'] = decimal_pretty(str(curve['real_period']))
            data['regulator'] = decimal_pretty(str(curve['regulator'])) if curve['regulator'] > -0.5 else 'unknown'
            if data['mw_rank'] == 0 and data['mw_rank_proved']:
                data['regulator'] = '1' # display an exact 1 when we know this

            data['tamagawa_product'] = ZZ(curve['tamagawa_product']) if curve.get('tamagawa_product') else 0
            data['analytic_sha'] = ZZ(curve['analytic_sha']) if curve.get('analytic_sha') else 0
            data['leading_coeff'] = decimal_pretty(str(curve['leading_coeff'])) if curve['leading_coeff'] else 'unknown'

            data['rat_pts'] = ratpts['rat_pts']
            data['rat_pts_v'] =  ratpts['rat_pts_v']
            data['rat_pts_table'] = ratpts_table(ratpts['rat_pts'],ratpts['rat_pts_v'])
            data['rat_pts_simple_table'] = ratpts_simpletable(ratpts['rat_pts'],ratpts['rat_pts_v'],data['min_eqn'])

            data['mw_gens_v'] = ratpts['mw_gens_v']
            lower = len([n for n in ratpts['mw_invs'] if n == 0])
            upper = data['analytic_rank']
            invs = ratpts['mw_invs'] if data['mw_gens_v'] or lower >= upper else [0 for n in range(upper-lower)] + ratpts['mw_invs']
            if len(invs) == 0:
                data['mw_group'] = 'trivial'
            else:
                data['mw_group'] = r'\(' + r' \times '.join([ (r'\Z' if n == 0 else r'\Z/{%s}\Z' % n) for n in invs]) + r'\)'
            if lower >= upper:
                data['mw_gens_table'] = mw_gens_table (ratpts['mw_invs'], ratpts['mw_gens'], ratpts['mw_heights'], ratpts['rat_pts'])
                data['mw_gens_simple_table'] = mw_gens_simple_table (ratpts['mw_invs'], ratpts['mw_gens'], ratpts['mw_heights'], ratpts['rat_pts'], data['min_eqn'])

            if curve['two_torsion_field'][0]:
                data['two_torsion_field_knowl'] = nf_display_knowl (curve['two_torsion_field'][0], field_pretty(curve['two_torsion_field'][0]))
            else:
                t = curve['two_torsion_field']
                data['two_torsion_field_knowl'] = r"splitting field of \(%s\) with Galois group %s" % (intlist_to_poly(t[1]),transitive_group_display_knowl(f"{t[2][0]}T{t[2][1]}"))

            tamalist = [[item['p'],item['tamagawa_number']] for item in tama]
            data['local_table'] = local_table (data['cond'],data['abs_disc'],tamalist,data['bad_lfactors_pretty'],clus)
            data['galrep_table'] = galrep_table (galrep)

            lmfdb_label = data['label']
            cond, alpha, disc, num = split_g2c_lmfdb_label(lmfdb_label)
            self.downloads = [#('Frobenius eigenvalues to text', url_for(".download_G2C_fouriercoeffs", label=self.lmfdb_label, limit=1000)),
                          ('All stored data to text', url_for(".download_G2C_all", label=lmfdb_label)),
                          ('Code to Magma', url_for(".g2c_code_download", conductor=cond, iso=alpha, discriminant=disc, number=num, label=lmfdb_label, download_type='magma'))#,
                          #('Code to SageMath', url_for(".g2c_code_download", conductor=cond, iso=alpha, discriminant=disc, number=num, label=lmfdb_label, download_type='sage')),
                          #('Code to GP', url_for(".g2c_code_download", conductor=cond, iso=alpha, discriminant=disc, number=num, label=lmfdb_label, download_type='gp'))
            ]
            #TODO (?) also for the isogeny class
        else:
            # invariants specific to isogeny class
            curves_data = list(db.g2c_curves.search({"class": curve['class']}, ['label','eqn']))
            if not curves_data:
                raise KeyError("No curves found in database for isogeny class %s of genus 2 curve %s." %(curve['class'],curve['label']))
            data['curves'] = [ {"label": c['label'], "equation_formatted": min_eqn_pretty(literal_eval(c['eqn'])), "url": url_for_curve_label(c['label'])} for c in curves_data ]
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
        data['end_statement_base'] = (r"Endomorphism %s over \(\Q\):<br>" %("ring" if is_curve else "algebra") +
            end_statement(data['factorsQQ_base'], endo['factorsRR_base'], ring=data['end_ring_base'] if is_curve else None))

        # Field over which all endomorphisms are defined
        data['end_field_label'] = endo['fod_label']
        data['end_field_poly'] = intlist_to_poly(endo['fod_coeffs'])
        data['end_field_statement'] = end_field_statement(data['end_field_label'], data['end_field_poly'])

        # Endomorphism data over QQbar:
        data['factorsQQ_geom'] = endo['factorsQQ_geom']
        data['factorsRR_geom'] = endo['factorsRR_geom']
        if data['end_field_label'] != '1.1.1.1':
            data['gl2_statement_geom'] = gl2_statement_base(data['factorsRR_geom'], r'\(\overline{\Q}\)')
            data['end_statement_geom'] = (r"Endomorphism %s over \(\overline{\Q}\):" %("ring" if is_curve else "algebra") +
                end_statement(data['factorsQQ_geom'], data['factorsRR_geom'], field=r'\overline{\Q}', ring=data['end_ring_geom'] if is_curve else None))
        data['real_geom_end_alg_name'] = real_geom_end_alg_name(curve['real_geom_end_alg'])
        data['geom_end_alg_name'] = geom_end_alg_name(curve['geom_end_alg'])
        data['end_alg_name'] = end_alg_name(curve['end_alg'])

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
            plot_from_db = db.g2c_plots.lucky({"label": curve['label']})
            if (plot_from_db is None):
                self.plot = encode_plot(eqn_list_to_curve_plot(data['min_eqn'], ratpts['rat_pts'] if ratpts else []))
            else:
                self.plot = plot_from_db['plot']
            plot_link = '<a href="{0}"><img src="{0}" width="200" height="150"/></a>'.format(self.plot)

            properties += [
                (None, plot_link),
                ('Conductor', prop_int_pretty(data['cond'])),
                ('Discriminant', prop_int_pretty(data['disc'])),
                ]
            if data['mw_rank_proved']:
                properties += [('Mordell-Weil group', data['mw_group'])]
        else:
            properties += [('Conductor', prop_int_pretty(data['cond']))]
        properties += [
            ('Sato-Tate group', st_anchor(curve['st_label'])),
            (r'\(\End(J_{\overline{\Q}}) \otimes \R\)', r'\(%s\)' % data['real_geom_end_alg_name']),
            (r'\(\End(J_{\overline{\Q}}) \otimes \Q\)', r'\(%s\)' % data['geom_end_alg_name']),
            (r'\(\End(J) \otimes \Q\)', r'\(%s\)' % data['end_alg_name']),
            (r'\(\overline{\Q}\)-simple', bool_pretty(data['is_simple_geom'])),
            (r'\(\mathrm{GL}_2\)-type', bool_pretty(data['is_gl2_type'])),
            ]

        if is_curve:
            self.downloads = [("Underlying data", url_for(".G2C_data", label=data['label']))]
        else:
            self.downloads = []

        # Friends
        self.friends = friends = []
        if is_curve:
            friends.append(('Isogeny class %s.%s' % (data['slabel'][0], data['slabel'][1]), url_for(".by_url_isogeny_class_label", cond=data['slabel'][0], alpha=data['slabel'][1])))

        # first deal with ECs and MFs
        ecs = []
        mfs = []
        if 'split_labels' in data:
            for friend_label in data['split_labels']:
                if is_curve:
                    ecs.append(("Elliptic curve " + friend_label, url_for_ec(friend_label)))
                else:
                    ecs.append(("Elliptic curve " + ec_label_class(friend_label), url_for_ec_class(friend_label)))
                try:
                    cond, iso = ec_label_class(friend_label).split(".")
                    newform_label = ".".join([cond, str(2), 'a', iso])
                    mfs.append(("Modular form " + newform_label, url_for("cmf.by_url_newform_label", level=cond, weight=2, char_orbit_label='a', hecke_orbit=iso)))
                except ValueError:
                    # means the friend isn't an elliptic curve over Q; adding Hilbert/Bianchi modular forms
                    # is dealt with via the L-functions instances below
                    pass

        ecs.sort(key=lambda x: key_for_numerically_sort(x[0]))
        mfs.sort(key=lambda x: key_for_numerically_sort(x[0]))

        # then again EC from lfun
        instances = []
        for elt in db.lfunc_instances.search({'Lhash':data['Lhash'], 'type': 'ECQP'}, 'url'):
            instances.extend(elt.split('|'))

        # and then the other isogeny friends
        instances.extend([
            elt['url'] for elt in
            get_instances_by_Lhash_and_trace_hash(data["Lhash"],
                                                  4,
                                                  int(data["Lhash"])
                                                  )
            ])

        exclude = {elt[1].rstrip('/').lstrip('/') for elt in self.friends
                   if elt[1]}
        exclude.add(data['lfunc_url'].lstrip('/L/').rstrip('/'))
        for elt in ecs + mfs + names_and_urls(instances, exclude=exclude):
            # because of the splitting we must use G2C specific code
            add_friend(friends, elt)
        if is_curve:
            friends.append(('Twists', url_for(".index_Q",
                                              g20=str(data['g2'][0]),
                                              g21=str(data['g2'][1]),
                                              g22=str(data['g2'][2]))))

        friends.append(('L-function', data['lfunc_url']))

        # Breadcrumbs
        self.bread = bread = [
             ('Genus 2 curves', url_for(".index")),
             (r'$\Q$', url_for(".index_Q")),
             ('%s' % data['slabel'][0], url_for(".by_conductor", cond=data['slabel'][0])),
             ('%s' % data['slabel'][1], url_for(".by_url_isogeny_class_label", cond=data['slabel'][0], alpha=data['slabel'][1]))
             ]
        if is_curve:
            bread += [
                ('%s' % data['slabel'][2], url_for(".by_url_isogeny_class_discriminant", cond=data['slabel'][0], alpha=data['slabel'][1], disc=data['slabel'][2])),
                ('%s' % data['slabel'][3], url_for(".by_url_curve_label", cond=data['slabel'][0], alpha=data['slabel'][1], disc=data['slabel'][2], num=data['slabel'][3]))
                ]

        # Title
        self.title = "Genus 2 " + ("curve " if is_curve else "isogeny class ") + data['label']

        # Code snippets (only for curves)
        if not is_curve:
            return
        self.code = code = {}
        code['show'] = {'sage':'','magma':''} # use default show names
        f,h = fh = data['min_eqn']
        g = simplify_hyperelliptic(fh)
        code['curve'] = {'sage':'R.<x> = PolynomialRing(QQ); C = HyperellipticCurve(R(%s), R(%s));'%(f,h),
                         'magma':'R<x> := PolynomialRing(Rationals()); C := HyperellipticCurve(R!%s, R!%s);'%(f,h) }
        code['simple_curve'] = {'sage':'X = HyperellipticCurve(R(%s))'%(g), 'magma':'X,pi:= SimplifiedModel(C);' }
        if data['abs_disc'] % 4096 == 0:
            ind2 = [a[0] for a in data['bad_lfactors']].index(2)
            bad2 = data['bad_lfactors'][ind2][1]
            magma_cond_option = ': ExcFactors:=[*<2,Valuation('+str(data['cond'])+',2),R!'+str(bad2)+'>*]'
        else:
            magma_cond_option = ''
        code['cond'] = {'magma': 'Conductor(LSeries(C%s)); Factorization($1);'% magma_cond_option}
        code['disc'] = {'magma':'Discriminant(C); Factorization(Integers()!$1);'}
        code['geom_inv'] = {'sage':'C.igusa_clebsch_invariants(); [factor(a) for a in _]',
                            'magma':'IgusaClebschInvariants(C); IgusaInvariants(C); G2Invariants(C);'}
        code['aut'] = {'magma':'AutomorphismGroup(C); IdentifyGroup($1);'}
        code['autQbar'] = {'magma':'AutomorphismGroup(ChangeRing(C,AlgebraicClosure(Rationals()))); IdentifyGroup($1);'}
        code['num_rat_wpts'] = {'magma':'#Roots(HyperellipticPolynomials(SimplifiedModel(C)));'}
        if ratpts:
            code['rat_pts'] = {'magma': '[' + ','.join(["C![%s,%s,%s]"%(p[0],p[1],p[2]) for p in ratpts['rat_pts']]) + ']; // minimal model'}
            code['rat_pts_simp'] = {'magma': '[' + ','.join(["C![%s,%s,%s]"%(p[0],p[1],p[2]) for p in [simplify_hyperelliptic_point(data['min_eqn'], pt) for pt in ratpts['rat_pts']]]) + ']; // simplified model'}
        code['mw_group'] = {'magma':'MordellWeilGroupGenus2(Jacobian(C));'}
        code['two_selmer'] = {'magma':'TwoSelmerGroup(Jacobian(C)); NumberOfGenerators($1);'}
        code['has_square_sha'] = {'magma':'HasSquareSha(Jacobian(C));'}
        code['locally_solvable'] = {'magma':'f,h:=HyperellipticPolynomials(C); g:=4*f+h^2; HasPointsEverywhereLocally(g,2) and (#Roots(ChangeRing(g,RealField())) gt 0 or LeadingCoefficient(g) gt 0);'}
        code['torsion_subgroup'] = {'magma':'TorsionSubgroup(Jacobian(SimplifiedModel(C))); AbelianInvariants($1);'}

        self._code = None

    def get_code(self):
        if self._code is None:

            # read in code.yaml from current directory:
            _curdir = os.path.dirname(os.path.abspath(__file__))
            self._code =  yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)

            # Fill in placeholders for this specific curve:
            for lang in ['magma']: #TODO: 'sage', 'pari',
                self._code['curve'][lang] = self._code['curve'][lang] % (self.data['min_eqn'])

        return self._code
