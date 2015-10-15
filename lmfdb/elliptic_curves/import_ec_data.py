# -*- coding: utf-8 -*-
r""" Import data from Cremona tables.  Note: This code can be run on
all files in any order. Even if you rerun this code on previously
entered files, it should have no affect.  This code checks if the
entry exists, if so returns that and updates with new information. If
the entry does not exist then it creates it and returns that.

Initial version (Paris 2010)
More tables Feb 2011 Gagan Sekhon
Needed importing code for Stein-Watkins

Rewritten by John Cremona and David Roe, Bristol, March 2012

The documents in the collection 'curves' in the database 'elliptic_curves' have the following fields:

   - '_id': internal mogodb identifier
   - 'label':  (string) full Cremona label, e.g. '1225a2'
   - 'lmfdb_label':  (string) full LMFDB label, e.g. '1225.a2'
   - 'conductor': (int) conductor, e.g. 1225
   - 'iso': (string) Cremona isogeny class code, e.g. '11a'
   - 'lmfdb_iso': (string) LMFDB isogeny class code, e.g. '11.a'
   - 'number': (int) Cremona curve number within its class, e.g. 2
   - 'lmfdb_number': (int) LMFDB curve number within its class, e.g. 2
   - 'ainvs': (list of strings) list of a-invariants, e.g. ['0', '1', '1', '10617', '75394']
   - 'jinv': (string) j-invariant, e.g. -4096/11
   - 'cm': (int) 0 for no CM, or a negative discriminant
   - 'rank': (int) rank, e.g. 0
   - 'torsion': (int) torsion order, e.g. 1
   - 'torsion_structure': (list of strings) list of invariants of torsion subgroup, e.g. ['3']
   - 'torsion_generators': (list of strings) list of generators of torsion subgroup, e.g. ['(5, 5)']
   - 'x-coordinates_of_integral_points': (string) list of x-coordinates of integral points, e.g. '[5,16]'
   - 'gens': (list of strings) list of generators of infinite order, e.g. ['(0:0:1)']
   - 'regulator': (float) regulator, e.g. 1.0
   - 'tamagawa_product': (int) product of Tamagawa numbers, e.g. 4
   - 'special_value': (float) special value of r'th derivative of L-function (divided by r!), e.g.1.490882041449698
   - 'real_period': (float) real period, e.g. 0.3727205103624245
   - 'degree': (int) degree of modular parametrization, e.g. 1984
   - 'non-surjective_primes': (list of ints) primes p for which the
      mod p Galois representation is not surjective, e.g. [5]
   - 'galois_images': (list of strings) Sutherland codes for the
      images of the mod p Galois representations for the primes in
      'non-surjective_primes' e.g. ['5B']
   - '2adic_index': (int) the index of the 2-adic representation in
      GL(2,Z2) (or 0 for CM curves, which have infinite index)
   - '2adic_log_level': (int) the smallest n such that the image
      contains the kernel of reduction modulo 2^n (or None for CM curves)
   - '2adic_gens': (list of lists of 4 ints) list of entries [a,b,c,d]
      of matrices in GL(2,Z/2^nZ) generating the image where n is the
      log_level (None for CM curves)
   - '2adic_label': (string) Rouse label of the associated modular
      curve (None for CM curves)
   - 'isogeny_matrix': (list of lists of ints) isogeny matrix for
     curves in the class
   - 'sha_an': (float) analytic order of sha (approximate unless r=0)
   - 'sha': (int) analytic order of sha (rounded value of sha_an)
   - 'sha_primes': (list of ints) primes dividing sha
   - 'torsion_primes': (list of ints) primes dividing torsion
"""

import os.path
import gzip
import re
import sys
import time
import os
import random
import glob
import pymongo
from lmfdb import base
from lmfdb.website import dbport
from sage.rings.all import ZZ

print "calling base._init()"
dbport=37010
base._init(dbport, '')
print "getting connection"
conn = base.getDBConnection()
print "setting curves"
# curves = conn.elliptic_curves.test
curves = conn.elliptic_curves.curves

# The following ensure_index command checks if there is an index on
# label, conductor, rank and torsion. If there is no index it creates
# one.  Need: once torsion structure is computed, we should have an
# index on that too.

curves.ensure_index('label')
curves.ensure_index('conductor')
curves.ensure_index('rank')
curves.ensure_index('torsion')
curves.ensure_index('degree')
curves.ensure_index('jinv')
curves.ensure_index('sha')
curves.ensure_index('cm')

print "finished indices"


def parse_tgens(s):
    r"""
    Converts projective coordinates to affine coordinates for generator
    """
    g1 = s.replace('(', ' ').replace(')', ' ').split(':')
    x, y, z = [ZZ(c) for c in g1]
    g = (x / z, y / z)
    return str(g)


