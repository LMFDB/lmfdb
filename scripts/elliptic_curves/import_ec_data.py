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
   - 'iso_nlabel': (int) numerical version of the (lmfdb) isogeny class label
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
   - 'non-maximal_primes': (list of ints) primes p for which the
      mod p Galois representation is not maximal, e.g. [5]
   - 'mod-p_images': (list of strings) Sutherland codes for the
      images of the mod p Galois representations for the primes in
      'non-maximal_primes' e.g. ['5B']
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
     curves in the class w.r.t. Cremona ordering
   - 'isogeny_degrees': (list of ints) degrees of cyclic isogenies from this curve
   - 'class_size': (int) size of isogeny class
   - 'class_deg': (int) max (=lcm) of isogeny degrees in the class
   - 'sha': (int) analytic order of sha (rounded value of sha_an)
   - 'sha_primes': (list of ints) primes dividing sha
   - 'torsion_primes': (list of ints) primes dividing torsion

Extra data fields added May 2016 to avoid computation on the fly:
   - 'xainvs': (string) '[a1,a2,a3,a4,a6]' (will replace 'ainvs' in due course)
   - 'equation': (string)
   - 'local_data': (list of dicts, one per prime)
   - 'signD': (sign of discriminant) int (+1 or -1)
   - 'min_quad_twist': (dict) {label:string, disc: int} #NB Cremona label
   - 'heights': (list of floats) heights of generators
   - 'aplist': (list of ints) a_p for p<100
   - 'anlist': (list of ints) a_p for p<20
