
from lmfdb.base import getDBConnection
fields = getDBConnection().localfields.fields

# The database entries have the following fields
# p: the prime
# n: the degree
# c: discriminant exponent
# e: ramification index
# f: residue field degree
# coefs: a vector of coefficients
# gal: code for the Galois group
# inertia: code for the inertia subgroup of the Galois group
# slopes: list of wild slopes
# t: tame degree of Galois closure
# u: unramified degree of Galois closure
# unram: polynomial defining unramified subfield
# eisen: Eisenstein polynomial defining field over its unram subfield
# rf: code for discriminant root field
# hw: root number
# gms: Galois mean slope
# aut: number of automorphisms
# galT: galois T number

# unused and collides with coeffs defined in loop below
# def coeffs(s):
#    return [a for a in s[1:-1].split(',')]


def base_label(p, n, c, ind):
    return str(p) + "." + str(n) + "." + str(c) + "." + str(ind)


def lookup_or_create(label):
    item = None  # fields.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

from getme import li  # this reads in the list called li

print "finished importing getme, number = %s" % len(li)

for F in li:
 #    print F
 #   t = time.time()
    p, c, e, f, n, coeffs, gal, inertia, slopes, t, u, unram, eisen, rf, hw, gms, aut, galT = F
    data = {
        'p': p,
        'c': c,
        'e': e,
        'f': f,
        'n': n,
        'coeffs': coeffs,
        'gal': gal,
        'inertia': inertia,
        'slopes': slopes,
        't': t,
        'u': u,
        'unram': unram,
        'eisen': eisen,
        'rf': rf,
        'hw': hw,
        'gms': gms,
        'aut': aut,
        'galT': galT
    }

    index = 1
    is_new = True
    holdfield = {}
    for field in fields.find({'p': p,
                              'n': n,
                              'c': c}):
        index += 1
        if field['coeffs'] == coeffs:
            is_new = False
            holdfield = field
            break

    if is_new:
        print "new field"
        label = base_label(p, n, c, index)
        info = {'label': label}
        info.update(data)
        print "entering %s into database" % info
        fields.save(info)
    else:
        holdfield.update(data)
        print "field already in database, updating with %s" % holdfield
        fields.save(holdfield)
 #   if time.time() - t > 5:
 #       print "\t", label
 #       t = time.time()
