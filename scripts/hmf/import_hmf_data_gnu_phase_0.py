# -*- coding: utf-8 -*-
Dan_test = True
import os.path

from pymongo.mongo_client import MongoClient
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb')

# Saved login procedure from old script; not working now (JV 07-2017)
# from lmfdb.lmfdb.base import getDBConnection
# C= getDBConnection()
# C['admin'].authenticate('lmfdb', 'lmfdb') # read-only

# if Dan_test:
#    import sys
#    from sage.all import preparse
#    # sys.path.append('/Users/d_yasaki/repos/lmfdb/lmfdb/scripts/hmf')
# else:
from sage.all import preparse
# import sage.misc.preparser
# from sage.misc.preparser import preparse

from sage.interfaces.magma import magma

from sage.all import ZZ, QQ, PolynomialRing

from scripts.hmf.check_conjugates import fix_one_label
from sage.databases.cremona import class_to_int
import yaml

# Assumes running from lmfdb root directory
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['hmfs'].authenticate(username, password)

hmf_forms = C.hmfs.forms_dan
hmf_fields = C.hmfs.fields
fields = C.numberfields.fields

magma.eval('nice_idealstr := function(F : Bound := 10000); idealsstr := []; ideals := IdealsUpTo(Bound, F); for I in ideals do bl, g := IsPrincipal(I); if bl then s := Sprintf("[%o, %o, %o]", Norm(I), Minimum(I), F!g); else zs := Generators(I); z := zs[#zs]; m := Minimum(I); z := F![(Integers()!c) mod m : c in Eltseq(F!z)]; assert ideal<Integers(F) | [m, z]> eq I; s := Sprintf("[%o, %o, %o]", Norm(I), m, z); end if; Append(~idealsstr, s); end for; return idealsstr; end function;')

from lmfdb.number_fields.number_field import make_disc_key
from lmfdb.hilbert_modular_forms.web_HMF import construct_full_label

P = PolynomialRing(QQ, 3, ['w', 'e', 'x'])
w, e, x = P.gens()

def import_all_data(n, fileprefix=None, ferrors=None, test=True):
    nstr = str(n)

    if fileprefix == None:
        fileprefix = "/home/jvoight/Elements/ModFrmHilDatav1.1/Data/" + nstr + "/dir.tmp"
    ff = open(fileprefix, 'r')
    files = ff.readlines()
    files = [f[:-1] for f in files]

    files = [f for f in files if f.find('_old') == -1]
    for file_name in files:
        print("About to import data from file %s" % file_name)
        import_data(file_name, fileprefix=fileprefix, ferrors=ferrors, test=test)