"""

import os.path
import re
import sys
import os
import pymongo
from sage.all import ZZ, RR, EllipticCurve, prod, Set
from lmfdb.utils import web_latex
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

def numerical_iso_label(lmfdb_iso):
    from scripts.ecnf.import_utils import numerify_iso_label
    return numerify_iso_label(lmfdb_iso.split('.')[1])

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
    t = data[5]
    if t=='[]':
        t = []
    else:
        t = [int(c) for c in t[1:-1].split(",")]
    torsion = int(prod([ti for ti in t], 1))
    ainvs = parse_ainvs(data[3])
    E = EllipticCurve([ZZ(a) for a in ainvs])
    jinv = unicode(str(E.j_invariant()))
    if E.has_cm():
        cm = int(E.cm_discriminant())
    else:
        cm = int(0)

    content = {
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
    extra_data = make_extra_data(label,content['number'],ainvs,content['gens'])
    content.update(extra_data)

    return label, content

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
    and a dict containing seven fields, 'conductor', 'iso', 'number',
    'lmfdb_label', 'lmfdb_iso', 'iso_nlabel', 'lmfdb_number', being strings or ints.

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
    lmfdb_iso = data[3] + '.' + data[4]
    iso_nlabel = numerical_iso_label(lmfdb_iso)
    return label, {
        'conductor': int(data[0]),
        'iso': data[0] + data[1],
        'number': int(data[2]),
        'lmfdb_label': lmfdb_label,
        'lmfdb_iso': lmfdb_iso,
        'iso_nlabel': iso_nlabel,
        'lmfdb_number': int(data[5])
    }

def split_galois_image_code(s):
    """Each code starts with a prime (1-3 digits but we allow for more)
    followed by an image code or that prime.  This function returns
    two substrings, the prefix number and the rest.
    """
    p = re.findall(r'\d+', s)[0]
    return p, s[len(p):]

def galrep(line, new_format=True):
    r""" Parses one line from a galrep file.  Returns the label and a
    dict containing two fields: 'non-maximal_primes', a list of
    primes p for which the Galois representation modulo p is not
    maximal, 'mod-p_images', a list of strings
    encoding the image when not maximal, following Sutherland's
    coding scheme for subgroups of GL(2,p).  Note that these codes
    start with a 1 or 2 digit prime followed a letter in
    ['B','C','N','S'].

    Input line fields (new_format=False):

    conductor iso number ainvs rank torsion codes

    Sample input line:

    66 c 3 [1,0,0,-10065,-389499] 0 2 2B 5B.1.2

    Input line fields (new_format=True):

    label codes

    Sample input line:

    66c3 2B 5B.1.2

    """
    data = split(line)
    if new_format:
        label = data[0]
        image_codes = data[1:]
    else:
        label = data[0] + data[1] + data[2]
        image_codes = data[6:]

    pr = [ int(split_galois_image_code(s)[0]) for s in image_codes]

    if new_format:
        d = {
            'non-maximal_primes': pr,
            'mod-p_images': image_codes,
        }
    else:
        d = {
            'non-surjective_primes': pr,
            'galois_images': image_codes,
        }

    return label, d

def allisog(line, lmfdb_order=True):
    r""" Parses one line from an allisog file.

    Note that unlike all the other input files this does not have one
    line per curve, but just one line per class.  Nevertheless,
    reading this one line must update the records for all curves in
    the class.  For this reason we do not process this file from
    within the usual upload_to_db() script, but separately.

    Returns the label and a dict containing two fields:
    'isogeny_matrix', a list of lists of integers representing the
    isogeny matrix for the associated isogeny class, and
    'isogeny_degrees_dict', a dict with keys the numbers (from 1) of
    the curves in the class and values lists of integers of the
    degrees of the cyclic isogenies from this curve.

    NB The matrices in the allisog files number the curves using
    Cremona labelling, not LMFDB labelling (these are different for
    smaller conductors).  By default we permute the rows and columns
    of the matrix here so that the resulting matrix is in LMFDB order
    for storing in the database and then displaying with no need for
    further permutation.  Set lmfdb_order=False to not do this.

    Note that the website shows the isogeny class w.r.t. LMFDB
    ordering, so if the matrices were stored in Cremona order they
    would have to be permuted before displaying.

    Input line fields:

    conductor iso number ainvs all_ainvs isogeny_matrix

    Sample input line:

    11 a 1 [0,-1,1,-10,-20] [[0,-1,1,-10,-20],[0,-1,1,-7820,-263580],[0,-1,1,0,0]] [[1,5,5],[5,1,25],[5,25,1]]

    """
    data = split(line)
    isomat = data[5]
    isomat = [[int(d) for d in row.split(",")] for row in isomat[2:-2].split("],[")]

    if lmfdb_order:
        curves = data[4] # string
        curves = [[ZZ(ai) for ai in c.split(",")] for c in curves[2:-2].split("],[")]
        perm = dict([[i,curves.index(c)] for i,c in enumerate(sorted(curves))])
        # that maps L to C (with offset by 1)
        ncurves = len(curves)
        isomat = [[isomat[perm[i]][perm[j]] for i in range(ncurves)] for j in range(ncurves)]

    # count the curves in the class
    isogeny_degrees = dict([[n+1,sorted(list(set(row)))] for n,row in enumerate(isomat)])

    return {'label': data[:3],
        'isogeny_matrix': isomat,
        'isogeny_degrees': isogeny_degrees,
    }


filename_base_list = ['allbsd', 'allgens', 'intpts', 'alldegphi', 'alllabel']


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

def upload_to_db(base_path, min_N, max_N, insert=True):
    r""" Uses insert_one() if insert=True, which is faster but will fail if
    the label is already in the database; otherwise uses update_one()
    with upsert=True
    """
    allbsd_filename = 'allbsd/allbsd.%s-%s' % (min_N, max_N)
    allgens_filename = 'allgens/allgens.%s-%s' % (min_N, max_N)
    intpts_filename = 'intpts/intpts.%s-%s' % (min_N, max_N)
    alldegphi_filename = 'alldegphi/alldegphi.%s-%s' % (min_N, max_N)
    alllabels_filename = 'alllabels/alllabels.%s-%s' % (min_N, max_N)
    galreps_filename = 'galrep/galrep.%s-%s' % (min_N, max_N)
    twoadic_filename = '2adic/2adic.%s-%s' % (min_N, max_N)
    allisog_filename = 'allisog/allisog.%s-%s' % (min_N, max_N)
    file_list = [allbsd_filename, allgens_filename, intpts_filename, alldegphi_filename, alllabels_filename, galreps_filename,twoadic_filename,allisog_filename]
#    file_list = [twoadic_filename]
#    file_list = [allgens_filename]

    parsing_dict = {}
    for f in file_list:
        prefix = f[f.find('/')+1:f.find('.')]
        if prefix == '2adic':
            parsing_dict[f] = twoadic
        else:
            parsing_dict[f] = globals()[prefix]


    data_to_insert = {}  # will hold all the data to be inserted

    for f in file_list:
        if f==allisog_filename: # dealt with differently
            continue
        h = open(os.path.join(base_path, f))
        print "opened %s" % os.path.join(base_path, f)

        parse=parsing_dict[f]
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

    if allisog_filename in file_list: # code added March 2017, not yet tested
        isogmats = read1isogmats(base_path, min_N, max_N)
        for val in vals:
                val.update(isogmats[val['label']])


    if insert:
        print("inserting all data")
        curves.insert_many(vals)
    else:
        count = 0
        for val in vals:
            # print val
            curves.update_one({'label': val['label']}, {"$set": val}, upsert=True)
            count += 1
            if count % 5000 == 0:
                print "inserted %s" % (val['label'])


# A one-off script to add isogeny matrices to the database: this
# version computes on the fly and does not include the isog_degrees
# field.  See add_isogs() for the one to use which reads an allisog
# file.

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
    query['number'] = int(1)
    res = curves.find(query)
    res = res.sort([('conductor', pymongo.ASCENDING),
                    ('lmfdb_iso', pymongo.ASCENDING)])
    for C in res:
        if 'isogeny_matrix' in C:
            print("class {} has isogeny matrix already, skipping".format(C['label']))
            continue
        lmfdb_iso = C['lmfdb_iso']
        E = EllipticCurve([int(a) for a in C['ainvs']])
        M = E.isogeny_class(order="lmfdb").matrix()
        mat = [list([int(c) for c in r]) for r in M.rows()]
        n = len(mat)
        print("{} curves in class {}".format(n,lmfdb_iso))
        for label_i in [lmfdb_iso+str(i+1) for i in  range(n)]:
            data = {}
            data['lmfdb_label'] = label_i
            data['isogeny_matrix'] = mat
            curves.update({'lmfdb_label': label_i}, {"$set": data}, upsert=True)

def add_isogs(base_path, min_N, max_N, upload=False):
    r""" Do not use this function as is since it does not permute the
    matrices returned by allisog() from Cremona to LMFDB labelling
    before uploading.
    """
    f = 'allisog/allisog.%s-%s' % (min_N, max_N)
    h = open(os.path.join(base_path, f))
    print("Opened {}".format(os.path.join(base_path, f)))
    count = 0
    for line in h.readlines():
        data = allisog(line)
        N,iso,num = data['label']
        class_label = N+iso
        num=1
        if 'isogeny_matrix' in curves.find_one({'label':class_label+str(num)}):
            continue
        if count%1000==0:
            print("read {}".format(class_label))
        count += 1
        isogmat = data['isogeny_matrix']
        allisogdegs = data['isogeny_degrees']
        ncurves = len(allisogdegs)
        for n in range(ncurves):
            isogdegs = allisogdegs[n+1]
            label = class_label+str(n+1)
            val = {'isogeny_matrix': isogmat,
                   'isogeny_degrees': isogdegs}
            if upload:
                curves.update_one({'label': label}, {"$set": val}, upsert=True)
            else:
                print("(not) adding {} to record for {}".format(val,label))

def read1isogmats(base_path, min_N, max_N, lmfdb_order=True):
    r""" Returns a dictionary whose keys are Cremona labels of individual
    curves, and whose values are the isogeny_matrix (in LMFDB (default) or Cremona
    ordering) and isogeny_degrees for each curve in the class,
    together with the class size and the maximal degree in the class.

    This function reads a single allisog file.
    """
    if min_N==0:
        f = 'allisog/allisog.00000-09999'
    else:
        f = 'allisog/allisog.%s-%s' % (min_N, max_N)
    h = open(os.path.join(base_path, f))
    print("Opened {}".format(os.path.join(base_path, f)))
    data = {}
    for line in h.readlines():
        data1 = allisog(line, lmfdb_order=lmfdb_order)
        N,iso,num = data1['label']
        class_label = N+iso
        isogmat = data1['isogeny_matrix']
        # maxdeg is the maximum degree of a cyclic isogeny in the
        # class, which uniquely determines the isogeny graph (over Q)
        maxdeg = max(max(r) for r in isogmat)
        allisogdegs = data1['isogeny_degrees']
        ncurves = len(allisogdegs)
        for n in range(ncurves):
            isogdegs = allisogdegs[n+1]
            label = class_label+str(n+1)
            data[label] = {'isogeny_matrix': isogmat,
                           'isogeny_degrees': isogdegs,
                           'class_size': ncurves,
                           'class_deg': maxdeg}
    return data

def readallisogmats(base_path, nfiles=40):
    r""" Returns a dictionary whose keys are Cremona labels of individual
    curves, and whose values are the isogeny_matrix (in Cremona
    ordering) and isogeny_degrees for each curve in the class.

    This function reads all allisog files.
    """
    data = {}
    for k in range(nfiles): # suitable when we have conductors to 10000*nfiles.
        data.update(read1isogmats(base_path,k*10000,(k+1)*10000-1))
    return data

# To add all the isogeny matrix data to the database, first use the
# preceding function readllisogmats() to create a large dict called
# isogdata keyed on curve labels, then pass the following function to
# the rewrite_collection() function:

isogdata = {} # to keep pyflakes happy

def add_isogs_to_one(c):
    c.update(isogdata[c['label']])
    c['lmfdb_number'] = int(c['lmfdb_number'])
    return c

def readallgalreps(base_path, f):
    r""" Returns a dictionary whose keys are Cremona labels of individual
    curves, and whose values are a dictionary with the keys
    'non-maximal_primes' and 'mod-p_images'

    This function reads one new-format galrep file.
    """
    h = open(os.path.join(base_path, f))
    print("Opened {}".format(os.path.join(base_path, f)))
    data = {}
    for line in h.readlines():
        label, data1 = galrep(line, new_format=True)
        data[label] = data1
    return data

# To add all the galrep data to the database, first use the
# preceding function readllgalreps() to create a large dict called
# galrepdata keyed on curve labels, then pass the following function to
# the rewrite_collection() function:

galrepdata = {} # to keep pyflakes happy

def add_galreps_to_one(c):
    c.update(galrepdata[c['label']])
    return c

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

# one-off script to add numerical conversion of the isogeny class letter code, for sorting purposes
def add_numerical_iso_codes(N1,N2):
    """
    Add the 'iso_nlabel' field to every
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
        n += 1
        if n%1000==0: print label
        data = {}
        data['iso_nlabel'] = numerical_iso_label(C['lmfdb_iso'])
        curves.update_one({'_id': C['_id']}, {"$set": data}, upsert=True)

