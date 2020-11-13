#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
r""" 
   Dump existing label information
   If a degree is given, just do that degree
"""

import sys, os

HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))

from lmfdb import db

fields = db.nf_fields

saving = True 

count = 0
#t = time.time()
first = 0
deg=0

dlist = range(1,48)
if(len(sys.argv)>1):
  dlist = [int(i) for i in sys.argv[1:]]

for deg in dlist:
    fn = "label-data-%d"%(deg)
    info = {}
    cur = fields.search({'degree': deg}, info=info)
    if info['number']>0:
        outf=open(fn, 'w')
        for f in cur:
            pol = f['coeffs']
            pol = str(pol)
            pol = pol.replace("L","")
            disc = f['disc_abs']
            n = int(f['degree'])
            sig = n-2*f['r2'] 
            outf.write("[%s,%s,%d,%d]\n"%(pol,n,disc,sig))
        outf.close()