def import_data(hmf_filename, fileprefix=None, ferrors=None, test=True):
    if fileprefix==None:
        fileprefix="."
    hmff = file(os.path.join(fileprefix,hmf_filename))

    if ferrors==None:
        if Dan_test:
            ferrors = file('/Users/d_yasaki/repos/lmfdb/lmfdb/scripts/hmf/fixing-permuted-primes/import_data.err', 'a')
        else:
            ferrors = file('/home/jvoight/lmfdb/backups/import_data.err', 'a')

    # Parse field data
    v = hmff.readline()
    assert v[:9] == 'COEFFS :='
    coeffs = eval(v[10:][:-2])
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
    if Dan_test:
        assert F_hmf is not None  # Assuming the hmf field is already there!
    if F_hmf is None:
        # Create list of ideals
        print "...adding!"
        ideals = eval(preparse(magma.eval('nice_idealstr(F);')))
        ideals_str = [str(c) for c in ideals]
        if test:
            print("Would now insert data for %s into hmf_fields" % field_label)
        else:
            hmf_fields.insert_one({"label": field_label,
                                   "degree": n,
                                   "discriminant": d,
                                   "ideals": ideals_str})
        F_hmf = hmf_fields.find_one({"label": field_label})
    else:
        print "...found!"

    print "Computing ideals..."
    ideals_str = F_hmf['ideals']
    ideals = [eval(preparse(c)) for c in ideals_str]
    ideals_norms = [c[0] for c in ideals]
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

    primes_indices = eval(magma.eval('primes_indices'))
    primes_str = [ideals_str[j - 1] for j in primes_indices]
    assert len(primes_array) == len(primes_str)
    print "...comparing..."
    for i in range(len(primes_array)):
        assert magma('ideal<ZF | {F!x : x in ' + primes_array[i] + '}> eq '
                     + 'ideal<ZF | {F!x : x in ' + primes_str[i] + '}>;')
    if resort:
        # Important also to resort the list of primes themselves!
        # not just the a_pp's
        primes_str = [primes_str[i] for i in primes_resort]
    if Dan_test:
        assert 'primes' in F_hmf  # DY:  want to make sure the fields are not touched!
    if 'primes' in F_hmf:  # Nothing smart: make sure it is the same
        assert F_hmf['primes'] == primes_str
    else:
        F_hmf['primes'] = primes_str
        if test:
            print("Would now save primes string %s... into hmf_fields" % primes_str[:100])
        else:
            hmf_fields.replace_one(F_hmf)
            print "...saved!"

    # Collect levels
    v = hmff.readline()
    if v[:9] == 'LEVELS :=':
        # Skip this line since we do not use the list of levels
        v = hmff.readline()
    for i in range(3):
        if v[:11] != 'NEWFORMS :=':
            v = hmff.readline()
        else:
            break

    # Finally, newforms!
    print "Starting newforms!"
    while v != '':
        v = hmff.readline()[1:-3]
        if len(v) == 0:
            break
        data = eval(preparse(v))
        level_ideal = data[0]
        level_norm = data[0][0]
        label_suffix = fix_one_label(data[1])
        weight = [2 for i in range(n)]
        label_nsuffix = class_to_int(label_suffix)

        level_ind = int(magma('Index(ideals, ideal<ZF | {F!x : x in ' + str(level_ideal) + '}>)')
                        ) - 1  # Magma counts starting at 1
        level_ideal = ideals_str[level_ind]
        assert magma('ideal<ZF | {F!x : x in ' + str(level_ideal) + '}> eq '
                     + 'ideal<ZF | {F!x : x in ' + str(data[0]) + '}>;')
        level_dotlabel = level_ind - ideals_norms.index(level_norm) + 1   # Start counting at 1
        assert level_dotlabel > 0
        level_label = str(level_norm) + '.' + str(level_dotlabel)

        label = construct_full_label(field_label, weight, level_label, label_suffix)
        short_label = level_label + '-' + label_suffix

        if len(data) == 3:
            hecke_polynomial = x
            hecke_eigenvalues = data[2]
        else:
            hecke_polynomial = data[2]
            hecke_eigenvalues = data[3]

        if resort:
            hecke_eigenvalues = [hecke_eigenvalues[i] for i in primes_resort]

        # Constrain eigenvalues to size 2MB
        hecke_eigenvalues = [str(c) for c in hecke_eigenvalues]
        leftout = 0
        while sum([len(s) for s in hecke_eigenvalues]) > 2000000:
            hecke_eigenvalues = hecke_eigenvalues[:-1]
            leftout += 1
            # commented code below throws an error.  use above.
            # just be safe and remove one eigenvalue at a time.
            # Aurel's code will adjust and remove extra when needed.
            #q = primes_resort[len(hecke_eigenvalues)]
            #while primes_resort[len(hecke_eigenvalues)] == q:
            #    # Remove all with same norm 
            #    leftout += 1
            #    hecke_eigenvalues = hecke_eigenvalues[:-1]
            
        if leftout > 0:
            print "Left out", leftout

        info = {"label": label,
                "short_label": short_label,
                "field_label": field_label,
                "level_norm": int(level_norm),
                "level_ideal": str(level_ideal),
                "level_label": level_label,
                "weight": str(weight),
                "label_suffix": label_suffix,
                "label_nsuffix" : label_nsuffix,
                "dimension": hecke_polynomial.degree(),
                "hecke_polynomial": str(hecke_polynomial),
                "hecke_eigenvalues": hecke_eigenvalues}  # DY: don't deal with AL right now.
                #,
                #"AL_eigenvalues": [[str(a[0]), str(a[1])] for a in AL_eigenvalues]}
        print info['label']

        existing_forms = hmf_forms.find({"label": label})
        assert existing_forms.count() <= 1
        if existing_forms.count() == 0:
            if test:
                print("Would now insert form data %s into hmf_forms" % info)
            else:
                hmf_forms.insert_one(info)
        else:
            existing_form = existing_forms.next()
            assert info['hecke_polynomial'] == existing_form['hecke_polynomial']
            try:
                assert info['hecke_eigenvalues'] == existing_form['hecke_eigenvalues']
                print "...duplicate"
            except AssertionError:
                print "...Hecke eigenvalues do not match!  Checking for permutation"
                assert set(info['hecke_eigenvalues'] + ['0','1','-1']) == set(existing_form['hecke_eigenvalues'] + [u'0',u'1',u'-1'])
                # Add 0,1,-1 to allow for Atkin-Lehner eigenvalues, if not computed
                print "As sets, ignoring 0,1,-1, the eigenvalues match!"
                if test:
                    print("Would now replace permuted form data %s with %s" % (existing_form, info))
                else:
                    existing_form['hecke_eigenvalues'] = info['hecke_eigenvalues']
                    hmf_forms.save(existing_form)


def repair_fields(D):
    F = hmf_fields.find_one({"label": '2.2.' + str(D) + '.1'})

    P = PolynomialRing(QQ, 'w')
    # P is used implicitly in the eval() calls below.  When these are
    # removed, this will not longer be neceesary, but until then the
    # assert statement is for pyflakes.
    assert P

    primes = F['primes']
    primes = [[int(eval(p)[0]), int(eval(p)[1]), str(eval(p)[2])] for p in primes]
    F['primes'] = primes

    hmff = file("data_2_" + (4 - len(str(D))) * '0' + str(D))

    # Parse field data
    for i in range(7):
        v = hmff.readline()
    ideals = eval(v[10:][:-2])
    ideals = [[p[0], p[1], str(p[2])] for p in ideals]
    F['ideals'] = ideals
    hmf_fields.save(F)


