#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
r""" Import mod l Galois representations

  This deals with determinants and the power of the cyclotomic
  character itself.

"""


import re
import json
import os
import sys
import gzip

HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))

from lmfdb import db

reps = db.modlgal_reps


from sage.all import prime_range, DirichletGroup, ZZ, GF, Matrix, discrete_log, primitive_root

def get_det(ent):
  c = ent['conductor']
  frobs = ent['frobenius_matrices']
  ell = ent['base_ring_characteristic']
  plist = [z for z in prime_range(100) if not ZZ(z).divides(ell*c)]
  n = ent['dimension']
  F = GF(ell)
  primroot = primitive_root(ell)
  dets = [Matrix(F,n,z).det() for z in frobs]
  DG=DirichletGroup(c*ell, F, zeta=primroot)
  clistall = [z for z in DG if z.order().divides(ell-1)]
  #clistall1 = [[z(p) for p in plist] for z in clistall]
  clist = [z for z in clistall if [F(z(p)) for p in plist]==dets]
  try:
    assert len(clist)==1
  except:
    print(ent['label'])

  mychar = clist[0].primitive_character()
  newmod = mychar.modulus()
  N1 = ZZ(newmod/ell**newmod.valuation(ell))
  connum = max(mychar.conrey_number(), 1)
  l1 = rf"{ell}.1.{N1}.{newmod}-{connum}"
  modell = discrete_log(F(connum), F(primroot), ell-1) if ZZ(ell).divides(newmod) else 0
  return [l1, modell]


def last_label(base_label, n):
    return ".".join([str(base_label),str(n)])

## Main importing function

label_dict = {}
outrecs = []

for a in reps.search():
  lab = a['label']
  parts = lab.split('.')
  baselabel = '.'.join(parts[0:-1])
  if not '-' in parts[-1]:
      num = int(parts[-1])
      newset = label_dict.get(baselabel,set([]))
      label_dict[baselabel] = newset.union({num})

def label_lookup(base_label):
    global label_dict
    n=1
    s = label_dict.get(base_label, set([]))
    while n in s:
        n += 1
    s.add(n)
    label_dict[base_label] = s
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
        'top_slope_rational', 'top_slope_real', 'generating_primes', 'frobenius_matrices',
        'image_abstract_group', 'projective_image_abstract_group']
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
    [detlabel, charpower] = get_det(data)
    data['determinant_label'] = detlabel
    data['cyclotomic_exponent'] = charpower

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

