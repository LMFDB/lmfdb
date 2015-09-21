# -*- coding: utf-8 -*-
r""" Import data for elliptic curves over number fields.  Note: This code
can be run on all files in any order. Even if you rerun this code on
previously entered files, it should have no affect.  This code checks
if the entry exists, if so returns that and updates with new
information. If the entry does not exist then it creates it and
returns that.

Initial version (Arizona March 2014) based on import_ec_data.py: John Cremona
Revised continuously 2014-2015 by John Cremona: now uncludes download functions too.

The documents in the collection 'nfcurves' in the database
'elliptic_curves' have the following keys (* denotes a mandatory
field) and value types (with examples):

   - '_id': internal mogodb identifier

   - field_label  *   string          2.2.5.1
   - degree       *   int             2
   - signature    *   [int,int]       [2,0]
   - abs_disc     *   int             5

   - label              *     string (see below)
   - short_label        *     string
   - conductor_label    *     string
   - iso_label          *     string (letter code of isogeny class)
   - conductor_ideal    *     string
   - conductor_norm     *     int
   - number             *     int    (number of curve in isogeny class, from 1)
   - ainvs              *     list of 5 list of d lists of 2 ints
   - jinv               *     list of d lists of 2 STRINGS
   - cm                 *     either int (a negative discriminant, or 0) or '?'
   - q_curve            *     boolean (True, False)
   - base_change        *     list of labels of elliptic curve over Q
   - rank                     int
   - rank_bounds              list of 2 ints
   - analytic_rank            int
   - torsion_order            int
   - torsion_structure        list of 0, 1 or 2 ints
   - gens                     list of lists of 3 lists of d lists of 2 ints
   - torsion_gens             list of lists of 3 lists of d lists of strings
   - sha_an                   int
   - isogeny_matrix     *     list of list of ints (degrees)


   Each NFelt is a string concatenating rational coefficients with
   respect to a power basis for the number field, using the defining
   polynomial for the number field in the number_field database,
   separated by commas with no whitespace.

   label = “%s-%s” % (field_label, short_label)
   short_label = “%s.%s%s” % (conductor_label, iso_label, str(number))

To run the functions in this file, cd to the top-level lmfdb directory, start sage and use the command

   sage: %runfile lmfdb/ecnf/import_ecnf_data.py
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
from lmfdb.base import _init as init
from lmfdb.base import getDBConnection
from sage.rings.all import ZZ, QQ
from sage.databases.cremona import cremona_to_lmfdb

print "calling base._init()"
dbport = 37010
init(dbport, '')
print "getting connection"
conn = getDBConnection()
print "setting nfcurves"
nfcurves = conn.elliptic_curves.nfcurves
qcurves = conn.elliptic_curves.curves

# The following ensure_index command checks if there is an index on
# label, conductor, rank and torsion. If there is no index it creates
# one.  Need: once torsion structure is computed, we should have an
# index on that too.

# The following have not yet been thoroughly thought about!
nfcurves.ensure_index('label')
nfcurves.ensure_index('short_label')
nfcurves.ensure_index('conductor_norm')
nfcurves.ensure_index('rank')
nfcurves.ensure_index('torsion')
nfcurves.ensure_index('jinv')

print "finished indices"

# We have to look up number fields in the database from their labels,
# but only want to do this once for each label, so we will maintain a
# dict of label:field pairs:
nf_lookup_table = {}


def nf_lookup(label):
    r"""
    Returns a NumberField from its label, caching the result.
    """
    # print "Looking up number field with label %s" % label
    if label in nf_lookup_table:
        # print "We already have it: %s" % nf_lookup_table[label]
        return nf_lookup_table[label]
    # print "We do not have it yet, finding in database..."
    field = conn.numberfields.fields.find_one({'label': label})
    if not field:
        raise ValueError("Invalid field label: %s" % label)
    # print "Found it!"
    coeffs = [ZZ(c) for c in field['coeffs'].split(",")]
    K = NumberField(PolynomialRing(QQ, 'x')(coeffs), 'a')
    # print "The field with label %s is %s" % (label, K)
    nf_lookup_table[label] = K
    return K

# HNF of an ideal I in a quadratic field


def ideal_HNF(I):
    r"""
    Returns an HNF triple defining the ideal I in a quadratic field
    with integral basis [1,w].

    This is a list [a,b,d] such that [a,c+d*w] is a Z-basis of I, with
    a,d>0; c>=0; N = a*d = Norm(I); d|a and d|c; 0 <=c < a.
    """
    N = I.norm()
    a, c, b, d = I.pari_hnf().python().list()
    assert a > 0 and d > 0 and N == a * d and d.divides(a) and d.divides(b) and 0 <= c < a
    return [a, c, d]

# Label of an ideal I in a quadratic field: string formed from the
# Norm and HNF of the ideal


def ideal_label(I):
    r"""
    Returns the HNF-based label of an ideal I in a quadratic field
    with integral basis [1,w].  This is the string '[N,c,d]' where
    [a,c,d] is the HNF form of I and N=a*d=Norm(I).
    """
    a, c, d = ideal_HNF(I)
    return "[%s,%s,%s]" % (a * d, c, d)

# Reconstruct an ideal in a quadratic field from its label.


def ideal_from_label(K, lab):
    r"""Returns the ideal with label lab in the quadratic field K.
    """
    N, c, d = [ZZ(c) for c in lab[1:-1].split(",")]
    a = N // d
    return K.ideal(a, K([c, d]))


def parse_NFelt(K, s):
    r"""
    Returns an element of K defined by the string s.
    """
    return K([QQ(c) for c in s.split(",")])


def NFelt(a):
    r"""
    Returns an NFelt string encoding the element a (in a number field K).
    """
    return ",".join([str(c) for c in list(a)])


def QorZ_list(a):
    r"""
    Return the list representation of the rational number.
    """
    return [int(a.numerator()), int(a.denominator())]


def K_list(a):
    r"""
    Return the list representation of the number field element.
    """
    # return [QorZ_list(c) for c in list(a)]  # old: [num,den]
    return [str(c) for c in list(a)]         # new: "num/den"


def NFelt_list(a):
    r"""
    Return the list representation of the NFelt string.
    """
    return [QorZ_list(QQ(c)) for c in a.split(",")]


def parse_point(E, s):
    r"""
    Returns a point on E defined by the string s.
    """
    K = E.base_field()
    cc = s[1:-1].split(":")
    return E([parse_NFelt(c) for c in cc])


def point_string(P):
    r"""Return a string representation of a point on an elliptic curve
    """
    return "[" + ":".join([NFelt(c) for c in list(P)]) + "]"


def point_string_to_list(s):
    r"""Return a list representation of a point string
    """
    return s[1:-1].split(":")


def point_list(P):
    r"""Return a list representation of a point on an elliptic curve
    """
    return [K_list(c) for c in list(P)]


def field_data(s):
    r"""
    Returns full field data from field label.
    """
    deg, r1, abs_disc, n = [int(c) for c in s.split(".")]
    sig = [r1, (deg - r1) // 2]
    return [s, deg, sig, abs_disc]


@cached_function
def get_cm_list(K):
    return cm_j_invariants_and_orders(K)


def get_cm(j):
    r"""
    Returns the CM discriminant for this j-invariant, or 0
    """
    if not j.is_integral():
        return 0
    for d, f, j1 in get_cm_list(j.parent()):
        if j == j1:
            return int(d * f * f)
    return 0

whitespace = re.compile(r'\s+')


def split(line):
    return whitespace.split(line.strip())


def curves(line):
    r""" Parses one line from a curves file.  Returns the label and a dict
    containing fields with keys 'field_label', 'degree', 'signature',
    'abs_disc', 'label', 'short_label', conductor_label',
    'conductor_ideal', 'conductor_norm', 'iso_label', 'number',
    'ainvs', 'jinv', 'cm', 'q_curve', 'base_change',
    'torsion_order', 'torsion_structure', 'torsion_gens'.

    Input line fields (13):

    field_label conductor_label iso_label number conductor_ideal conductor_norm a1 a2 a3 a4 a6 cm base_change

    Sample input line:

    2.0.4.1 [65,18,1] a 1 [65,18,1] 65 1,1 1,1 0,1 -1,1 -1,0 0 0
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) != 13:
        print "line %s does not have 13 fields, skipping" % line
    field_label = data[0]       # string
    conductor_label = data[1]   # string
    iso_label = data[2]         # string
    number = int(data[3])       # int
    short_class_label = "%s-%s" % (conductor_label, iso_label)
    short_label = "%s%s" % (short_class_label, str(number))
    class_label = "%s-%s" % (field_label, short_class_label)
    label = "%s-%s" % (field_label, short_label)

    conductor_ideal = data[4]     # string
    conductor_norm = int(data[5])  # int
    ainvs = data[6:11]            # list of 5 NFelt strings
    cm = data[11]                 # int or '?'
    if cm != '?':
        cm = int(cm)
    q_curve = (data[12] == '1')   # bool

    # Create the field and curve to compute the j-invariant:
    dummy, deg, sig, abs_disc = field_data(field_label)
    K = nf_lookup(field_label)
    ainvsK = [parse_NFelt(K, ai) for ai in ainvs]  # list of K-elements
    ainvs = [[str(c) for c in ai] for ai in ainvsK]
    E = EllipticCurve(ainvsK)
    j = E.j_invariant()
    jinv = K_list(j)
    if cm == '?':
        cm = get_cm(j)
        if cm:
            print "cm=%s for j=%s" % (cm, j)

    # Here we should check that the conductor of the constructed curve
    # agrees with the input conductor.  We just check the norm.
    if E.conductor().norm() == conductor_norm:
        pass
        # print "Conductor norms agree: %s" % conductor_norm
    else:
        raise RuntimeError("Wrong conductor for input line %s" % line)

    # get torsion order, structure and generators:
    # print("E = %s over %s" % (ainvsK,K))
    torgroup = E.torsion_subgroup()
    # print("torsion = %s" % torgroup)
    ntors = int(torgroup.order())
    torstruct = [int(n) for n in list(torgroup.invariants())]
    torgens = [point_list(P.element()) for P in torgroup.gens()]

    # get label of elliptic curve over Q for base_change cases (a
    # subset of Q-curves)

    if q_curve:
        # print "%s is a Q-curve, testing for base-change..." % label
        E1list = E.descend_to(QQ)
        if len(E1list):
            base_change = [cremona_to_lmfdb(E1.label()) for E1 in E1list]
            print "%s is base change of %s" % (label, base_change)
        else:
            base_change = []
            print "%s is a Q-curve, but not base-change..." % label
    else:
        base_change = []

    return label, {
        'field_label': field_label,
        'degree': deg,
        'signature': sig,
        'abs_disc': abs_disc,
        'class_label': class_label,
        'short_class_label': short_class_label,
        'label': label,
        'short_label': short_label,
        'conductor_label': conductor_label,
        'conductor_ideal': conductor_ideal,
        'conductor_norm': conductor_norm,
        'iso_label': iso_label,
        'number': number,
        'ainvs': ainvs,
        'jinv': jinv,
        'cm': cm,
        'q_curve': q_curve,
        'base_change': base_change,
        'torsion_order': ntors,
        'torsion_structure': torstruct,
        'torsion_gens': torgens,
    }


