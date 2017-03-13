# -*- coding: utf-8 -*-
r""" Import Iwasawa invariant data (as computed by Rob Pollack).

Initial version (Warwick December 2016)

In general "number" means an int or double or string representing a number (e.g. '1/2').

Additional data fields for each elliptic curve over Q

   - 'iwp0' (int) if nonzero, a prime p0 such that lambda=mu=0 for all good p>=p0
   - 'iwdata' (dict) keys: primes, including all bad multiplicative primes and all primes up to some bound
                     values: '?' if unknown
                             'a' if bad additive
                             [lambda,mu] (two ints) if good ordinary or bad multiplicative
                             [lambda+,lambda-,mu] (three ints) if good supersingular
                                              [Here mu=0 always (conjecturally) but stored to distinguish cases.]


"""
import os
from sage.all import ZZ, primes, sqrt, EllipticCurve

from lmfdb.base import getDBConnection
print "getting connection"
C= getDBConnection()
print "authenticating on the elliptic_curves database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['elliptic_curves'].authenticate(username, password)
print "setting curves"
curves = C.elliptic_curves.curves

def read_line(line, debug=0):
    r""" Parses one line from input file.  Returns and a dict containing
    fields with keys as above.

    Sample line: 11 a 1 0,-1,1,-10,-20 7 1,0 0,1,0 0,0 0,1 

    Fields: label (3 fields)
            a-invariants
            p0
            For each bad  prime:  'a'                if additive
                                  lambda,mu          if multiplicative (or 'o?' if unknown)
            For each good prime:  lambda,mu          if ordinary (or 'o?' if unknown)
                                  lambda+,lambda-,mu if supersingular (or 's?' if unknown)
    """
    data = {}
    if debug: print("Parsing input line {}".format(line[:-1]))
    fields = line.split()
    label = fields[0]+fields[1]+fields[2]
    data['label'] = label
    N = ZZ(fields[0])
    badp = N.support()
    nbadp = len(badp)
    ainvs = fields[3]
    p0 = int(fields[4])
    data['iwp0'] = p0
    if debug: print("p0={}".format(p0))

    iwdata = {}

    # read data for bad primes

    for p,pdat in zip(badp,fields[5:5+nbadp]):
        p = str(p)
        if debug>1: print("p={}, pdat={}".format(p,pdat))
        if pdat in ['o?','a']:
            iwdata[p]=pdat
        else:
            iwdata[p]=[int(x) for x in pdat.split(",")]

    # read data for all primes

    for p,pdat in zip(primes(1000),fields[5+nbadp:]):
        p = str(p)
        if debug>1: print("p={}, pdat={}".format(p,pdat))
        if pdat in ['s?','o?','a']:
            iwdata[p]=pdat
        else:
            iwdata[p]=[int(x) for x in pdat.split(",")]

    data['iwdata'] = iwdata
    if debug: print("label {}, data {}".format(label,data))
    return label, data

# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile lmfdb/elliptic_curves/import_iwasawa_data.py
#
# and then run the following function.
# Unless you set test=False it will not actually upload any data.

def upload_to_db(base_path, f, test=True):
    f = os.path.join(base_path, f)
    h = open(f)
    print "opened %s" % f

    data_to_insert = {}  # will hold all the data to be inserted
    count = 0

    for line in h.readlines():
        count += 1
        if count%1000==0:
            print "read %s lines" % count
        label, data = read_line(line,0)
        data_to_insert[label] = data

    print "finished reading %s lines from file" % count
    vals = data_to_insert.values()

    print("Number of records to insert = %s" % len(vals))
    count = 0

    if test:
        print("Not inserting any records as in test mode")
        print("First record is %s" % vals[0])
        return

    for val in vals:
        #print val
        count += 1
        if not test:
            curves.update_one({'label': val['label']}, {"$set": val}, upsert=True)
        if count % 1000 == 0:
            print("inserted %s items" % count)
