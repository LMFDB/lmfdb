#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
r""" Import mod l modular forms.  

"""


import re
import json
import os
import sys
import gzip

HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))

from lmfdb import db

#import yaml

reps = db.modlgal_reps


def last_label(base_label, n):
    return ".".join([str(base_label),str(n)])

## Main importing function

label_dict = {}
outrecs = []

def label_lookup(base_label):
    global label_dict
    n = label_dict.get(base_label, 0)+1
    label_dict[base_label] = n
    return n

def do_import(ll):
    global outrecs
    mykeys = ['algebraic_group', 'bad_prime_list', 'base_ring_characteristic',
        'base_ring_is_field', 'base_ring_order', 'conductor',
        'conductor_primes', 'conductor_is_squarefree',
        'conductor_num_primes',
        'cyclotomic_exponent', 'determinant_label', 'dimension', 'good_prime_list',
        'image_index', 'image_label', 'image_order', 'image_type', 'is_absolutely_irreducible',
        'is_irreducible', 'is_solvable', 'is_surjective', 'kernel_polynomial',
        'label', 'projective_is_surjective', 'projective_kernel_polynomial', 'projective_type',
        'top_slope_rational', 'top_slope_real', 'generating_primes', 'frobenius_matrices']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
    data['num'] = label_lookup(data['label'])
    data['label'] = data['label']+"."+ str(data['num'])
    data['related_objects'] = []
    # dual_pair_of_algebras left as None
    # convert booleans
    for ky in ['base_ring_is_field', 'conductor_is_squarefree','is_absolutely_irreducible','is_irreducible', 'is_solvable', 'is_surjective', 'projective_is_surjective']:
        data[ky] = (data[ky]>0)
# we need still to organize this better with respect to tie breaks 

#    rep = reps.lucky({'label': data['label']})
    rep = None

    if rep is None:
        #print("new mod l Galois representation")
        outrecs.append(data)
    else:
        print("mod l Galois representation already in the database")
        # maybe put this back in later
        #rep.upsert({'label': label}, data)
    #if saving:
    #    reps.update({'label': label} , {"$set": rep}, upsert=True)



# Loop over files

for path in sys.argv[1:]:
    print(path)
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)

reps.insert_many(outrecs)