def curve_data(line):
    r""" Parses one line from a curve_data file.  Returns the label and a dict
    containing fields with keys 'label', 'rank', 'rank_bounds',
    'analytic_rank', 'gens', 'sha_an'.

    Input line fields (9+n where n is the 8th); all but the first 4
    are optional and if not known should contain"?" except that the 8th
    should contain 0.

    field_label conductor_label iso_label number rank rank_bounds analytic_rank ngens gen_1 ... gen_n sha_an

    Sample input line:

    2.0.4.1 [65,18,1] a 1 0 ? 0 0 ?
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) < 9:
        print "line %s does not have 9 fields (excluding gens), skipping" % line
    ngens = int(data[7])
    if len(data) != 9 + ngens:
        print "line %s does not have 9 fields (excluding gens), skipping" % line
    field_label = data[0]       # string
    conductor_label = data[1]   # string
    iso_label = data[2]         # string
    number = int(data[3])       # int
    short_label = "%s-%s%s" % (conductor_label, iso_label, str(number))
    label = "%s-%s" % (field_label, short_label)

    edata = {'label': label}
    r = data[4]
    if r != "?":
        edata['rank'] = int(r)
    rb = data[5]
    if rb != "?":
        edata['rank_bounds'] = [int(c) for c in rb[1:-1].split(",")]
    ra = data[6]
    if ra != "?":
        edata['analytic_rank'] = int(ra)
    ngens = int(data[7])
    edata['gens'] = [point_string_to_list(g) for g in data[8:8 + ngens]]
    sha = data[8 + ngens]
    if sha != "?":
        edata['sha_an'] = int(sha)
    return label, edata


def isoclass(line):
    r""" Parses one line from an isovlass file.  Returns the label and a dict
    containing fields with keys .

    Input line fields (5); the first 4 are the standard labels and the
    5th the isogeny matrix as a list of lists of ints.

    field_label conductor_label iso_label number isogeny_matrix

    Sample input line:

    2.0.4.1 [65,18,1] a 1 [[1,6,3,18,9,2],[6,1,2,3,6,3],[3,2,1,6,3,6],[18,3,6,1,2,9],[9,6,3,2,1,18],[2,3,6,9,18,1]]
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) < 5:
        print "isoclass line %s does not have 5 fields (excluding gens), skipping" % line
    field_label = data[0]       # string
    conductor_label = data[1]   # string
    iso_label = data[2]         # string
    number = int(data[3])       # int
    short_label = "%s-%s%s" % (conductor_label, iso_label, str(number))
    label = "%s-%s" % (field_label, short_label)

    mat = data[4]
    mat = [[int(a) for a in r.split(",")] for r in mat[2:-2].split("],[")]

    edata = {'label': label, 'isogeny_matrix': mat}
    return label, edata