def repair_fields_add_ideal_labels(D):
    F = hmf_fields.find_one({"label": '2.2.' + str(D) + '.1'})

    ideals = F['ideals']
    ideal_labels = ['1.1']
    N = 1
    cnt = 1
    for I in ideals[2:]:
        NI = I[0]
        if NI == N:
            cnt += 1
        else:
            cnt = 1
        N = NI
        ideal_labels.append(str(NI) + '.' + str(cnt))
    F['ideal_labels'] = ideal_labels
    hmf_fields.save(F)


def attach_new_label(f):
    print f['label']
    F = hmf_fields.find_one({"label": f['field_label']})

    P = PolynomialRing(QQ, 'w')
    # P is used implicitly in the eval() calls below.  When these are
    # removed, this will not longer be neceesary, but until then the
    # assert statement is for pyflakes.
    assert P

    if type(f['level_ideal']) == str or type(f['level_ideal']) == unicode:
        N = eval(f['level_ideal'])
    else:
        N = f['level_ideal']
    if type(N) != list or len(N) != 3:
        print f, N, type(N)
        assert False

    f['level_ideal'] = [N[0], N[1], str(N[2])]

    try:
        ideal_label = F['ideal_labels'][F['ideals'].index(f['level_ideal'])]
        f['level_ideal_label'] = ideal_label
        f['label'] = construct_full_label(f['field_label'], f['weight'], f['level_ideal_label'], f['label_suffix'])
        hmf_forms.save(f)
        print f['label']
    except ValueError:
        hmf_forms.remove(f)
        print "REMOVED!"






## ========= COPIED from import_hmf_extra_gnu_phase_0.py on 7-18-2017

def parseALstring(s):
    # Drop first char bracket
    #in [[4,2,1/2*w^3-2*w],-1],[[191,191,-w^3-2*w^2+5*w+7],-1]] 
    #out ['[[4', '2', '1/2*w^3-2*w]', '-1]', '[[191', '191', '-w^3-2*w^2+5*w+7]', '-1]]']
    if s == '[]':
        return []
    s = s[1:-1]
    sm = s.split(',')
    outlist = []
    #print s, sm
    assert len(sm) % 4 == 0
    for i in range(len(sm)/4):
        outlist += [[sm[4*i][1:]+","+sm[4*i+1]+","+sm[4*i+2], sm[4*i+3][:-1]]]
    return outlist


def import_extra_data(hmf_extra_filename, fileprefix=None, ferrors=None, test=True):
    ''' 
    put in docstring!
    '''
    if ferrors==None:
        if Dan_test:
            ferrors = file('/Users/d_yasaki/repos/lmfdb/lmfdb/scripts/hmf/fixing-permuted-primes/import_extra.err', 'a')
        else:
            ferrors = file('/home/jvoight/lmfdb/backups/import_data.err', 'a')
    field_label = hmf_extra_filename.split('-')[0]
    if fileprefix==None:
        fileprefix="."
    hmff = file(os.path.join(fileprefix,hmf_extra_filename))

    with hmff as infile:
        # assumes the input filename starts with the field label.
        F = hmf_fields.find_one({'label':field_label})
        assert F is not None
        clean_primes = [p.replace(' ','') for p in F['primes']]

        print clean_primes

        for line in infile:
            # sample line - 4.4.1600.1-25.1-a:[25,5,w^2-3]:no:yes:[[[25,5,w^2-3],1]]:done:[[25,5,w^2-3],-1]
            line_keys = ['label', 'level_ideal','is_CM','is_base_change','AL_eigenvalues','AL_eigenvalues_fixed'] 
            data = line.split(':')
            label = data[0]
            f = hmf_forms.find_one({'label':label})
            if f is None:
                continue
            assert f['field_label'] == field_label
            f['AL_eigenvalues'] = parseALstring(data[line_keys.index('AL_eigenvalues')])
            enter_keys = ['is_CM','is_base_change','AL_eigenvalues_fixed']
            for k in enter_keys:  
                f[k] = data[line_keys.index(k)]
            # need to fix some aps:  data[-1]
            # adjust f['hecke_eigenvalues']
            if len(data) > 6:
                # there are ap to fix
                for apfix in data[6:]:
                    pp = apfix.rstrip()[1:-1].split('],')[0] + ']'
                    ap = apfix.rstrip()[1:-1].split('],')[1]
                    if not ap in {'1','-1'}:
                        print '?????   ',ap,label
                    assert ap in {'1','-1'}
                    if clean_primes.index(pp) < len(f['hecke_eigenvalues']):
                        try: 
                            assert f['hecke_eigenvalues'][clean_primes.index(pp)] in {'0','1','-1'}
                        except AssertionError:
                            print f['hecke_eigenvalues'][clean_primes.index(pp)]
                            print f
                            assert False
                        f['hecke_eigenvalues'][clean_primes.index(pp)] = ap
                    else:
                        print '!!! a_pp not corrected since not many stored !!!'
            if not test:
                print label
                hmf_forms.save(f)  
            else:
                print f



