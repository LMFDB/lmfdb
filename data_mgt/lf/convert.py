#!/usr/bin/env python
# -*- coding: utf-8 -*-
# the purpose of this demo is to read in the yaml file
# and produce the protobuf output.

import os, sys
os.chdir(os.path.abspath(os.path.dirname(__file__)))

import yaml
import lf_pb2 as lf

fn = sys.argv[1]
fn_new = os.path.splitext(fn)[0] + ".pb2"

data = yaml.load(file(fn))
#print data

# create the new protobuf object
data_pb = lf.LFunction()

for field in ['logsign', 'arithmetic', 'self_dual', 'primitive',
              'degree', 'level', 'character_mod', 'character_nr', 'Gamma_factor_precision']:
    d = data[field]
    print "%s => %s" % (field, d)
    setattr(data_pb, field, d)

for field in ['character', 'signature', 'real_shiftsR', 'real_shiftsC', 'imaginary_shiftsR', 'imaginary_shiftsC']:
    # .append if just one value
    d = data[field]
    print "%s => %s" % (field, d)
    getattr(data_pb, field).extend(d)

cdeci = data_pb.coefficients_decimal
cdeci.precision = data['coefficients_decimal']['precision']
cdeci.coefficients.extend(data['coefficients_decimal']['coefficients'])

with open(fn_new, 'wb') as f:
    f.write(data_pb.SerializeToString())

print('successfully converted %(fn)s to %(fn_new)s.' % locals())
