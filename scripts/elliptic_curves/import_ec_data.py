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

Postgres table ec_curves has these columns (updated 2019-08-05):
"""
from __future__ import print_function
from six import text_type

qcurves_col_type = {
    u'2adic_gens': 'jsonb',
    u'2adic_index': 'smallint',
    u'2adic_label': 'text',
    u'2adic_log_level': 'smallint',
    u'ainvs': 'jsonb',
    u'anlist': 'jsonb',
    u'aplist': 'jsonb',
    u'bad_primes': 'integer[]',
    u'class_deg': 'smallint',
    u'class_size': 'smallint',
    u'cm': 'smallint',
    u'conductor': 'numeric',
    u'degree': 'numeric',
    u'equation': 'text',
    #u'galois_images': 'jsonb', # column dropped 20190828
    u'gens': 'jsonb',
    u'heights': 'jsonb',
    u'id': 'bigint',
    u'iso': 'text',
    u'iso_nlabel': 'smallint',
    u'isogeny_degrees': 'jsonb',
    u'isogeny_matrix': 'jsonb',
    u'iwdata': 'jsonb',
    u'iwp0': 'smallint',
    u'jinv': 'text',
    u'label': 'text',
    u'lmfdb_iso': 'text',
    u'lmfdb_label': 'text',
    u'lmfdb_number': 'smallint',
    u'local_data': 'jsonb',
    u'manin_constant': 'smallint', # added 20190828
    u'min_quad_twist': 'jsonb',
    u'modp_images': 'jsonb',
    u'nonmax_primes': 'jsonb',
    u'nonmax_rad': 'integer',
    u'number': 'smallint',
    u'num_bad_primes': 'smallint', # added 20190828
    u'num_int_pts': 'smallint', # added 20190828
    u'optimality': 'smallint', # added 20190828
    u'rank': 'smallint',
    u'real_period': 'numeric',
    u'regulator': 'numeric',
    u'semistable': 'boolean', # added 20190828
    u'sha': 'integer',
    u'sha_an': 'numeric',
    u'sha_primes': 'jsonb',
    u'signD': 'smallint',
    u'special_value': 'numeric',
    u'tamagawa_product': 'integer',
    u'tor_degs': 'jsonb',
    u'tor_fields': 'jsonb',
    u'tor_gro': 'jsonb',
    u'torsion': 'smallint',
    u'torsion_generators': 'jsonb',
    u'torsion_primes': 'jsonb',
    u'torsion_structure': 'jsonb',
    u'trace_hash': 'bigint',
    u'xcoord_integral_points': 'jsonb',
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
   - 'ainvs': (list of ints) a-invariants, e.g. [0,1,1,10617,75394]
   - 'jinv': (string) j-invariant, e.g. -4096/11
   - 'cm': (int) 0 for no CM, or a negative discriminant
   - 'rank': (int) rank, e.g. 0
   - 'torsion': (int) torsion order, e.g. 1
   - 'torsion_structure': (list of strings) list of invariants of torsion subgroup, e.g. ['3']
   - 'torsion_generators': (list of strings) list of generators of torsion subgroup, e.g. ['(5, 5)']
   - 'xcoord_integral_points': (list of ints) list of x-coordinates of integral points, e.g. [5,16]
   - 'gens': (list of strings) list of generators of infinite order, e.g. ['(0:0:1)']
   - 'regulator': (float) regulator, e.g. 1.0
   - 'tamagawa_product': (int) product of Tamagawa numbers, e.g. 4
   - 'special_value': (float) special value of r'th derivative of L-function (divided by r!), e.g.1.490882041449698
   - 'real_period': (float) real period, e.g. 0.3727205103624245
   - 'degree': (int) degree of modular parametrization, e.g. 1984
   - 'nonmax_primes': (list of ints) primes p for which the
      mod p Galois representation is not maximal, e.g. [5]
   - 'nonmax_rad': (int) product of nonmax_primes
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
   - 'equation': (string)
   - 'local_data': (list of dicts, one per prime)
   - 'signD': (sign of discriminant) int (+1 or -1)
   - 'min_quad_twist': (dict) {label:string, disc: int} #NB Cremona label
   - 'heights': (list of floats) heights of generators
   - 'aplist': (list of ints) a_p for p<100
   - 'anlist': (list of ints) a_p for p<20

   - 'num_int_pts': (int) number of integral points (up to sign)
   - 'num_bad_primes': (int) number of bad primes
   - 'semistable': (bool) is conductor squarefree?
   - 'optimality': (int) -1 if optimality status unknown
                          0 if not optimal
                          1 if optimal
                          n>1 if one of n possibly optimal curves in its isogeny class
   - 'manin_constant': (int) Manin constant, 0 if unknown

"""

