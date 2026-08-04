from sage.all import PolynomialRing, NumberField, QQ, gcd, latex, factor

import re
RE_EXP = r"\^(\d+)"

def bracket_me(m):
    return "^{%s}" % (m.group(0)).split("^")[1]

def fix_brackets(rec):
    if rec.get('plane_model_latex'):
        latex = rec['plane_model_latex']
        latex = re.sub(RE_EXP, bracket_me,latex)
        rec['plane_model_latex'] = latex
    return rec

def plane_map_constant(rec):
    R = PolynomialRing(QQ, 'x')
    K = NumberField(R(rec['base_field']), 'nu')
    if rec.get('plane_constant'):
        a = K(rec['plane_constant'])
        rec['plane_map_constant'] = 1/a
    return rec

def plane_map_constant_factored(rec):
    R = PolynomialRing(QQ, 'x')
    K = NumberField(R(rec['base_field']), 'nu')
    if rec.get('plane_constant'):
        a = K(rec['plane_constant'])
        a = 1/a
        if a == 1:
            rec['plane_map_constant_factored'] = ''
        else:
            d = a.denominator()
            num = a*d
            num_list = num.list()
            n = gcd(num_list)
            num_list = [el/n for el in num_list]
            poly = K(num_list)
            # now LaTeX everything
            s = ''
            if a in QQ:
                s = '-' if a.sign()==-1 else '' # if a in QQ, keep track of sign
                poly_lat = ''
            else:
                if ("+" in str(poly)) or ("-" in str(poly)):
                    poly_lat = "(%s)" % latex(poly)
                else:
                    poly_lat = latex(poly)
            if d == 1:
                rec['plane_map_constant_factored'] = "%s" % (latex(factor(n))+poly_lat)
            else:
                rec['plane_map_constant_factored'] = r"%s\frac{%s}{%s}%s" % (s,latex(factor(n)), latex(factor(d)), poly_lat)
    return rec

def pretty_print_factor(f):
    d = f.denominator()
    if d == 1:
        return (f.factor())
    else:
        n = f.numerator().factor()
        return ('({})/({})'.format(n, d.factor()))