filename_base_list = ['curves', 'curve_data']

#


def upload_to_db(base_path, filename_suffix):
    curves_filename = 'curves.%s' % (filename_suffix)
    curve_data_filename = 'curve_data.%s' % (filename_suffix)
    isoclass_filename = 'isoclass.%s' % (filename_suffix)
    file_list = [curves_filename, curve_data_filename, isoclass_filename]
#    file_list = [isoclass_filename]
#    file_list = [curves_filename]
#    file_list = [curve_data_filename]

    data_to_insert = {}  # will hold all the data to be inserted

    for f in file_list:
        try:
            h = open(os.path.join(base_path, f))
            print "opened %s" % os.path.join(base_path, f)
        except IOError:
            print "No file %s exists" % os.path.join(base_path, f)
            continue  # in case not all prefixes exist

        parse = globals()[f[:f.find('.')]]

        t = time.time()
        count = 0
        print "Starting to read lines from file %s" % f
        for line in h.readlines():
            # if count==10: break # for testing
            label, data = parse(line)
            if count % 100 == 0:
                print "read %s from %s" % (label, f)
            count += 1
            if label not in data_to_insert:
                data_to_insert[label] = {'label': label}
            curve = data_to_insert[label]
            for key in data:
                if key in curve:
                    if curve[key] != data[key]:
                        raise RuntimeError("Inconsistent data for %s:\ncurve=%s\ndata=%s\nkey %s differs!" % (label, curve, data, key))
                else:
                    curve[key] = data[key]
        print "finished reading %s lines from file %s" % (count, f)

    vals = data_to_insert.values()
    count = 0
    for val in vals:
        # print val
        nfcurves.update({'label': val['label']}, {"$set": val}, upsert=True)
        count += 1
        if count % 100 == 0:
            print "inserted %s" % (val['label'])