import re, os
import time
from sage.all import ZZ, RR, EllipticCurve, prod, Set
from lmfdb.utils import web_latex, TraceHashClass
from lmfdb.elliptic_curves.web_ec import count_integral_points
from lmfdb import db
print("setting curves")
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

# Two dicts: the first has lmfdb labels as keys and the corresponding
# Cremona labels as values; the second is the other way round.  These
# are filled by alllabels() and used by allgens().

lmfdb_label_to_label = {}
label_to_lmfdb_label = {}

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

nallgens = 0

def allgens(line):
    r""" Parses one line from an allgens file.  Returns the label and
    a dict containing fields with keys 'conductor', 'iso', 'number',
    'ainvs', 'jinv', 'cm', 'rank', 'gens', 'torsion_order', 'torsion_structure',
    'torsion_generators', all values being strings or ints, and more.

    Input line fields:

    conductor iso number ainvs rank torsion_structure gens torsion_gens

    Sample input line:

    20202 i 2 [1,0,0,-298389,54947169] 1 [2,4] [-570:6603:1] [-622:311:1] [834:19239:1]
    """
    global lmfdb_label_to_label
    global label_to_lmfdb_label

    data = split(line)
    iso = data[0] + data[1]
    label = iso + data[2]
    try:
        lmfdb_label = label_to_lmfdb_label[label]
    except AttributeError:
        print("Label {} not found in label_to_lmfdb_label dict!".format(label))
        lmfdb_label = ""

    global nallgens
    nallgens += 1
    if nallgens%100==0:
        print("processing allgens for {} (#{})".format(label, nallgens))
    rank = int(data[4])
    t = data[5]
    tor_struct = [] if t=='[]' else t[1:-1].split(",")
    torsion = int(prod([int(ti) for ti in tor_struct], 1))
    ainvs = parse_ainvs(data[3])
    E = EllipticCurve(ainvs)
    jinv = text_type(E.j_invariant())
    if E.has_cm():
        cm = int(E.cm_discriminant())
    else:
        cm = int(0)
    N = E.conductor()
    bad_p = N.prime_factors() # will be sorted
    num_bad_p = len(bad_p)

    local_data = [{'p': int(ld.prime().gen()),
                           'ord_cond':int(ld.conductor_valuation()),
                           'ord_disc':int(ld.discriminant_valuation()),
                           'ord_den_j':int(max(0,-(E.j_invariant().valuation(ld.prime().gen())))),
                           'red':int(ld.bad_reduction_type()),
                           'rootno':int(E.root_number(ld.prime().gen())),
                           'kod':web_latex(ld.kodaira_symbol()).replace('$',''),
                           'cp':int(ld.tamagawa_number())}
                          for ld in E.local_data()]
    semistable = all([ld['ord_cond']==1 for ld in local_data])

    gens = [gen.replace("[","(").replace("]",")") for gen in data[6:6 + rank]]
    tor_gens = ["%s" % parse_tgens(tgens[1:-1]) for tgens in data[6 + rank:]]

    from lmfdb.elliptic_curves.web_ec import parse_points
    heights = [float(E(P).height()) for P in parse_points(gens)]

    Etw, Dtw = E.minimal_quadratic_twist()
    if Etw.conductor()==N:
        min_quad_twist = {'label':label, 'lmfdb_label':lmfdb_label, 'disc':int(1)}
    else:
        minq_ainvs = Etw.ainvs()
        r = curves.lucky({'jinv':str(E.j_invariant()), 'ainvs':minq_ainvs}, projection=['label','lmfdb_label'])
        min_quad_twist = {'label': r['label'], 'lmfdb_label':r['lmfdb_label'], 'disc':int(Dtw)}

    trace_hash = TraceHashClass(iso, E)

    return label,  {
        'conductor': int(data[0]),
        'iso': iso,
        'number': int(data[2]),
        'ainvs': ainvs,
        'jinv': jinv,
        'cm': cm,
        'rank': rank,
        'gens': gens,
        'torsion': torsion,
        'torsion_structure': tor_struct,
        'torsion_generators': tor_gens,
        'trace_hash': trace_hash,
        'equation': web_latex(E),
        'bad_primes': bad_p,
        'num_bad_primes': num_bad_p,
        'local_data': local_data,
        'semistable': semistable,
        'signD': int(E.discriminant().sign()),
        'heights': heights,
        'aplist': E.aplist(100,python_ints=True),
        'anlist': E.anlist(20,python_ints=True),
        'min_quad_twist': min_quad_twist,
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
    'xcoord_integral_points', all values being strings.

    Input line fields:

    label ainvs x-coordinates_of_integral_points

    Sample input line:

    11a1 [0,-1,1,-10,-20] [5,16]
    """
    data = split(line)
    label = data[0]
    ainvs = parse_ainvs(data[1])
    xs = [] if data[2]=='[]' else parse_ainvs(data[2])
    return label, {
        'ainvs': ainvs,
        'xcoord_integral_points': xs,
        'num_int_pts': len(xs)
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

    Also populates two global dictionaries lmfdb_label_to_label and
    label_to_lmfdb_label, allowing other upload functions to look
    these up.

    Input line fields:

    conductor iso number conductor lmfdb_iso lmfdb_number

    Sample input line:

    57 c 2 57 b 1

    """
    global lmfdb_label_to_label
    global label_to_lmfdb_label
    data = split(line)
    if data[0] != data[3]:
        raise ValueError("Inconsistent data in alllabels file: %s" % line)
    label = data[0] + data[1] + data[2]
    lmfdb_label = data[3] + '.' + data[4] + data[5]
    lmfdb_iso = data[3] + '.' + data[4]
    iso_nlabel = numerical_iso_label(lmfdb_iso)

    lmfdb_label_to_label[lmfdb_label] = label
    label_to_lmfdb_label[label] = lmfdb_label

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

def opt_man(line):
    r""" Parses one line from an opt_man file, giving optimality and Manin
    constant data.  Returns the label and a dict containing fields
    with keys 'optimality', 'manin_constant', both values ints.

    Input line fields:

    N iso num ainvs opt mc

    where opt = (0 if not optimal, 1 if optimal, n>1 if one of n
    possibly optimal curves in the isogeny class), and mc = Manin
    constant *conditional* on curve #1 in the lcass being the optimal
    one.

    Sample input lines with comments added:

    11 a 1 [0,-1,1,-10,-20] 1 1       # optimal, mc=1
    11 a 2 [0,-1,1,-7820,-263580] 0 1 # not optimal, mc=1
    11 a 3 [0,-1,1,0,0] 0 5           # not optimal, mc=5
    499992 a 1 [0,-1,0,4481,148204] 3 1       # one of 3 possible optimal curves in class g, mc=1 for all whichever is optimal
    499992 a 2 [0,-1,0,-29964,1526004] 3 1    # one of 3 possible optimal curves in class g, mc=1 for all whichever is optimal
    499992 a 3 [0,-1,0,-446624,115024188] 3 1 # one of 3 possible optimal curves in class g, mc=1 for all whichever is optimal
    499992 a 4 [0,-1,0,-164424,-24344100] 0 1 # not optimal, mc=1
    """
    N, iso, num, ainvs, opt, mc = split(line)
    label = N+iso+num
    opt = int(opt)
    mc = int(mc)
    return label, {
        'optimality': opt,
        'manin_constant': mc,
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


def cmp_label(lab1, lab2):
    """
    EXAMPLES::

    cmp_label('24a5', '33a1')
    -1
    cmp_label('11a1', '11a1')
    0
    """
    from sage.databases.cremona import parse_cremona_label, class_to_int
    a, b, c = parse_cremona_label(lab1)
    id1 = int(a), class_to_int(b), int(c)
    a, b, c = parse_cremona_label(lab2)
    id2 = int(a), class_to_int(b), int(c)
    if id1 == id2:
        return 0
    return -1 if id1 < id2 else 1


def sorting_label(d1):
    """
    Provide a sorting key.
    """
    from sage.databases.cremona import parse_cremona_label, class_to_int
    a, b, c = parse_cremona_label(d1["label"])
    return (int(a), class_to_int(b), int(c))


def encode(x):
    if x is None:
        return '\\N'
    if x is True:
        return 't'
    if x is False:
        return 'f'
    return str(x)


def copy_records_to_file(records, fname, id0=0, verbose=True):
    searchfile = fname+'.search'
    extrafile = fname+'.extra'
    if verbose:
        print("Writing records to {} and {}".format(searchfile, extrafile))

    # NB since records might be a generator object we only pass through it once.

    fs = open(searchfile, 'w')
    fe = open(extrafile, 'w')
    curves._write_header_lines(fs, ["id"]+curves.search_cols)
    curves._write_header_lines(fe, ["id"]+curves.extra_cols)

    id = id0
    for c in records:
        fs.write("\t".join([str(id)]+[encode(c[k]) for k in curves.search_cols]))
        fs.write("\n")
        fe.write("\t".join([str(id)]+[encode(c[k]) for k in curves.extra_cols]))
        fe.write("\n")
        id +=1
    fs.close()
    fe.close()
    if verbose:
        print("Wrote {} lines to {} and {}".format(id-id0, searchfile, extrafile))

#


def upload_to_db(base_path, min_N, max_N, insert=True, mode='test'):
    r""" Uses insert_many() if insert=True, which is faster but will create
    duplicates and cause problems if any of the the labels are already
    in the database; otherwise uses upsert() which will update a
    single row, or add a row.

    mode = 'test': no upload or file dump, just check keys are correct and return the list of records
    mode = 'upload': upload directly
    mode = 'dump': write to files (one search, one extras)

    In case mode=='dump', files ec_curves.<N1>-<N2> and
    ec_curves.extras.<N1>-<N2> will be written, suitable for reading
    in using copy_from *after* prepending three header lines to each.

    NB The allgens() function requires the labels dics to be populated to alllabels must be read before allgens

    To run this go into the top-level lmfdb directory, run sage and give
    the command
    sage: %runfile lmfdb/elliptic_curves/import_ec_data.py

    The a typical command would be

    sage: v = upload_to_db("/scratch/jcremona/ecdata/", 490000, 499999, mode='test')

    to test that all is OK using input files in ~/ecdata/*/*.490000-499999

    or

    sage: upload_to_db("/scratch/jcremona/ecdata/", 490000, 499999, mode='upload')

    to actually upload data.  NB In the default insert==True it is
    important that the curves being uploaded are *not* already in
    the database.  To clear out the range about to be uploaded (if necessary) do

    sage: curves.delete({'conductor': {'$gte':490000, '$lte': 499999}})

    Future plans: run with mode='dump' to do all the processing and
    write to a file with correct headers (written but only partially
    tested); then use curves.copy_from() to do the upload.
    """
    Nrange = str(min_N) if min_N==max_N else "{}-{}".format(min_N,max_N)
    allbsd_filename = 'allbsd/allbsd.{}'.format(Nrange)
    allgens_filename = 'allgens/allgens.{}'.format(Nrange)
    intpts_filename = 'intpts/intpts.{}'.format(Nrange)
    alldegphi_filename = 'alldegphi/alldegphi.{}'.format(Nrange)
    alllabels_filename = 'alllabels/alllabels.{}'.format(Nrange)
    galreps_filename = 'galrep/galrep.{}'.format(Nrange)
    twoadic_filename = '2adic/2adic.{}'.format(Nrange)
    allisog_filename = 'allisog/allisog.{}'.format(Nrange)
    opt_man_filename = 'opt_man/opt_man.{}'.format(Nrange)
    file_list = [alllabels_filename, allgens_filename, allbsd_filename, intpts_filename, alldegphi_filename, galreps_filename,twoadic_filename,allisog_filename,opt_man_filename]
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
    keys = curves.col_type.keys()
    keys.remove('id')
    keys.sort()
    global nallgens
    nallgens = 0

    for f in file_list:
        if f==allisog_filename: # dealt with differently
            continue
        t0=time.time()
        h = open(os.path.join(base_path, f))
        print("opened %s" % os.path.join(base_path, f))

        parse=parsing_dict[f]
        count = 0
        for line in h.readlines():
            label, data = parse(line)
            if count%5000==0:
                print("read {} ({} lines so far, in {})".format(label, count+1, time.time()-t0))
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
        print("finished reading {} lines from file in {}".format(count, time.time()-t0))

    vals = data_to_insert.values()
    # vals.sort(key=sorting_label)

    if allisog_filename in file_list:
        isogmats = read1isogmats(base_path, min_N, max_N)
        for val in vals:
            val.update(isogmats[val['label']])

    # file fields iw* and tor* with null values as these are uploaded
    # separately, and WebEC objects handle these being None properly.
    for v in vals:
        v['iwdata'] = None
        v['iwp0'] = None
        v['tor_degs'] = None
        v['tor_fields'] = None
        v['tor_gro'] = None

    print("Checking keys")
    ok = True
    for v in vals:
        vkeys = sorted(v.keys())
        if vkeys!=keys:
            ok = False
            print("{} has incorrect key set".format(v['label']))
            print("keys present but not expected: {}".format([k for k in vkeys if not k in keys]))
            print("keys expected but not present: {}".format([k for k in keys if not k in vkeys]))
            #print("keys are {} but should be {}".format(vkeys,keys))
    if ok:
        print("All records have all required keys")
    else:
        print("Some records have missing keys, no uploading")
        return

    if insert:
        if mode=='test':
            print("(not) inserting all data")
            return vals
        elif mode=='upload':
            print("inserting all data ({} items)".format(len(vals)))
            curves.insert_many(vals)
        elif mode=='dump':
            copy_records_to_file(vals, 'curves.{}-{}'.format(min_N,max_N), curves.max_id()+1)
        else:
            print("mode {} not recognised!  Should be one of 'test', 'upload', 'dump'.".format(mode))
    else:
        count = 0
        for val in vals:
            # print val
            curves.upsert({'label': val['label']}, val)
            count += 1
            if count % 5000 == 0:
                print("inserted %s" % (val['label']))

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
        Nrange = str(min_N) if min_N==max_N else "{}-{}".format(min_N,max_N)
        f = 'allisog/allisog.{}'.format(Nrange)
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

def check_database_consistency(table, N1=None, N2=None, iwasawa_bound=150000):
    r""" Check that for conductors in the specified range (or all
    conductors) every database entry has all the fields it should, and
    that these have the correct type.

    NB Some key names were changed in the postgres conversion:
    'xainvs'                --> 'ainvs'
    'mod-p_images'          --> 'modp_images'
    'non-maximal_primes'    --> 'nonmax_primes'
    'x-coordinates_of_integral_points' --> 'xcoord_integral_points'

    """
    str_type = text_type
    int_type = type(int(1))
    bigint_type = type(ZZ(1))
    list_type = type([1,2,3])
    dict_type = type({'a':1})
    real_type = type(table.lucky({'label':'11a1'})['sha_an'])
    bool_type = type(True)

    keys_and_types = {'label':  str_type,
                      'lmfdb_label':  str_type,
                      'conductor': bigint_type,
                      'bad_primes': list_type,
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
                      'trace_hash': type(ZZ(2**65).__int__()),
                      'num_int_pts': int_type,
                      'num_bad_primes': int_type,
                      'semistable': bool_type,
                      'optimality': int_type,
                      'manin_constant': int_type,
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
    no_cm_keys = ['2adic_log_level', '2adic_gens', '2adic_label']

    tor_gro_keys = ['tor_gro', 'tor_degs', 'tor_fields']
    tor_gro_bound = 400000

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
        if c['conductor'] > iwasawa_bound:
            expected_keys = expected_keys - iwasawa_keys
        if c['conductor'] > tor_gro_bound:
            expected_keys = expected_keys - tor_gro_keys

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
    if basepath is None:
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


def swap2curves(iso, test=True):
    """Swaps the Cremona number part of the Cremona labels of two curves in isogeny class iso.

    Here iso is the Cremona label of an isogeny class (no dot, no
    final number).

    Example: swap2curves('235470bb') will swap curves '235470bb1' and
    '235470bb2'.  The only columns affected are 'label' and 'number'.
    This uses the fact that the columns 'lmfdb_label' (and
    'lmfdb_number') are unchanged.

    """
    c1_old_label = iso+"1"
    c2_old_label = iso+"2"
    c1_data = curves.lucky({'label':c1_old_label}, projection=['lmfdb_label','aplist','anlist'])
    c2_data = curves.lucky({'label':c2_old_label}, projection=['lmfdb_label','aplist','anlist'])
    c1_lmfdb_label = c1_data['lmfdb_label']
    c2_lmfdb_label = c2_data['lmfdb_label']
    print("Retrieved curves with LMFDB labels {} (keys {}) and {} (keys {})".format(c1_lmfdb_label, c1_data.keys(), c2_lmfdb_label, c2_data.keys()))
    print("Old (Cremona) labels for these: {} and {}".format(c1_old_label, c2_old_label))
    c1_new_data = {'label': c2_old_label, 'number': 2}
    c2_new_data = {'label': c1_old_label, 'number': 1, 'aplist':c1_data['aplist'], 'anlist':c1_data['anlist']}
    print("New (Cremona) labels for these: {} and {}".format(c2_old_label, c1_old_label))

    # Now do the updates:

    print("Changing data for {} using {}".format(c1_lmfdb_label, c1_new_data))
    print("Changing data for {} using {}".format(c2_lmfdb_label, c2_new_data))
    if not test:
        curves.upsert({'lmfdb_label':c1_lmfdb_label},c1_new_data)
        curves.upsert({'lmfdb_label':c2_lmfdb_label},c2_new_data)
        print("changes made")
    else:
        print("Taking no further action")


an_global = {}
ap_global={}

def get_an_ap(iso, verbose):
    global an_global, ap_global
    if not iso in an_global:
        if verbose:
            print("fetching anlist and aplist for class {}".format(iso))
        an_ap = db.ec_curves.lucky({'iso':iso, 'number':1}, projection=['anlist', 'aplist'])
        an_global[iso] = an_ap['anlist']
        ap_global[iso] = an_ap['aplist']
    return an_global[iso], ap_global[iso]

def add_an(e, verbose=False):
    """Given a curve record, adds fields 'anlist' and 'aplist' if not there already.
    """
    if not 'anlist' in e:
        if verbose:
            print("adding anlist and aplist to record {}".format(e['label']))
        anlist, aplist = get_an_ap(e['iso'], verbose)
        e['anlist'] = anlist
        e['aplist'] = aplist
    return e

def fix_quad_twist(c):
    mqt = c['min_quad_twist']
    if mqt['label'] == '':
        if mqt['lmfdb_label'] == '':
            ainvs = [ZZ(a) for a in EllipticCurve(c['ainvs']).quadratic_twist(mqt['disc']).ainvs()]
            ct = curves.lucky({'ainvs':ainvs}, projection=['label', 'lmfdb_label'])
        else:
            ct = curves.lucky({'lmfdb_label':mqt['lmfdb_label']}, projection=['label', 'lmfdb_label'])
        if ct is None:
            print("failed to find curve (twist of {})".format(c['label']))
        else:
            mqt['label'] = ct['label']
            if mqt['lmfdb_label'] == '':
                mqt['lmfdb_label'] = ct['lmfdb_label']
    return c


# Rewrite function to add optimality and manin constant data.
#
# Run when the max conductor was 409999 and optimality was known for
# N<250000.
#
# For N<250000 optimality=1 when number=1, else 0, and we read the
# Manin constants from tmanin.N1-N2 files.
#
# For N>250000 we read the opt and mc values from opt_man.N1-N2 files.

# Function to read all the data before running the rewrite:

def read_opt_man_data():
    opt_man_dict = {}
    for N in range(50):
        fname = "/scratch/home/jcremona/ecdata/opt_man/opt_man.{}0000-{}9999".format(N,N)
        print("Reading from {}".format(fname))
        for line in open(fname):
            N, iso, num, ainvs, opt, mc = line.split()
            label = N+iso+num
            mc = int(mc)
            opt = int(opt)
            opt_man_dict[label] = {'optimality': opt, 'manin_constant': mc}
    return opt_man_dict

opt_man_data = {} # to keep pyflakes happy

# Run
#
# opt_man_data = read_opt_man_data()
#
# before using the following function for rewriting

def add_opt_man(c):
    lab = c['label']
    if lab in opt_man_data:
        c.update(opt_man_data[lab])
    else:
        print("No new optimality/Manin data for curve {}".format(lab))
    return c

def update_num_int_pts(rec):
    rec['num_int_pts'] = count_integral_points(rec)
    return rec

def fix_opt(iso, test=True):
    """Given an isogeny class of 2 or more curves, fixes the 'optimality'
    column, so that the first has value 1 and the others 0.  Use for
    certain special cases or after determining that curve #1 is
    optimal in some range.
    """
    for c in curves.search({'iso':iso}, projection=['label', 'number', 'optimality']):
        old_opt = c['optimality']
        label = c['label']
        if old_opt:
            c['optimality'] = new_opt = int(c['number']==1)

            # Now do the updates:

            print("Updating optimality for {} from {} to {}".format(label, old_opt, new_opt))
            if not test:
                curves.upsert({'label':label},c)
                print("changes made")
            else:
                print("Taking no further action")
        else:
            print("No action for curve {} whose optimality code is 0".format(label))

opt_fixes = ['260116a', '280916a', '285172a', '291664a', '300368a', '302516a',
             '306932a', '329492a', '343412a', '345808a', '367252a', '377012b',
             '384464d', '391892a', '401972a', '425168b', '446288a', '481652a']
