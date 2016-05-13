import os.path
import gzip
import re
import sys
import time
import sage.misc.preparser
import subprocess
from sage.interfaces.magma import magma

from lmfdb.website import DEFAULT_DB_PORT as dbport
from pymongo.mongo_client import MongoClient
C= MongoClient(port=dbport)
C['admin'].authenticate('lmfdb', 'lmfdb') # read-only

import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['hmfs'].authenticate(username, password)
hmf_forms = C.hmfs.forms
hmf_fields = C.hmfs.fields
fields = C.numberfields.fields

P = sage.rings.polynomial.polynomial_ring_constructor.PolynomialRing(sage.rings.rational_field.RationalField(), 3, ['w', 'e', 'x'])
w, e, x = P.gens()

def find_Galois_squarefull_forms():
    forms_labels = []
    for F in hmf_fields.find():
        Fcoeff = fields.find_one({'label' : F['label']})['coeffs']
        magma.eval('F<w> := NumberField(Polynomial([' + str(Fcoeff) + ']));')
        if magma('IsNormal(F) and Degree(F) mod 2 eq 1;'):
            magma.eval('ZF := Integers(F);')
            for f in hmf_forms.find({'field_label' : F['label']}):
                magma.eval('NN := ideal<ZF | SequenceToSet(' + f['level_ideal'] + ')>;');
                if magma('Min([2] cat [ff[2] : ff in Factorization(NN)]) ge 2;'):
                    forms_labels.append(f['label'])
                    print f['label']
    return forms_labels