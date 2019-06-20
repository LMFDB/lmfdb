# -*- coding: utf-8 -*-
r""" Import data from Cremona tables.  Note: This code can be run on
all files in any order. Even if you rerun this code on previously
entered files, it should have no affect.  This code checks if the
entry exists, if so returns that and updates with new information. If
the entry does not exist then it creates it and returns that.

Initial version (Paris 2010)
More tables Feb 2011 Gagan Sekhon

Rewritten by John Cremona and David Roe, Bristol, March 2012
Evolved during 2012-2018
2018: adapted for postgres, JEC.

Postgres table ec_curves has these columns:
"""

qcurves_col_type = {
 u'2adic_gens': u'jsonb',
 u'2adic_index': u'smallint',
 u'2adic_label': u'text',
 u'2adic_log_level': u'smallint',
 u'ainvs': u'jsonb',
 u'anlist': u'jsonb',
 u'aplist': u'jsonb',
 u'class_deg': u'smallint',
 u'class_size': u'smallint',
 u'cm': u'smallint',
 u'conductor': u'numeric',
 u'degree': u'numeric',
 u'equation': u'text',
 u'galois_images': u'jsonb',
 u'gens': u'jsonb',
 u'heights': u'jsonb',
 u'id': u'bigint',
 u'iso': u'text',
 u'iso_nlabel': u'smallint',
 u'isogeny_degrees': u'jsonb',
 u'isogeny_matrix': u'jsonb',
 u'iwdata': u'jsonb',
 u'iwp0': u'smallint',
 u'jinv': u'text',
 u'label': u'text',
 u'lmfdb_iso': u'text',
 u'lmfdb_label': u'text',
 u'lmfdb_number': u'smallint',
 u'local_data': u'jsonb',
 u'min_quad_twist': u'jsonb',
 u'modp_images': u'jsonb',
 u'nonmax_primes': u'jsonb',
 u'nonmax_rad': u'integer',
 u'number': u'smallint',
 u'rank': u'smallint',
 u'real_period': u'numeric',
 u'regulator': u'numeric',
 u'sha': u'integer',
 u'sha_an': u'numeric',
 u'sha_primes': u'jsonb',
 u'signD': u'smallint',
 u'special_value': u'numeric',
 u'tamagawa_product': u'integer',
 u'tor_degs': u'jsonb',
 u'tor_fields': u'jsonb',
 u'tor_gro': u'jsonb',
 u'torsion': u'smallint',
 u'torsion_generators': u'jsonb',
 u'torsion_primes': u'jsonb',
 u'torsion_structure': u'jsonb',
 u'trace_hash': u'bigint',
 u'xcoord_integral_points': u'jsonb',
}

