# -*- coding: utf-8 -*-
import os
import sage.repl.preparse
from sage.repl.preparse import preparse
from sage.interfaces.magma import magma

from sage.all import ZZ

from lmfdb.base import getDBConnection
print "getting connection"
C= getDBConnection()
C['admin'].authenticate('lmfdb', 'lmfdb') # read-only

#import yaml
#pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
#username = pw_dict['data']['username']
#password = pw_dict['data']['password']
#C['hmfs'].authenticate(username, password)
hmf_forms = C.hmfs.forms
hmf_fields = C.hmfs.fields
fields = C.numberfields.fields

magma.eval('nice_idealstr := function(F : Bound := 10000); idealsstr := []; ideals := IdealsUpTo(Bound, F); for I in ideals do bl, g := IsPrincipal(I); if bl then s := Sprintf("[%o, %o, %o]", Norm(I), Minimum(I), F!g); else zs := Generators(I); z := zs[#zs]; m := Minimum(I); z := F![(Integers()!c) mod m : c in Eltseq(F!z)]; assert ideal<Integers(F) | [m, z]> eq I; s := Sprintf("[%o, %o, %o]", Norm(I), m, z); end if; Append(~idealsstr, s); end for; return idealsstr; end function;')

from lmfdb.number_fields.number_field import make_disc_key

P = sage.rings.polynomial.polynomial_ring_constructor.PolynomialRing(sage.rings.rational_field.RationalField(), 3, ['w', 'e', 'x'])
w, e, x = P.gens()

def import_all_data_fix_perm_primes(n, fileprefix=None, ferrors=None, test=True):
    nstr = str(n)

    if fileprefix == None:
        fileprefix = "/home/jvoight/Elements/ModFrmHilDatav1/Data/" + nstr 
    ff = open(fileprefix + "/dir.tmp", 'r')
    files = ff.readlines()
    files = [f[:-1] for f in files]
#    subprocess.call("rm dir.tmp", shell=True)

    files = [f for f in files if f.find('_old') == -1]
    for file_name in files:
        print("About to import data from file %s" % file_name)
        import_data_fix_perm_primes(file_name, fileprefix=fileprefix, ferrors=ferrors, test=test)


def import_data_fix_perm_primes(hmf_filename, fileprefix=None, ferrors=None, test=True):
    if fileprefix==None:
        fileprefix="."
    hmff = file(os.path.join(fileprefix,hmf_filename))

    if ferrors==None:
        ferrors = file('/home/jvoight/lmfdb/backups/import_data.err', 'a')

    # Parse field data
    v = hmff.readline()
    assert v[:9] == 'COEFFS :='
    coeffs = eval(v[10:].split(';')[0])
    v = hmff.readline()
    assert v[:4] == 'n :='
    n = int(v[4:][:-2])
    v = hmff.readline()
    assert v[:4] == 'd :='
    d = int(v[4:][:-2])

    magma.eval('F<w> := NumberField(Polynomial(' + str(coeffs) + '));')
    magma.eval('ZF := Integers(F);')

    # Find the corresponding field in the database of number fields
    dkey = make_disc_key(ZZ(d))[1]
    sig = "%s,%s" % (n,0)
    print("Finding field with signature %s and disc_key %s ..." % (sig,dkey))
    fields_matching = fields.find({"disc_abs_key": dkey, "signature": sig})
    cnt = fields_matching.count()
    print("Found %s fields" % cnt)
    assert cnt >= 1
    field_label = None
    co = str(coeffs)[1:-1].replace(" ","")
    for i in range(cnt):
        nf = fields_matching.next()
        print("Comparing coeffs %s with %s" % (nf['coeffs'], co))
        if nf['coeffs'] == co:
            field_label = nf['label']
    assert field_label is not None
    print "...found!"

    # Find the field in the HMF database
    print("Finding field %s in HMF..." % field_label)
    F_hmf = hmf_fields.find_one({"label": field_label})
    assert F_hmf is not None    # only proceed if field already in database
    print "...found!"

    print "Computing ideals..."
    ideals_str = F_hmf['ideals']
    # ideals = [eval(preparse(c)) for c in ideals_str] # doesn't appear to be used
    # ideals_norms = [c[0] for c in ideals] # doesn't appear to be used
    magma.eval('ideals_str := [' + ''.join(F_hmf['ideals']).replace('][', '], [') + ']')
    magma.eval('ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];')

    # Add the list of primes
    print "Computing primes..."
    v = hmff.readline()  # Skip line
    v = hmff.readline()
    assert v[:9] == 'PRIMES :='
    primes_str = v[10:][:-2]
    primes_array = [str(t) for t in eval(preparse(primes_str))]
    magma.eval('primes_array := ' + primes_str)
    magma.eval('primes := [ideal<ZF | {F!x : x in I}> : I in primes_array];')
    magma.eval('primes_indices := [Index(ideals, pp) : pp in primes];')
    try:
        assert magma('&and[primes_indices[j] gt primes_indices[j-1] : j in [2..#primes_indices]]')
        resort = False
    except AssertionError:
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Primes reordered!"
        resort = True
        magma.eval('_, sigma := Sort(primes_indices, func<x,y | x-y>);')
        magma.eval('perm := [[xx : xx in x] : x in CycleDecomposition(sigma) | #x gt 1]')
        # Check at least they have the same norm
        magma.eval('for tau in perm do assert #{Norm(ideals[primes_indices[t]]) : t in tau} eq 1; end for;')
        primes_resort = eval(magma.eval('Eltseq(sigma)'))
        primes_resort = [c - 1 for c in primes_resort]

    if resort:
        primes_indices = eval(magma.eval('primes_indices'))
        primes_str = [ideals_str[j - 1] for j in primes_indices]
        assert len(primes_array) == len(primes_str)
        print "...comparing..."
        for i in range(len(primes_array)):
            assert magma('ideal<ZF | {F!x : x in ' + primes_array[i] + '}> eq '
                        + 'ideal<ZF | {F!x : x in ' + primes_str[i] + '}>;')

        # Important also to resort the list of primes themselves!
        # not just the a_pp's
        primes_str = [primes_str[i] for i in primes_resort]
        print("Compare primes in hmf.fields\n  %s\n with NEW primes\n  %s" % (F_hmf['primes'], primes_str))
        if test:
            print("...Didn't do anything!  Just a test")
        else:
            F_hmf['primes'] = primes_str
            hmf_fields.save(F_hmf)
            print "...saved!"