def parse_ainvs(s):
    r"""
    Given a string like '[a1,a2,a3,a4,a6]' returns the list of substrings ['a1','a2','a3','a4','a6']
    """
#    return [int(a) for a in s[1:-1].split(',')]
    return [a for a in s[1:-1].split(',')]


# def parse_gens(s):
 #   return [int(a) for a in s[1:-1].split(':')]

whitespace = re.compile(r'\s+')


def split(line):
    return whitespace.split(line.strip())


def allbsd(line):
    r""" Parses one line from an allbsd file.  Returns the label and a
    dict containing fields with keys 'conductor', 'iso', 'number',
    'ainvs', 'rank', 'torsion', 'torsion_primes', 'tamagawa_product',
    'real_period', 'special_value', 'regulator', 'sha_an', 'sha',
    'sha_primes', all values being strings or floats or ints or lists
    of ints.

    Input line fields:

    conductor iso number ainvs rank torsion tamagawa_product real_period special_value regulator sha_an

    Sample input line:

    11 a 1 [0,-1,1,-10,-20] 0 5 5 1.2692093042795534217 0.25384186085591068434 1 1.00000000000000000000

    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    ainvs = parse_ainvs(data[3])

    torsion = ZZ(data[5])
    sha_an = RR(data[10])
    sha = sha_an.round()
    sha_primes = sha.prime_divisors()
    torsion_primes = torsion.prime_divisors()

    data = {
        'conductor': int(data[0]),
        'iso': data[0] + data[1],
        'number': int(data[2]),
        'ainvs': ainvs,
        'rank': int(data[4]),
        'tamagawa_product': int(data[6]),
        'real_period': float(data[7]),
        'special_value': float(data[8]),
        'regulator': float(data[9]),
        'sha_an': float(sha_an),
        'sha':  int(sha),
        'sha_primes':  [int(p) for p in sha_primes],
        'torsion':  int(torsion),
        'torsion_primes':  [int(p) for p in torsion_primes]
        }

    return label, data

# Next function redundant as all data in allcurves is also in allgens


def allcurves(line):
    r""" Parses one line from an allcurves file.  Returns the label and a
    dict containing fields with keys 'conductor', 'iso', 'number',
    'ainvs', 'jinv', 'cm', 'rank', 'torsion', all values being strings or ints.

    Input line fields:

    conductor iso number ainvs rank torsion

    Sample input line:

    11 a 1 [0,-1,1,-10,-20] 0 5
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    ainvs = parse_ainvs(data[3])
    E = EllipticCurve([ZZ(eval(a)) for a in ainvs])
    jinv = unicode(str(E.j_invariant()))
    if E.has_cm():
        cm = int(E.cm_discriminant())
    else:
        cm = int(0)

    return label, {
        'conductor': int(data[0]),
        'iso': data[0] + data[1],
        'number': int(data[2]),
        'ainvs': ainvs,
        'jinv': jinv,
        'cm': cm,
        'rank': int(data[4]),
        'torsion': int(data[5]),
    }