#
#
# Code to download data from the database, (re)creating file curves.*,
# curve_data.*, isoclass.*
#
#


def make_curves_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from a curves file.

    Output line fields (13):

    field_label conductor_label iso_label number conductor_ideal conductor_norm a1 a2 a3 a4 a6 cm base_change

    Sample output line:

    2.0.4.1 [65,18,1] a 1 [65,18,1] 65 1,1 1,1 0,1 -1,1 -1,0 0 0
    """
    output_fields = [ec['field_label'],
                     ec['conductor_label'],
                     ec['iso_label'],
                     str(ec['number']),
                     ec['conductor_ideal'],
                     str(ec['conductor_norm'])
                     ] + [",".join(t) for t in ec['ainvs']
                          ] + [str(ec['cm']), str(int(len(ec['base_change']) > 0))]
    return " ".join(output_fields)


def make_curve_data_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from a curve_data file.

    Output line fields (9+n where n is the 8th); all but the first 4
    are optional and if not known should contain"?" except that the 8th
    should contain 0.

    field_label conductor_label iso_label number rank rank_bounds analytic_rank ngens gen_1 ... gen_n sha_an

    Sample output line:

    2.0.4.1 [65,18,1] a 1 0 ? 0 0 ?
    """
    rk = '?'
    if 'rank' in ec:
        rk = str(ec['rank'])
    rk_bds = '?'
    if 'rank_bounds' in ec:
        rk_bds = str(ec['rank_bounds']).replace(" ", "")
    an_rk = '?'
    if 'analytic_rank' in ec:
        an_rk = str(ec['analytic_rank'])
    ngens = '0'
    gens_str = []
    if 'gens' in ec:
        gens_str = ["[" + ":".join([c for c in P]) + "]" for P in ec['gens']]
        ngens = str(len(gens_str))
    sha = '?'
    if 'sha_an' in ec:
        sha = str(int(ec['sha_an']))

    output_fields = [ec['field_label'],
                     ec['conductor_label'],
                     ec['iso_label'],
                     str(ec['number']),
                     rk, rk_bds, an_rk,
                     ngens] + gens_str + [sha]
    return " ".join(output_fields)