# one-off script to add extra data for curves already in the database

def make_extra_data(label,number,ainvs,gens):
    """
    C is a database elliptic curve entry.  Returns a dict with which to update the entry.

    Data fields needed in C already: 'ainvs', 'lmfdb_label', 'gens', 'number'
    """
    E = EllipticCurve([int(a) for a in ainvs])
    data = {}
    # convert from a list of strings to a single string, e.g. from ['0','0','0','1','1'] to '[0,0,0,1,1]'
    data['xainvs'] = ''.join(['[',','.join(ainvs),']'])
    data['equation'] = web_latex(E)
    data['signD'] = int(E.discriminant().sign())
    data['local_data'] = [{'p': int(ld.prime().gen()),
                           'ord_cond':int(ld.conductor_valuation()),
                           'ord_disc':int(ld.discriminant_valuation()),
                           'ord_den_j':int(max(0,-(E.j_invariant().valuation(ld.prime().gen())))),
                           'red':int(ld.bad_reduction_type()),
                           'rootno':int(E.root_number(ld.prime().gen())),
                           'kod':web_latex(ld.kodaira_symbol()).replace('$',''),
                           'cp':int(ld.tamagawa_number())}
                          for ld in E.local_data()]
    Etw, Dtw = E.minimal_quadratic_twist()
    if Etw.conductor()==E.conductor():
        data['min_quad_twist'] = {'label':label, 'disc':int(1)}
    else:
        # Later this should be changed to look for xainvs but now all curves have ainvs
        minq_ainvs = [str(c) for c in Etw.ainvs()]
        r = curves.find_one({'jinv':str(E.j_invariant()), 'ainvs':minq_ainvs})
        minq_label = "" if r is None else r['label']
        data['min_quad_twist'] = {'label':minq_label, 'disc':int(Dtw)}
    from lmfdb.elliptic_curves.web_ec import parse_points
    gens = [E(g) for g in parse_points(gens)]
    data['heights'] = [float(P.height()) for P in gens]
    if number==1:
        data['aplist'] = E.aplist(100,python_ints=True)
        data['anlist'] = E.anlist(20,python_ints=True)
    return data