r"""

The documents in the mongo collection 'curves' in the database 'elliptic_curves' had the following fields:

   - '_id': internal mogodb identifier
   - 'label':  (string) full Cremona label, e.g. '1225a2'
   - 'lmfdb_label':  (string) full LMFDB label, e.g. '1225.a2'
   - 'conductor': (int) conductor, e.g. 1225
   - 'iso': (string) Cremona isogeny class code, e.g. '11a'
   - 'lmfdb_iso': (string) LMFDB isogeny class code, e.g. '11.a'
   - 'iso_nlabel': (int) numerical version of the (lmfdb) isogeny class label
   - 'number': (int) Cremona curve number within its class, e.g. 2
   - 'lmfdb_number': (int) LMFDB curve number within its class, e.g. 2
   - 'ainvs': (string representing list of ints) a-invariants, e.g. '[0,1,1,10617,75394]'
   - 'jinv': (string) j-invariant, e.g. -4096/11
   - 'cm': (int) 0 for no CM, or a negative discriminant
   - 'rank': (int) rank, e.g. 0
   - 'torsion': (int) torsion order, e.g. 1
   - 'torsion_structure': (list of strings) list of invariants of torsion subgroup, e.g. ['3']
   - 'torsion_generators': (list of strings) list of generators of torsion subgroup, e.g. ['(5, 5)']
   - 'xcoord_integral_points': (string) list of x-coordinates of integral points, e.g. '[5,16]'
   - 'gens': (list of strings) list of generators of infinite order, e.g. ['(0:0:1)']
   - 'regulator': (float) regulator, e.g. 1.0
   - 'tamagawa_product': (int) product of Tamagawa numbers, e.g. 4
   - 'special_value': (float) special value of r'th derivative of L-function (divided by r!), e.g.1.490882041449698
   - 'real_period': (float) real period, e.g. 0.3727205103624245
   - 'degree': (int) degree of modular parametrization, e.g. 1984
   - 'nonmax_primes': (list of ints) primes p for which the
      mod p Galois representation is not maximal, e.g. [5]
   - 'nonmax_radd': (int) product of nonmax_primes
   - 'modp_images': (list of strings) Sutherland codes for the
      images of the mod p Galois representations for the primes in
      'nonmax_primes' e.g. ['5B']
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
     curves in the class w.r.t. LMFDB ordering
   - 'isogeny_degrees': (list of ints) degrees of cyclic isogenies from this curve
   - 'class_size': (int) size of isogeny class
   - 'class_deg': (int) max (=lcm) of isogeny degrees in the class
   - 'sha': (int) analytic order of sha (rounded value of sha_an)
   - 'sha_primes': (list of ints) primes dividing sha
   - 'torsion_primes': (list of ints) primes dividing torsion

Extra data fields added May 2016 to avoid computation on the fly:
   - 'ainvs': (string) '[a1,a2,a3,a4,a6]' (replaced 'ainvs' in due course)
   - 'equation': (string)
   - 'local_data': (list of dicts, one per prime)
   - 'signD': (sign of discriminant) int (+1 or -1)
   - 'min_quad_twist': (dict) {label:string, disc: int} #NB Cremona label
   - 'heights': (list of floats) heights of generators
   - 'aplist': (list of ints) a_p for p<100
   - 'anlist': (list of ints) a_p for p<20
"""