def allgens(line):
    r""" Parses one line from an allgens file.  Returns the label and
    a dict containing fields with keys 'conductor', 'iso', 'number',
    'ainvs', 'jinv', 'cm', 'rank', 'gens', 'torsion_order', 'torsion_structure',
    'torsion_generators', all values being strings or ints.

    Input line fields:

    conductor iso number ainvs rank torsion_structure gens torsion_gens

    Sample input line:

    20202 i 2 [1,0,0,-298389,54947169] 1 [2,4] [-570:6603:1] [-622:311:1] [834:19239:1]
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    rank = int(data[4])
    t = eval(data[5])
    torsion = int(prod([ti for ti in t], 1))
    ainvs = parse_ainvs(data[3])
    E = EllipticCurve([ZZ(eval(a)) for a in ainvs])
    jinv = unicode(str(E.j_invariant()))
    if E.has_cm():
        cm = int(E.cm_discriminant())
    else:
        cm = int(0)

    return label, {
        'conductor': int(data[0]),
        'iso': data[0] + data[1],
        'number': int(data[2]),
        'ainvs': ainvs,
        'jinv': jinv,
        'cm': cm,
        'rank': int(data[4]),
        'gens': ["(%s)" % gen[1:-1] for gen in data[6:6 + rank]],
        'torsion': torsion,
        'torsion_structure': ["%s" % tor for tor in t],
        'torsion_generators': ["%s" % parse_tgens(tgens[1:-1]) for tgens in data[6 + rank:]],
    }

def twoadic(line):
    r""" Parses one line from a 2adic file.  Returns the label and a dict
    containing fields with keys '2adic_index', '2adic_log_level',
    '2adic_gens' and '2adic_label'.

    Input line fields:

    conductor iso number ainvs index level gens label

    Sample input lines:

    110005 a 2 [1,-1,1,-185793,29503856] 12 4 [[3,0,0,1],[3,2,2,3],[3,0,0,3]] X24
    27 a 1 [0,0,1,0,-7] inf inf [] CM
    """
    data = split(line)
    assert len(data)==8
    label = data[0] + data[1] + data[2]
    model = data[7]
    if model == 'CM':
        return label, {
            '2adic_index': int(0),
            '2adic_log_level': None,
            '2adic_gens': None,
            '2adic_label': None,
        }

    index = int(data[4])
    level = ZZ(data[5])
    log_level = int(level.valuation(2))
    assert 2**log_level==level
    if data[6]=='[]':
        gens=[]
    else:
        gens = data[6][1:-1].replace('],[','];[').split(';')
        gens = [[int(c) for c in g[1:-1].split(',')] for g in gens]

    return label, {
            '2adic_index': index,
            '2adic_log_level': log_level,
            '2adic_gens': gens,
            '2adic_label': model,
    }


def intpts(line):
    r""" Parses one line from an intpts file.  Returns the label and a
    dict containing fields with keys 'ainvs',
    'x-coordinates_of_integral_points', all values being strings.

    Input line fields:

    label ainvs x-coordinates_of_integral_points

    Sample input line:

    11a1 [0,-1,1,-10,-20] [5,16]
    """
    data = split(line)
    label = data[0]
    ainvs = parse_ainvs(data[1])
    return label, {
        'ainvs': ainvs,
        'x-coordinates_of_integral_points': data[2]
    }


def alldegphi(line):
    r""" Parses one line from an alldegphi file.  Returns the label
    and a dict containing one field with key 'degree', all values
    being strings or ints.

    Input line fields:

    conductor iso number ainvs degree

    Sample input line:

    11 a 1 [0,-1,1,-10,-20] 1
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'degree': int(data[4])
    }


def alllabels(line):
    r""" Parses one line from an alllabels file.  Returns the label
    and a dict containing six fields, 'conductor', 'iso', 'number',
    'lmfdb_label', 'lmfdb_iso', 'lmfdb_number', being strings or ints.

    Input line fields:

    conductor iso number conductor lmfdb_iso lmfdb_number

    Sample input line:

    57 c 2 57 b 1

    """
    data = split(line)
    if data[0] != data[3]:
        raise ValueError("Inconsistent data in alllabels file: %s" % line)
    label = data[0] + data[1] + data[2]
    lmfdb_label = data[3] + '.' + data[4] + data[5]
    return label, {
        'conductor': int(data[0]),
        'iso': data[0] + data[1],
        'number': int(data[2]),
        'lmfdb_label': lmfdb_label,
        'lmfdb_iso': data[3] + '.' + data[4],
        'lmfdb_number': data[5]
    }