def add_extra_data(N1,N2,store=False):
    """Add these fields to curves in the db with conductors from N1 to
    N2: NB This refers to a new collection 'curves2' which was
    created temporarily when upgrading the data stored, and no longer
    exists.

   - 'xainvs': (string) '[a1,a2,a3,a4,a6]' (will replace 'ainvs' in due course)
   - 'equation': (string)
   - 'local_data': (list of dicts, one per prime)
   - 'signD': (sign of discriminant) int (+1 or -1)
   - 'min_quad_twist': (dict) {label:string, disc: int} #NB Cremona label
   - 'heights': (list of floats) heights of generators
   - 'aplist': (list of ints) a_p for p<100
   - 'anlist': (list of ints) a_p for p<20

    """
    curves2 = C.elliptic_curves.curves2
    query = {}
    query['conductor'] = { '$gte': int(N1), '$lte': int(N2) }
    res = curves.find(query)
    res = res.sort([('conductor', pymongo.ASCENDING)])
    n = 0
    res = list(res) # since the cursor times out after a few thousand curves
    newcurves = []
    for c in res:
        n += 1
        if n%100==0:
            print c['lmfdb_label']
        if n%1000==0:
            if store and len(newcurves):
                curves2.insert_many(newcurves)
                newcurves = []
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
        data = make_extra_data(c['label'],c['number'],c['ainvs'],c['gens'])
        c.update(data)
        if store:
            newcurves.append(c)
        else:
            pass
            #print("Not writing updated %s to database.\n" % c['label'])
    # insert the final left-overs since the last full batch
    if store and len(newcurves):
        curves2.insert_many(newcurves)

    print("\nfinished updating conductors from %s to %s" % (N1,N2))