import re, os, pprint
from sage.all import ZZ, RR, EllipticCurve, prod, Set
from lmfdb.utils import web_latex
from lmfdb import db
print "setting curves"
curves = db.ec_curves

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
    Given a string like '[a1,a2,a3,a4,a6]' returns the list of integers [a1,a2,a3,a4,a6]
    """
    return [ZZ(a) for a in s[1:-1].split(',')]


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
    ainvs = data[3]

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
    ainvs = data[3]
    E = EllipticCurve([ZZ(a) for a in parse_ainvs(ainvs)])
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
    'xcoord_integral_points', all values being strings.

    Input line fields:

    label ainvs x-coordinates_of_integral_points

    Sample input line:

    11a1 [0,-1,1,-10,-20] [5,16]
    """
    data = split(line)
    label = data[0]
    ainvs = data[1]
    return label, {
        'ainvs': ainvs,
        'xcoord_integral_points': data[2]
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
    dict containing two fields: 'nonmax_primes', a list of
    primes p for which the Galois representation modulo p is not
    maximal, 'modp_images', a list of strings
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
            'nonmax_primes': pr,
            'nonmax_rad': prod(pr),
            'modp_images': image_codes,
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

    Note that the website shows the isogeny class w.r.t. either the
    LMFDB or the Cremona ordering; in the latter case, they are
    permuted before displaying.

    Input line fields:

    conductor iso number ainvs all_ainvs isogeny_matrix

    Sample input line:

    11 a 1 [0,-1,1,-10,-20] [[0,-1,1,-10,-20],[0,-1,1,-7820,-263580],[0,-1,1,0,0]] [[1,5,5],[5,1,25],[5,25,1]]

    """
    data = split(line)
    isomat = data[5]
    isomat = [[int(d) for d in row.split(",")] for row in isomat[2:-2].split("],[")]
    
    # This dict stores the degrees of (cyclic) isogenies from each
    # curve.  We must compute this *before* the optional (but default)
    # reordering of the rows/cols.  The value for key n (=1,2,3,...)
    # is a sorted list of distinct degrees for the n'th curve in the
    # Cremona ordering.

    isogeny_degrees = dict([[n+1,sorted(list(set(row)))] for n,row in enumerate(isomat)])

    if lmfdb_order:
        curves = data[4] # string
        curves = [[ZZ(ai) for ai in c.split(",")] for c in curves[2:-2].split("],[")]
        perm = dict([[i,curves.index(c)] for i,c in enumerate(sorted(curves))])
        # that maps L to C (with offset by 1)
        ncurves = len(curves)
        isomat = [[isomat[perm[i]][perm[j]] for i in range(ncurves)] for j in range(ncurves)]


    return {'label': data[:3],
        'isogeny_matrix': isomat,
        'isogeny_degrees': isogeny_degrees,
    }

def fix_isogeny_degrees(C):
    """function to (re)compute the isogeny_degrees field of a database
    curve C from the isogeny_matrix. Note that the rows/columns of the
    isogeny_matrix are indexed 1,2,... using LMFDB ordering.  There is
    nothing to do if the class size is 1 or 2.
    """
    if C['class_size'] < 3:
        return C
    isomat = C['isogeny_matrix']
    old_isodegs = C['isogeny_degrees']
    new_isodegs = sorted(list(set(isomat[C['lmfdb_number']-1])))
    if new_isodegs == old_isodegs:
        return C
    #print("changing isogeny_degrees for {} ({}) from {} to {}".format(C['label'],C['lmfdb_label'],old_isodegs,new_isodegs))
    C['isogeny_degrees'] = new_isodegs
    return C
    

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

def upload_to_db(base_path, min_N, max_N, insert=True, test=True):
    r""" Uses insert_many() if insert=True, which is faster but will create
    duplicates and cause problems if any of the the labels are already
    in the database; otherwise uses upsert() which will update a
    single row, or add a row.
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
        if test:
            print("(not) inserting all data")
            print("First 10 vals:")
            for v in vals[:10]:
                pprint.pprint(v)
        else:
            print("inserting all data ({} items)".format(len(vals)))
            curves.insert_many(vals)
    else:
        count = 0
        for val in vals:
            # print val
            curves.upsert({'label': val['label']}, val)
            count += 1
            if count % 5000 == 0:
                print "inserted %s" % (val['label'])

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
# preceding function readallisogmats() to create a large dict called
# isogdata keyed on curve labels, then pass the following function to
# the rewrite() method of db_ec_curves:

isogdata = {} # to keep pyflakes happy

def add_isogs_to_one(c):
    c.update(isogdata[c['label']])
    c['lmfdb_number'] = int(c['lmfdb_number'])
    return c

def readallgalreps(base_path, f):
    r""" Returns a dictionary whose keys are Cremona labels of individual
    curves, and whose values are a dictionary with the keys
    'nonmax_primes', 'nonmax_rad' and 'modp_images'

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
# the rewrite() method of db.ec_curves:

galrepdata = {} # to keep pyflakes happy

def add_galreps_to_one(c):
    c.update(galrepdata[c['label']])
    return c

# function to compute some extra data on the fly duringupload.  This is called in the function allgens()

def make_extra_data(label,number,ainvs,gens):
    """Given a curve label (and number, as some data is only stored wih
    curve number 1 in each class) and its ainvs and gens, returns a
    dict with which to update the entry.

    Extra items computed here:
    'equation': latex string of curve's equation
    'signD': sign of discriminant
    'local_data': list of dicts, one item for each bad prime
    'min_quad_twist': dict holding curve's min quadratic twist and the twisting discriminant
    'heights': list of heights of gens

    and for curve #1 in a class only:

    'aplist': list of a_p for p<100
    'anlist': list of a_n for n<=20

    """
    E = EllipticCurve(parse_ainvs(ainvs))
    data = {}
    # convert from a list of strings to a single string, e.g. from ['0','0','0','1','1'] to '[0,0,0,1,1]'
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
        minq_ainvs = ''.join(['['] + [str(c) for c in Etw.ainvs()] + [']'])
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


def check_database_consistency(table, N1=None, N2=None, iwasawa_bound=100000):
    r""" Check that for conductors in the specified range (or all
    conductors) every database entry has all the fields it should, and
    that these have the correct type.

    NB Some key names were changed in the postgres conversion:
    'xainvs'                --> 'ainvs'
    'mod-p_images'          --> 'modp_images'
    'non-maximal_primes'    --> 'nonmax_primes'
    'x-coordinates_of_integral_points' --> 'xcoord_integral_points'

    """
    str_type = type(unicode('abc'))
    int_type = type(int(1))
    bigint_type = type(ZZ(1))
    list_type = type([1,2,3])
    dict_type = type({'a':1})
    real_type = type(table.lucky({'label':'11a1'})['sha_an'])
    
    keys_and_types = {'label':  str_type,
                      'lmfdb_label':  str_type,
                      'conductor': bigint_type,
                      'iso': str_type,
                      'lmfdb_iso': str_type,
                      'iso_nlabel': int_type,
                      'number': int_type,
                      'lmfdb_number': int_type,
                      'jinv': str_type,
                      'cm': int_type,
                      'rank': int_type,
                      'torsion': int_type,
                      'torsion_structure': list_type, # of strings
                      'torsion_generators': list_type, # of strings
                      'xcoord_integral_points': list_type,
                      'gens': list_type, # of strings
                      'regulator': real_type,
                      'tamagawa_product': int_type,
                      'special_value': real_type,
                      'real_period': real_type,
                      'degree': bigint_type,
                      'nonmax_primes': list_type, # of ints
                      'nonmax_rad': int_type,
                      'galois_images': list_type, # of strings [REDUNDANT]
                      'modp_images': list_type, # of strings
                      '2adic_index': int_type,
                      '2adic_log_level': int_type,
                      '2adic_gens': list_type, # of lists of 4 ints
                      '2adic_label': str_type,
                      'isogeny_matrix': list_type, # of lists of ints
                      'isogeny_degrees': list_type, # of ints
                      'class_size': int_type,
                      'class_deg': int_type,
                      'sha_an': real_type,
                      'sha': int_type,
                      'sha_primes': list_type, # of ints
                      'torsion_primes': list_type, # of ints
                      'ainvs': list_type,
                      'equation': str_type,
                      'local_data': list_type, # of dicts
                      'signD': int_type,
                      'min_quad_twist': dict_type,
                      'heights': list_type, # of floats
                      'aplist': list_type, # of ints
                      'anlist': list_type, # of ints
                      'iwdata': dict_type,
                      'iwp0': int_type,
                      'tor_fields': list_type,
                      'tor_gro': dict_type,
                      'tor_degs': list_type,
                      'trace_hash': type(long()),
    }

    key_set = Set(keys_and_types.keys())
    table_key_set = Set(qcurves_col_type)- ['id']
    if key_set==table_key_set:
        print("key set matches the table keys exactly")
    else:
        print("key set and table keys differ:")
        diff1 = [k for k in table_key_set if not k in key_set]
        print("{} keys in table not in key set: {}".format(len(diff1),diff1))
        diff2 = [k for k in key_set if not k in table_key_set]
        print("{} keys in key set not in table keys: {}".format(len(diff2),diff2))
        print()
        print("{} keys in key set:".format(len(key_set)))
        print(key_set)
        print()
        print("{} keys in table keys:".format(len(table_key_set)))
        print(table_key_set)
        return

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

    big_deg = 2**31-1
    count=0
    for c in table.search(query, projection=2):
        count +=1
        if count%10000==0:
            print("Checked {} entries...".format(count))
        expected_keys = key_set
        if c['number']!=1:
            expected_keys = expected_keys - number_1_only_keys
        if c['conductor'] > iwasawa_bound:
            expected_keys = expected_keys - iwasawa_keys

        label = c['label']
        db_keys = Set([str(k) for k in c.keys()]) - ['id']
        if db_keys == expected_keys:
            for k in db_keys:
                ktype = keys_and_types[k]
                if k in no_cm_keys and c['cm']:
                    continue
                if k=='degree' and c[k]>big_deg:
                    continue
                if type(c[k])!=ktype:
                    print("Type mismatch for key {} in curve {}".format(k,label))
                    print(" in database: {}".format(type(c[k])))
                    print(" expected:    {}".format(keys_and_types[k]))
        else:
            diff1 = [k for k in expected_keys if not k in db_keys and not (k in no_cm_keys and c['cm'])]
            diff2 = [k for k in db_keys if not k in expected_keys]
            if diff1 or diff2:
                print("keys mismatch for {}".format(label))
            if diff1: print("expected but absent:      {}".format(diff1))
            if diff2: print("not expected but present: {}".format(diff2))


def update_stats(recount=True, verbose=True):

    ecdb = db.ec_curves
    ecdbstats = db.ec_curves.stats
    if recount:
        ec_count = ecdbstats._slow_count
        ec_max = ecdbstats._slow_max
    else:
        ec_count = ecdb.count
        ec_max = ecdb.max

    # Do various counts, force each to be a recount so the (possibly)
    # updated value gets stored:
    ncurves = ec_count({})
    nclasses = ec_count({'number':1})

    if verbose:
        print("{} curves in {} isogeny classes".format(ncurves,nclasses))

    # Various max values, forced to be recomputed (?and stored?)
    max_N = ec_max('conductor',{})
    max_r = ec_max('rank',{})
    max_sha = ec_max('sha',{})
    max_sqrt_sha = ZZ(max_sha).sqrt() # exact
    if verbose:
        print("max conductor = {}".format(max_N))
        print("max rank = {}".format(max_r))
        print("max Sha = {} = {}^2".format(max_sha, max_sqrt_sha))

    for r in range(max_r+1):
        ncu = ec_count({'rank':r})
        ncl = ec_count({'rank':r, 'number':1})
        if verbose:
            print("{} curves in {} classes have rank {}".format(ncu,ncl,r))

    for t in  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16]:
        ncu = ec_count({'torsion':t})
        if verbose:
            print("{} curves have torsion order {}".format(ncu,t))
        if t in [4,8,12]: # two possible structures
            ncyc = ec_count({'torsion_structure':[t]})
            if verbose:
                print("   of which {} curves have cyclic torsion, {} non-cyclic".format(ncyc,ncu-ncyc))

    for s in range(1,1+max_sqrt_sha):
        ncu = ec_count({'sha':s**2})
        if verbose and ncu:
            print("{} curves have Sha order {}^2".format(ncu,s))
    
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

def update_int_pts(filename, test=True, verbose=0, basepath=None):
    if basepath==None:
        basepath = os.environ['HOME']
    int_pts_data = {}
    for L in open(os.path.join(basepath,filename)):
        lab, dat = intpts(L)
        int_pts_data[lab] = dat

    print("read {} lines of data".format(len(int_pts_data)))

    for lab in int_pts_data:
        e = curves.lucky({'label':lab})

        assert e['label']==lab
        dat = int_pts_data[lab]
        assert e['ainvs']==parse_ainvs(dat['ainvs'])
        db_xs = e['xcoord_integral_points']
        if verbose>1:
            print("{}: xs read from db:   {}".format(lab,db_xs))
        file_xs = parse_ainvs(dat['xcoord_integral_points'])
        if verbose>1:
            print("{}: xs read from file: {}".format(lab,file_xs))
        if db_xs==file_xs:
            if verbose:
                print("{}: data agrees".format(lab))
        else:
            if verbose:
                print("{}: db has {} xs while file has {}".format(lab,len(db_xs),len(file_xs)))
            d = [x for x in db_xs if not x in file_xs]
            if d:
                print("Curve {}: ****************** db has x = {} not in file!".format(lab, d))
            d = [x for x in file_xs if not x in db_xs]
            if d and verbose:
                print("file has x = {} not in db".format(d))

            # Update the copy of the database record:
            e['xcoord_integral_points'] = file_xs
            if verbose>1:
                print("New curve record for {}: {}".format(lab, e))
            if test:
                print("Not changing database entry for {}".format(lab))
            else:
                print("Using upsert to change database entry for {}".format(lab))
                curves.upsert({'label': lab}, e)
