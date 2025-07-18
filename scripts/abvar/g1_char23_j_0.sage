from sage.schemes.elliptic_curves.ell_finite_field import curves_with_j_0, curves_with_j_0_char2, curves_with_j_0_char3, curves_with_j_1728
from sage.databases.cremona import cremona_letter_code
from collections import defaultdict

filename = "output23.txt"

qs = [2^r for r in range(1,11)] + [3^r for r in range(1,7)]


def signed_cremona_letter_code(m):
    if m >= 0:
        return cremona_letter_code(m)
    else:
        return 'a' + cremona_letter_code(-m)
    
def get_label(f,q):
    g=1
    return '%s.%s.%s' % (g, q, '_'.join(signed_cremona_letter_code(f[i]) for i in range(1,g+1)))
    
    
def get_entries():
    with open(filename, "w") as file:
        file.write("")

    for q in qs:
        label_to_curves = defaultdict(set)
        if q%2 == 0:
            curves = curves_with_j_0_char2(GF(q))
        else:
            curves = curves_with_j_0_char3(GF(q))
            
        for curve in curves:
            print(curve._equation_string())
            print(curve.frobenius_polynomial())
            Lpoly = curve.frobenius_polynomial()
            print(get_label(Lpoly,q))
            label_to_curves[get_label(Lpoly,q)].add(curve._equation_string())
        
        for label_key in label_to_curves:
            with open(filename, "a") as file:
                to_write = "%s|{%s}\n" % (label_key, ','.join(label_to_curves[label_key]))
                file.write(to_write)