def add_extra_data1(C):
    """Add these fields to a single curve record in the db (for use with
    the rewrite script in data_mgt/utilities/rewrite.py):

   - 'xainvs': (string) '[a1,a2,a3,a4,a6]' (will replace 'ainvs' in due course)
   - 'equation': (string)
   - 'local_data': (list of dicts, one per prime)
   - 'signD': (sign of discriminant) int (+1 or -1)
   - 'min_quad_twist': (dict) {label:string, disc: int} #NB Cremona label
   - 'heights': (list of floats) heights of generators
   - 'aplist': (list of ints) a_p for p<100
   - 'anlist': (list of ints) a_p for p<20

    """
    C.update(make_extra_data(C['label'],C['number'],C['ainvs'],C['gens']))
    return C

def tidy_ecdb(C):
    """A rewrite function for tidying up the curves collection, Feb 2018.
    """
    if C['conductor']<380000:
        return C
    # 1. delete the old redundant 'ainvs' field (we now use 'xainvs'
    #C.pop('ainvs')
    #
    # 2. add local root number if missing
    ld = C['local_data']
    if not 'rootno' in ld[0]:
        E = EllipticCurve([int(ai) for ai in C['xainvs'][1:-1].split(",")])
        for i, ldp in enumerate(ld):
            ldp['rootno'] = int(E.root_number(ZZ(ldp['p'])))
            ld[i] = ldp
        C['local_data'] = ld
    return C

