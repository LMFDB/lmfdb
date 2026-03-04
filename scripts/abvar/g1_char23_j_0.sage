from sage.schemes.elliptic_curves.ell_finite_field import curves_with_j_0_char2, curves_with_j_0_char3
from sage.databases.cremona import cremona_letter_code
from collections import defaultdict

output_filename = "output23_0_1728.txt"
counts_filename = "counts23_0_1728.txt"

qs = [2^r for r in range(1,11)] + [3^r for r in range(1,7)]

def signed_cremona_letter_code(m):
    if m >= 0:
        return cremona_letter_code(m)
    else:
        return 'a' + cremona_letter_code(-m)
    
def get_label(f,q):
    g=1
    return '%s.%s.%s' % (g, q, '_'.join(signed_cremona_letter_code(f[i]) for i in range(1,g+1)))
    
    
def output_data():
    with open(output_filename, "w") as file:
        file.write("")
    
    with open(counts_filename, "w") as file:
        file.write("")

    for q in qs:
        with open(output_filename, "a") as file:
            file.write("\n")
            to_write = "(g,q) = %s,%s\n" % (1, q)
            file.write(to_write)
            
        F.<a> = GF(q, name='a')
        label_to_curves = defaultdict(set)
        
        if q%2 == 0:
            curves = curves_with_j_0_char2(F)
        else:
            curves = curves_with_j_0_char3(F)
            
        for curve in curves:
            Lpoly = curve.frobenius_polynomial()
            to_output = (curve._equation_string()).replace(" ", "")
            label_to_curves[get_label(Lpoly,q)].add(to_output)
        
        for label, equations in label_to_curves.items():
            with open(output_filename, "a") as file:
                to_write = "%s|{%s}\n" % (label, ','.join(equations))
                file.write(to_write)
            
        with open(counts_filename, "a") as file:
            to_write = "%s,%s\n" % (q, len(label_to_curves.keys()))
            file.write(to_write)
                
output_data()