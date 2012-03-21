# -*- coding: utf-8 -*-
import os.path, gzip, re, sys, time
from pymongo import Connection

hmf_forms = Connection(port=int(37010)).hmfs.forms
hmf_fields = Connection(port=int(37010)).hmfs.fields

fields = Connection(port=int(37010)).numberfields.fields

hmf_forms.create_index('field_label')
hmf_forms.create_index('level_norm')
hmf_forms.create_index('level_ideal')
hmf_forms.create_index('dimension')

def parse_label(field_label, weight, level_ideal_label, label_suffix):
    return field_label + '-' + str(weight) + '-' + level_ideal_label + '-' + label_suffix

def import_data(hmf_filename):
    hmff = file(hmf_filename)

    # Parse field data
    v = hmff.readline()
    coeffs = eval(v[10:][:-2])
    v = hmff.readline()
    n = int(v[4:][:-2])
    v = hmff.readline()
    d = int(v[4:][:-2])

    # Find the corresponding field in the database of number fields
    fields_matching = fields.find({"signature" : [n,int(0)], 
                                   "discriminant" : d})
    cnt = fields_matching.count()
    assert cnt >= 1
    field_label = None
    for i in range(cnt):
        nf = fields_matching.next()
        if nf['coefficients'] == coeffs:
            field_label = nf['label']
    assert field_label <> None

    # Find the field in the HMF database
    F_hmf = hmf_fields.find_one({"label" : field_label})
    if F_hmf == None:
        hmf_fields.insert({"label" : field_label,
                           "degree" : n,
                           "discriminant" : d})
        F_hmf = hmf_fields.find_one({"label" : field_label})
    
    # Add the list of primes
    v = hmff.readline()  # Skip line
    primes_str = hmff.readline()[10:][:-2]
    P = PolynomialRing(Rationals(), 3, ['w','e','x'])
    w,e,x = P.gens()
    primes_array = [str(t) for t in eval(primes_str)]
    if F_hmf.has_key('primes'): # Nothing smart: make sure it is the same
        if len(F_hmf['primes']) <= len(primes_array):
            assert F_hmf['primes'] == primes_array[:len(F_hmf['primes'])]
        else:
            assert primes_array == F_hmf.primes[:len(primes_array)]
    else:
        F_hmf['primes'] = primes_array
    hmf_fields.save(F_hmf)

    # Collect levels
    v = hmff.readline()  # Skip line
    levels_str = hmff.readline()[10:][:-2]
    levels_array = [str(t) for t in eval(levels_str)]

    # Finally, newforms!   
    v = hmff.readline()  # Skip line
    v = hmff.readline() 
    v = hmff.readline() 
    while v <> '':
        v = hmff.readline()[1:][:-3]
        v = v.replace('^', '**')
        data = eval(v)
        level_ideal = data[0]
        level_norm = data[0][0]
        label_suffix = data[1]
        weight = [2 for i in range(n)]
        label = parse_label(field_label, weight, level_ideal, label_suffix)
        if len(data) == 3:
            hecke_polynomial = x
            hecke_eigenvalues = data[2]
        else:
            hecke_polynomial = data[2]
            hecke_eigenvalues = data[3]
        info = {"label" : label,
                "field_label" : field_label,
                "level_norm" : int(level_norm),
                "level_ideal" : str(level_ideal),
                "weight" : weight,
                "label_suffix" : label_suffix,
                "dimension" : int(hecke_polynomial.degree()),
                "hecke_polynomial" : str(hecke_polynomial),
                "hecke_eigenvalues" : str(hecke_eigenvalues)}
        print info['label']

        existing_forms = hmf_forms.find({"label" : label})
        assert existing_forms.count() <= 1
        if existing_forms.count() == 0:
            hmf_forms.insert(info)
        else:
            existing_form = existing_forms.next()
            assert info['hecke_eigenvalues'] == existing_form['hecke_eigenvalues']

#def parse_label_old(field_label, weight, level_ideal, label_suffix):
#    label_str = field_label + str(weight) + str(level_ideal) + label_suffix
#    label_str = label_str.replace(' ', '')
#    return label_str

def repair_fields(D):
    F = hmf_fields.find_one({"label" : '2.2.' + str(D) + '.1'})

    P = PolynomialRing(Rationals(), 'w')
    w = P.gens()[0]

    primes = F['primes']
    primes = [[int(eval(p)[0]), int(eval(p)[1]), str(eval(p)[2])] for p in primes]
    F['primes'] = primes
    
    hmff = file("data_2_" + (4-len(str(D)))*'0' + str(D))

    # Parse field data
    for i in range(7):
        v = hmff.readline()
    ideals = eval(v[10:][:-2])
    ideals = [[p[0],p[1],str(p[2])] for p in ideals]
    F['ideals'] = ideals
    hmf_fields.save(F)

def repair_fields_add_ideal_labels(D):
    F = hmf_fields.find_one({"label" : '2.2.' + str(D) + '.1'})

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
    F = hmf_fields.find_one({"label" : f['field_label']})

    P = PolynomialRing(Rationals(), 'w')
    w = P.gens()[0]

    N = eval(f['level_ideal'])
    f['level_ideal'] = [N[0], N[1], str(N[2])]
    ideal_label = F['ideal_labels'][F['ideals'].index(f['level_ideal'])]
    f['level_ideal_label'] = ideal_label

    f['label'] =  parse_label(f['field_label'], f['weight'], ideal_label, f['label_suffix'])
    print f['label']
    hmf_forms.save(f)