def check_database_consistency(collection, N1=None, N2=None, iwasawa_bound=100000):
    r""" Check that for conductors in the specified range (or all
    conductors) every database entry has all the fields it should, and
    that these have the correct type.
    """
    str_type = type(unicode('abc'))
    int_type = type(int(1))
    float_type = type(float(1))
    list_type = type([1,2,3])
    dict_type = type({'a':1})

    keys_and_types = {'label':  str_type,
                      'lmfdb_label':  str_type,
                      'conductor': int_type,
                      'iso': str_type,
                      'lmfdb_iso': str_type,
                      'iso_nlabel': int_type,
                      'number': int_type,
                      'lmfdb_number': int_type,
                      'ainvs': list_type, # of strings [REDUNDANT]
                      'jinv': str_type,
                      'cm': int_type,
                      'rank': int_type,
                      'torsion': int_type,
                      'torsion_structure': list_type, # of strings
                      'torsion_generators': list_type, # of strings
                      'x-coordinates_of_integral_points': str_type,
                      'gens': list_type, # of strings
                      'regulator': float_type,
                      'tamagawa_product': int_type,
                      'special_value': float_type,
                      'real_period': float_type,
                      'degree': int_type,
                      'non-surjective_primes': list_type, # of ints [REDUNDANT]
                      'non-maximal_primes': list_type, # of ints
                      'galois_images': list_type, # of strings [REDUNDANT]
                      'mod-p_images': list_type, # of strings
                      '2adic_index': int_type,
                      '2adic_log_level': int_type,
                      '2adic_gens': list_type, # of lists of 4 ints
                      '2adic_label': str_type,
                      'isogeny_matrix': list_type, # of lists of ints
                      'isogeny_degrees': list_type, # of ints
                      'class_size': int_type,
                      'class_deg': int_type,
                      'sha_an': float_type,
                      'sha': int_type,
                      'sha_primes': list_type, # of ints
                      'torsion_primes': list_type, # of ints
                      'xainvs': str_type,
                      'equation': str_type,
                      'local_data': list_type, # of dicts
                      'signD': int_type,
                      'min_quad_twist': dict_type,
                      'heights': list_type, # of floats
                      'aplist': list_type, # of ints
                      'anlist': list_type, # of ints
                      'iwdata': dict_type,
                      'iwp0': int_type,
                  }

    key_set = Set(keys_and_types.keys())
    iwasawa_keys = ['iwdata', 'iwp0']        # not present for N > iwasawa_bound
    number_1_only_keys = ['aplist','anlist'] # only present if 'number':1
    no_cm_keys = ['2adic_log_level', '2adic_gens', '2adic_label']

    print("key_set has {} keys".format(len(key_set)))

    query = {}
    Nquery = {}
    if N1 is not None:
        Nquery['$gt'] = int(N1)-1
    if N2 is not None:
        Nquery['$lt'] = int(N2)+1
    if Nquery:
        query['conductor'] = Nquery

    count=0
    for c in C.elliptic_curves.get_collection(collection).find(query):
        count +=1
        if count%10000==0:
            print("Checked {} entries...".format(count))
        expected_keys = key_set
        if c['number']!=1:
            expected_keys = expected_keys - number_1_only_keys
        if c['conductor'] > iwasawa_bound:
            expected_keys = expected_keys - iwasawa_keys

        label = c['label']
        db_keys = Set([str(k) for k in c.keys()]) - ['_id']
        if db_keys == expected_keys:
            for k in db_keys:
                ktype = keys_and_types[k]
                if k in no_cm_keys and c['cm']:
                    ktype = type(None)
                if k=='degree' and c[k]>2**31-1:
                    ktype = type(c[k]) # = <class 'bson.int64.Int64'>
                if type(c[k]) != ktype:
                    print("Type mismatch for key {} in curve {}".format(k,label))
                    print(" in database: {}".format(type(c[k])))
                    print(" expected:    {}".format(keys_and_types[k]))
        else:
            print("keys mismatch for {}".format(label))
            diff1 = [k for k in expected_keys if not k in db_keys]
            diff2 = [k for k in db_keys if not k in expected_keys]
            if diff1: print("expected but absent:      {}".format(diff1))
            if diff2: print("not expected but present: {}".format(diff2))

def update_stats(verbose=True):
    if verbose:
        print("Finding max and min conductor and total number of curves")
    Nlist = curves.distinct('conductor')
    Nmax = int(max(Nlist))
    Nmin = int(min(Nlist))
    Ncurves = int(curves.count())
    if verbose:
        print("{} curves of conductor from {} to {}".format(Ncurves,Nmin,Nmax))
    curves.stats.insert_one({'_id':'conductor', 'min':Nmin, 'max': Nmax, 'total': Ncurves})
    from data_mgt.utilities.rewrite import (update_attribute_stats, update_joint_attribute_stats)
    # Basic counts for these attributes:
    ec = C.elliptic_curves
    if verbose:
        print("Adding simple counts for rank, torsion, torsion structure and Sha")
    update_attribute_stats(ec, 'curves', ['rank', 'torsion', 'torsion_structure', 'sha'])
    # rank counts for isogeny classes:
    if verbose:
        print("Adding isogeny class rank counts")
    update_attribute_stats(ec, 'curves', 'rank', prefix='class', filter={'number':1})
    # torsion order by rank:
    if verbose:
        print("Adding torsion counts by rank")
    update_joint_attribute_stats(ec, 'curves', ['rank','torsion'], prefix='byrank', unflatten=True)
    # torsion structure by rank:
    if verbose:
        print("Adding torsion structure counts by rank")
    update_joint_attribute_stats(ec, 'curves', ['rank','torsion_structure'], prefix='byrank', unflatten=True)
    # sha by rank:
    if verbose:
        print("Adding sha counts by rank")
    update_joint_attribute_stats(ec, 'curves', ['rank','sha'], prefix='byrank', unflatten=True)

def update_torsion_growth_stats(verbose=True):
    # torsion growth:
    if verbose:
        print("Torsion growth stats")
    #curvesnew = C.elliptic_curves.curves.new
    curvesnew = curves
    tor_gro_degs = curvesnew.distinct('tor_degs')
    tor_gro_degs.sort()
    tor_gro_counts = dict([(str(d),curvesnew.count({'tor_degs': d})) for d in tor_gro_degs])
    curves.stats.insert_one({'_id':'torsion_growth', 'degrees': tor_gro_degs, 'counts': tor_gro_counts})
