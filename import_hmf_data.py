import os.path, gzip, re, sys, time
from pymongo import Connection

hmf_forms = Connection(port=int(37010)).hmfs.forms
hmf_fields = Connection(port=int(37010)).hmfs.fields

fields = Connection(port=int(37010)).numberfields.fields

hmf_forms.create_index('field_label')
hmf_forms.create_index('level_norm')
hmf_forms.create_index('level_ideal')
hmf_forms.create_index('dimension')

def parse_label(field_label, weight, level_ideal, label_suffix):
    label_str = field_label + str(weight) + str(level_ideal) + label_suffix
    label_str = label_str.replace(' ', '')
    return label_str

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