def make_isoclass_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from an isoclass file.

    Output line fields (15):

    field_label conductor_label iso_label number isogeny_matrix

    Sample output line:

    2.0.4.1 [65,18,1] a 1 [[1,6,3,18,9,2],[6,1,2,3,6,3],[3,2,1,6,3,6],[18,3,6,1,2,9],[9,6,3,2,1,18],[2,3,6,9,18,1]]
    """
    mat = ''
    if 'isogeny_matrix' in ec:
        mat = str(ec['isogeny_matrix']).replace(' ', '')
    else:
        print("Making isogeny matrix for class %s" % ec['label'])
        from lmfdb.ecnf.isog_class import permute_mat
        from lmfdb.ecnf.WebEllipticCurve import FIELD
        K = FIELD(ec['field_label'])
        curves = nfcurves.find({'field_label': ec['field_label'],
                                'conductor_label': ec['conductor_label'],
                                'iso_label': ec['iso_label']}).sort('number')
        Elist = [EllipticCurve([K.parse_NFelt(x) for x in c['ainvs']]) for c in curves]
        cl = Elist[0].isogeny_class()
        perm = dict([(i, cl.index(E)) for i, E in enumerate(Elist)])
        mat = permute_mat(cl.matrix(), perm, True)
        n = len(Elist)
        mat = str([list(ri) for ri in mat.rows()]).replace(" ", "")

    output_fields = [ec['field_label'],
                     ec['conductor_label'],
                     ec['iso_label'],
                     str(ec['number']),
                     mat]
    return " ".join(output_fields)


def download_curve_data(field_label, base_path, min_norm=0, max_norm=None):
    r""" Extract curve data for the given field for curves with conductor
    norm in the given range, and write to output files in the same
    format as in the curves/curve_data/isoclass input files.
    """
    query = {}
    query['field_label'] = field_label
    query['conductor_norm'] = {'$gte': int(min_norm)}
    if max_norm:
        query['conductor_norm']['$lte'] = int(max_norm)
    else:
        max_norm = 'infinity'
    cursor = nfcurves.find(query)
    ASC = pymongo.ASCENDING
    res = cursor.sort([('conductor_norm', ASC), ('conductor_label', ASC), ('iso_label', ASC), ('number', ASC)])

    file = {}
    prefixes = ['curves', 'curve_data', 'isoclass']
    suffix = ''.join([".", field_label, ".", str(min_norm), "-", str(max_norm)])
    for prefix in prefixes:
        filename = os.path.join(base_path, ''.join([prefix, suffix]))
        file[prefix] = open(filename, 'w')

    for ec in res:
        file['curves'].write(make_curves_line(ec) + "\n")
        file['curve_data'].write(make_curve_data_line(ec) + "\n")
        if ec['number'] == 1:
            file['isoclass'].write(make_isoclass_line(ec) + "\n")

    for prefix in prefixes:
        file[prefix].close()