def galrep(line):
    r""" Parses one line from a galrep file.  Returns the label and a
    dict containing two fields: 'non-surjective_primes', a list of
    primes p for which the Galois representation modulo p is not
    surjective (cut off at p=37 for CM curves for which this would
    otherwise contain all primes), 'galois_images', a list of strings
    encoding the image when not surjective, following Sutherland's
    coding scheme for subgroups of GL(2,p).  Note that these codes
    start with a 1 or 2 digit prime followed a letter in
    ['B','C','N','S'].

    Input line fields:

    conductor iso number ainvs rank torsion codes

    Sample input line:

    66 c 3 [1,0,0,-10065,-389499] 0 2 2B 5B.1.2

    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    image_codes = data[6:]
    pr = [ int(s[:2]) if s[1].isdigit() else int(s[:1]) for s in image_codes]
    return label, {
        'non-surjective_primes': pr,
        'galois_images': image_codes,
    }


filename_base_list = ['allcurves', 'allbsd', 'allgens', 'intpts', 'alldegphi', 'alllabel']


def cmp_label(lab1, lab2):
    from sage.databases.cremona import parse_cremona_label, class_to_int
#    print lab1,lab2
    a, b, c = parse_cremona_label(lab1)
    id1 = int(a), class_to_int(b), int(c)
    a, b, c = parse_cremona_label(lab2)
    id2 = int(a), class_to_int(b), int(c)
    return cmp(id1, id2)


def comp_dict_by_label(d1, d2):
    return cmp_label(d1['label'], d2['label'])

# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile lmfdb/elliptic_curves/import_ec_data.py
#

def upload_to_db(base_path, min_N, max_N):
    allbsd_filename = 'allbsd/allbsd.%s-%s' % (min_N, max_N)
    allgens_filename = 'allgens/allgens.%s-%s' % (min_N, max_N)
    intpts_filename = 'intpts/intpts.%s-%s' % (min_N, max_N)
    alldegphi_filename = 'alldegphi/alldegphi.%s-%s' % (min_N, max_N)
    alllabels_filename = 'alllabels/alllabels.%s-%s' % (min_N, max_N)
    galreps_filename = 'galrep/galrep.%s-%s' % (min_N, max_N)
    twoadic_filename = '2adic/2adic.%s-%s' % (min_N, max_N)
    file_list = [allbsd_filename, allgens_filename, intpts_filename, alldegphi_filename, alllabels_filename, galreps_filename,twoadic_filename]
#    file_list = [twoadic_filename]

    parsing_dict = {}
    for f in file_list:
        prefix = f[f.find('/')+1:f.find('.')]
        if prefix == '2adic':
            parsing_dict[f] = twoadic
        else:
            parsing_dict[f] = globals()[prefix]


    data_to_insert = {}  # will hold all the data to be inserted

    for f in file_list:
        h = open(os.path.join(base_path, f))
        print "opened %s" % os.path.join(base_path, f)

        parse=parsing_dict[f]
        t = time.time()
        count = 0
        for line in h.readlines():
            label, data = parse(line)
            if count%5000==0:
                print "read %s" % label
            count += 1
            if label not in data_to_insert:
                data_to_insert[label] = {'label': label}
            curve = data_to_insert[label]
            for key in data:
                if key in curve:
                    if curve[key] != data[key]:
                        raise RuntimeError("Inconsistent data for %s" % label)
                else:
                    curve[key] = data[key]
        print "finished reading %s lines from file" % count

    vals = data_to_insert.values()
    # vals.sort(cmp=comp_dict_by_label)
    count = 0
    for val in vals:
        # print val
        curves.update({'label': val['label']}, {"$set": val}, upsert=True)
        count += 1
        if count % 5000 == 0:
            print "inserted %s" % (val['label'])


# A one-off script to add isogeny matrices to the database

def add_isogeny_matrices(N1,N2):
    """
    Add the 'isogeny_matrix' field to every curve in the database
    whose conductor is between N1 and N2 inclusive.  The matrix is
    stored as a list of n lists of n ints, where n is the size of the
    class and the (i,j) entry is the degree of a cyclic isogeny from
    curve i to curve j in the class, using the lmfdb numbering within
    each class.  Hence this matrix is exactly the same for all curves
    in the class.  This was added in July 2014 to save recomputing the
    complete isogeny class every time despite the fact that the curves
    in the class were already in the database.
    """
    query = {}
    query['conductor'] = { '$gt': int(N1)-1, '$lt': int(N2)+1 }
    query['lmfdb_number'] = int(1)
    res = curves.find(query)
    res = res.sort([('conductor', pymongo.ASCENDING),
                    ('lmfdb_iso', pymongo.ASCENDING)])
    for C in res:
        label = C['label']
        lmfdb_label = C['lmfdb_label']
        lmfdb_iso = C['lmfdb_iso']
        E = EllipticCurve([int(a) for a in C['ainvs']])
        M = E.isogeny_class(order="lmfdb").matrix()
        mat = [list([int(c) for c in r]) for r in M.rows()]
        n = len(mat)
        print "%s curves in class %s" % (n,lmfdb_iso)
        for label_i in [lmfdb_iso+str(i+1) for i in  range(n)]:
            data = {}
            data['lmfdb_label'] = label_i
            data['isogeny_matrix'] = mat
            curves.update({'lmfdb_label': label_i}, {"$set": data}, upsert=True)

# A one-off script to add (1) exact Sha order; (2) prime factors of Sha; (3) prime factors of torsion

def add_sha_tor_primes(N1,N2):
    """
    Add the 'sha', 'sha_primes', 'torsion_primes' fields to every
    curve in the database whose conductor is between N1 and N2
    inclusive.
    """
    query = {}
    query['conductor'] = { '$gte': int(N1), '$lte': int(N2) }
    res = curves.find(query)
    res = res.sort([('conductor', pymongo.ASCENDING)])
    n = 0
    for C in res:
        label = C['lmfdb_label']
        if n%1000==0: print label
        n += 1
        torsion = ZZ(C['torsion'])
        sha = RR(C['sha_an']).round()
        sha_primes = sha.prime_divisors()
        torsion_primes = torsion.prime_divisors()
        data = {}
        data['sha'] = int(sha)
        data['sha_primes'] = [int(p) for p in sha_primes]
        data['torsion_primes'] = [int(p) for p in torsion_primes]
        curves.update({'lmfdb_label': label}, {"$set": data}, upsert=True)
