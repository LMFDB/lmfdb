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
field) and value types (with examples).  Here the base field is
K=Q(w) of degree d.

 An NFelt-string is a string representing an element of K as a
 comma-separated list of rational coefficients with respect to the
 power basis.

 An ideal-string is a string representing [N,a,alpha] defining an
 ideal of norm N, minimal positive integer a and second generator
 alpha, expressed as a polynomial in w.

 A point-string is a string of the form [X,Y,Z] where each of X, Y, Z
 is an NFelt surrounded by "[","]".  For example (degree 2):
 '[[1/2,2],[3/4,5/6],[1,0]]'.

 label = “%s-%s” % (field_label, short_label)
 short_label = “%s.%s%s” % (conductor_label, iso_label, str(number))

   - '_id': internal mogodb identifier

   - field_label  *   string          2.2.5.1
   - degree       *   int             2
   - signature    *   [int,int]       [2,0]
   - abs_disc     *   int             5

   - label              *     string (see below)
   - short_label        *     string
   - class_label        *     string
   - short_class_label  *     string
   - conductor_label    *     string
   - iso_label          *     string (letter code of isogeny class)
   - iso_nlabel         *     int (numerical code of isogeny class)
   - conductor_ideal    *     ideal-string
   - conductor_norm     *     int
   - number             *     int    (number of curve in isogeny class, from 1)
   - ainvs              *     string joining 5 NFelt-strings by ";"
   - jinv               *     NFelt-string
   - cm                 *     int (a negative discriminant, or 0)
   - q_curve            *     boolean (True, False)
   - base_change        *     list of labels of elliptic curve over Q
   - rank                     int
   - rank_bounds              list of 2 ints
   - analytic_rank            int
   - torsion_order            int
   - torsion_structure        list of 0, 1 or 2 ints
   - gens                     list of point-strings (see below)
   - torsion_gens       *     list of point-strings (see below)
   - sha_an                   int
   - isogeny_matrix     *     list of list of ints (degrees)
   - non_surjective_primes    list of ints
   - galois_images            list of strings

   - equation           *     string
   - local_data         *     list of dicts (one per bad prime)
   - non_min_p          *     list of strings (one per nonminimal prime)
   - minD               *     ideal-string (minimal discriminant ideal)
   - heights                  list of floats (one per gen)
   - reg                      float


To run the functions in this file, cd to the top-level lmfdb
directory, start sage and use the command

   sage: %runfile lmfdb/ecnf/import_ecnf_data.py
"""

import os.path
import re
import os
import pymongo
import pprint
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex
from sage.all import NumberField, PolynomialRing, EllipticCurve, ZZ, QQ, Set
from sage.databases.cremona import cremona_to_lmfdb
from lmfdb.ecnf.ecnf_stats import field_data
from lmfdb.ecnf.WebEllipticCurve import FIELD, ideal_from_string, ideal_to_string, parse_ainvs, parse_point
from scripts.ecnf.import_utils import make_curves_line, make_curve_data_line, split, numerify_iso_label, NFelt, get_cm, point_string

print "getting connection"
C= getDBConnection()

print "authenticating on the elliptic_curves database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['elliptic_curves'].authenticate(username, password)
print "setting nfcurves"
oldnfcurves = C.elliptic_curves.nfcurves.old
nfcurves = C.elliptic_curves.nfcurves
qcurves = C.elliptic_curves.curves
C['admin'].authenticate('lmfdb', 'lmfdb') # read-only


# We have to look up number fields in the database from their labels,
# but only want to do this once for each label, so we will maintain a
# dict of label:field pairs:
nf_lookup_table = {}
special_names = {'2.0.4.1': 'i',
                 '2.2.5.1': 'phi',
                 '4.0.125.1': 'zeta5',
                 }

def nf_lookup(label):
    r"""
    Returns a NumberField from its label, caching the result.
    """
    global nf_lookup_table, special_names
    #print "Looking up number field with label %s" % label
    if label in nf_lookup_table:
        #print "We already have it: %s" % nf_lookup_table[label]
        return nf_lookup_table[label]
    #print "We do not have it yet, finding in database..."
    field = C.numberfields.fields.find_one({'label': label})
    if not field:
        raise ValueError("Invalid field label: %s" % label)
    #print "Found it!"
    coeffs = [ZZ(c) for c in field['coeffs'].split(",")]
    gen_name = special_names.get(label,'a')
    K = NumberField(PolynomialRing(QQ, 'x')(coeffs), gen_name)
    #print "The field with label %s is %s" % (label, K)
    nf_lookup_table[label] = K
    return K

from lmfdb.nfutils.psort import ideal_label

the_labels = {}

def convert_ideal_label(K, lab):
    """An ideal label of the form N.c.d is converted to N.i.  Here N.c.d
    defines the ideal I with Z-basis [a, c+d*w] where w is the standard
    generator of K, N=N(I) and a=N/d.  The standard label is N.i where I is the i'th ideal of norm N in the standard ordering.

    NB Only intended for use in coverting IQF labels!  To get the standard label from any ideal I just use ideal_label(I).
    """
    global the_labels
    if K in the_labels:
        if lab in the_labels[K]:
            return the_labels[K][lab]
        else:
            pass
    else:
        the_labels[K] = {}

    comps = lab.split(".")
    # test for labels which do not need any conversion
    if len(comps)==2:
        return lab
    assert len(comps)==3
    N, c, d = [int(x) for x in comps]
    a = N//d
    I = K.ideal(a, c+d*K.gen())
    newlab = ideal_label(I)
    #print("Ideal label converted from {} to {} over {}".format(lab,newlab,K))
    the_labels[K][lab] = newlab
    return newlab

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
    cursor = C.elliptic_curves.nfcurves.find(query)
    ASC = pymongo.ASCENDING
    res = cursor.sort([('conductor_norm', ASC), ('conductor_label', ASC), ('iso_nlabel', ASC), ('number', ASC)])

    file = {}
    prefixes = ['curves', 'curve_data', 'isoclass']
    prefixes = ['curve_data']
    suffix = ''.join([".", field_label, ".", str(min_norm), "-", str(max_norm)])
    for prefix in prefixes:
        filename = os.path.join(base_path, ''.join([prefix, suffix]))
        file[prefix] = open(filename, 'w')

    for ec in res:
        if 'curves' in prefixes:
            file['curves'].write(make_curves_line(ec) + "\n")
        if 'curve_data' in prefixes:
            file['curve_data'].write(make_curve_data_line(ec) + "\n")
        if 'isoclass' in prefixes:
            if ec['number'] == 1:
                file['isoclass'].write(make_isoclass_line(ec) + "\n")

    for prefix in prefixes:
        file[prefix].close()


def convert_conductor_label(field_label, label):
    """If the field is imaginary quadratic, calls convert_ideal_label, otherwise just return label unchanged.
    """
    if field_label.split(".")[:2] != ['2','0']:
        return label
    K = nf_lookup(field_label)
    new_label = convert_ideal_label(K,label)
    #print("Converting conductor label from {} to {}".format(label, new_label))
    return new_label


def curves(line, verbose=False):
    r""" Parses one line from a curves file.  Returns the label and a dict
    containing fields with keys 'field_label', 'degree', 'signature',
    'abs_disc', 'label', 'short_label', conductor_label',
    'conductor_ideal', 'conductor_norm', 'iso_label', 'iso_nlabel',
    'number', 'ainvs', 'jinv', 'cm', 'q_curve', 'base_change',
    'torsion_order', 'torsion_structure', 'torsion_gens'; and (added
    May 2016): 'equation', 'local_data', 'non_min_p', 'minD'

    Input line fields (13):

    field_label conductor_label iso_label number conductor_ideal conductor_norm a1 a2 a3 a4 a6 cm base_change

    Sample input line:

    2.0.4.1 65.18.1 a 1 [65,18,1] 65 1,1 1,1 0,1 -1,1 -1,0 0 0
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) != 13:
        print "line %s does not have 13 fields, skipping" % line
    field_label = data[0]       # string
    IQF_flag = field_label.split(".")[:2] == ['2','0']
    K = nf_lookup(field_label) if IQF_flag else None
    conductor_label = data[1]   # string
    # convert label (does nothing except for imaginary quadratic)
    conductor_label = convert_conductor_label(field_label, conductor_label)
    iso_label = data[2]         # string
    iso_nlabel = numerify_iso_label(iso_label)         # int
    number = int(data[3])       # int
    short_class_label = "%s-%s" % (conductor_label, iso_label)
    short_label = "%s%s" % (short_class_label, str(number))
    class_label = "%s-%s" % (field_label, short_class_label)
    label = "%s-%s" % (field_label, short_label)

    conductor_ideal = data[4]     # string
    conductor_norm = int(data[5]) # int
    ainvs = ";".join(data[6:11])  # one string joining 5 NFelt strings
    cm = data[11]                 # int or '?'
    if cm != '?':
        cm = int(cm)

    # Create the field and curve to compute the j-invariant:
    dummy, deg, sig, abs_disc = field_data(field_label)
    K = nf_lookup(field_label)
    #print("Field %s created, gen_name = %s" % (field_label,str(K.gen())))
    ainvsK = parse_ainvs(K,ainvs)  # list of K-elements
    E = EllipticCurve(ainvsK)
    #print("{} created with disc = {}, N(disc)={}".format(E,K.ideal(E.discriminant()).factor(),E.discriminant().norm().factor()))
    j = E.j_invariant()
    jinv = NFelt(j)
    if cm == '?':
        cm = get_cm(j)
        if cm:
            print "cm=%s for j=%s" % (cm, j)

    q_curve = data[12]   # 0, 1 or ?.  If unknown we'll determine this below.
    if q_curve in ['0','1']: # already set -- easy
        q_curve = bool(int(q_curve))
    else:
        try:
            q_curve = is_Q_curve(E)
        except NotImplementedError:
            q_curve = '?'

    # Here we should check that the conductor of the constructed curve
    # agrees with the input conductor.
    N = ideal_from_string(K,conductor_ideal)
    NE = E.conductor()
    if N=="wrong" or N!=NE:
        print("Wrong conductor ideal {} for label {}, using actual conductor {} instead".format(conductor_ideal,label,NE))
        conductor_ideal = ideal_to_string(NE)
        N = NE

    # get torsion order, structure and generators:
    torgroup = E.torsion_subgroup()
    ntors = int(torgroup.order())
    torstruct = [int(n) for n in list(torgroup.invariants())]
    torgens = [point_string(P.element()) for P in torgroup.gens()]

    # get label of elliptic curve over Q for base_change cases (a
    # subset of Q-curves)

    if True:  # q_curve: now we have not precomputed Q-curve status
              # but still want to test for base change!
        if verbose:
            print("testing {} for base-change...".format(label))
        E1list = E.descend_to(QQ)
        if len(E1list):
            base_change = [cremona_to_lmfdb(E1.label()) for E1 in E1list]
            if verbose:
                print "%s is base change of %s" % (label, base_change)
        else:
            base_change = []
            # print "%s is a Q-curve, but not base-change..." % label
    else:
        base_change = []

    # NB if this is not a global minimal model then local_data may
    # include a prime at which we have good reduction.  This causes no
    # problems except that the bad_reduction_type is then None which
    # cannot be converted to an integer.  The bad reduction types are
    # coded as (Sage) integers in {-1,0,1}.
    local_data = [{'p': ideal_to_string(ld.prime()),
                   'normp': str(ld.prime().norm()),
                   'ord_cond':int(ld.conductor_valuation()),
                   'ord_disc':int(ld.discriminant_valuation()),
                   'ord_den_j':int(max(0,-(E.j_invariant().valuation(ld.prime())))),
                   'red':None if ld.bad_reduction_type()==None else int(ld.bad_reduction_type()),
                   'kod':web_latex(ld.kodaira_symbol()).replace('$',''),
                   'cp':int(ld.tamagawa_number())}
                  for ld in E.local_data()]

    non_minimal_primes = [ideal_to_string(P) for P in E.non_minimal_primes()]
    minD = ideal_to_string(E.minimal_discriminant_ideal())

    edata = {
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
        'iso_nlabel': iso_nlabel,
        'number': number,
        'ainvs': ainvs,
        'jinv': jinv,
        'cm': cm,
        'q_curve': q_curve,
        'base_change': base_change,
        'torsion_order': ntors,
        'torsion_structure': torstruct,
        'torsion_gens': torgens,
        'equation': web_latex(E),
        'local_data': local_data,
        'minD': minD,
        'non_min_p': non_minimal_primes,
    }

    return label, edata





def add_heights(data, verbose = False):
    r""" If data holds the data fields for a curve this returns the same
    with the heights of the points included as a new field with key
    'heights'.  It is more convenient to do this separately than while
    parsing the input files since curves() knows tha a-invariants but
    not the gens and curve_data() vice versa.
    """
    if 'heights' in data and 'reg' in data:
        return data
    ngens = data.get('ngens', 0)
    if ngens == 0:
        data['heights'] = []
        data['reg'] = float(1)
        return data
    # Now there is work to do
    K = nf_lookup(data['field_label'])
    if 'ainvs' in data:
        ainvs = data['ainvs']
    else:
        ainvs = nfcurves.find_one({'label':data['label']})['ainvs']
    ainvsK = parse_ainvs(K, ainvs)  # list of K-elements
    E = EllipticCurve(ainvsK)
    gens = [E(parse_point(K,x)) for x in data['gens']]
    data['heights'] = [float(P.height()) for P in gens]
    data['reg'] = float(E.regulator_of_points(gens))
    if verbose:
        print("added heights %s and regulator %s to %s" % (data['heights'],data['reg'], data['label']))
    return data

def isoclass(line):
    r""" Parses one line from an isoclass file.  Returns the label and a dict
    containing fields with keys .

    Input line fields (5); the first 4 are the standard labels and the
    5th the isogeny matrix as a list of lists of ints.

    field_label conductor_label iso_label number isogeny_matrix

    Sample input line:

    2.0.4.1 65.18.1 a 1 [[1,6,3,18,9,2],[6,1,2,3,6,3],[3,2,1,6,3,6],[18,3,6,1,2,9],[9,6,3,2,1,18],[2,3,6,9,18,1]]
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) < 5:
        print "isoclass line %s does not have 5 fields (excluding gens), skipping" % line
    field_label = data[0]       # string
    conductor_label = data[1]   # string
    # convert label (does nothing except for imaginary quadratic)
    conductor_label = convert_conductor_label(field_label, conductor_label)
    iso_label = data[2]         # string
    number = int(data[3])       # int
    short_label = "%s-%s%s" % (conductor_label, iso_label, str(number))
    label = "%s-%s" % (field_label, short_label)

    mat = data[4]
    mat = [[int(a) for a in r.split(",")] for r in mat[2:-2].split("],[")]
    isogeny_degrees = dict([[n+1,sorted(list(set(row)))] for n,row in enumerate(mat)])

    edata = {'label': [field_label,conductor_label,iso_label],
             'isogeny_matrix': mat,
             'isogeny_degrees': isogeny_degrees}
    return label, edata

def read1isogmats(base_path, filename_suffix):
    r""" Returns a dictionary whose keys are labels of individual curves,
    and whose values are the isogeny_matrix and isogeny_degrees for
    each curve in the class, together with the class size and the
    maximal degree in the class.

    This function reads a single isoclass file.
    """
    isoclass_filename = 'isoclass.%s' % (filename_suffix)
    h = open(os.path.join(base_path, isoclass_filename))
    print("Opened {}".format(os.path.join(base_path, isoclass_filename)))
    data = {}
    for line in h.readlines():
        label, data1 = isoclass(line)
        class_label = "-".join(data1['label'][:3])
        isogmat = data1['isogeny_matrix']
        # maxdeg is the maximum degree of a cyclic isogeny in the
        # class, which uniquely determines the isogeny graph (over Q)
        maxdeg = max(max(r) for r in isogmat)
        allisogdegs = data1['isogeny_degrees']
        ncurves = len(allisogdegs)
        for n in range(ncurves):
            isogdegs = allisogdegs[n+1]
            label = class_label+str(n+1)
            data[label] = {'isogeny_degrees': isogdegs,
                           'class_size': ncurves,
                           'class_deg': maxdeg}
            if n==0:
                #print("adding isogmat = {} to {}".format(isogmat,label))
                data[label]['isogeny_matrix'] = isogmat

    return data

def split_galois_image_code(s):
    """Each code starts with a prime (1-3 digits but we allow for more)
    followed by an image code or that prime.  This function returns
    two substrings, the prefix number and the rest.
    """
    p = re.findall(r'\d+', s)[0]
    return p, s[len(p):]

def galrep(line):
    r""" Parses one line from a galrep file.  Returns the label and a
    dict containing two fields: 'non_surjective_primes', a list of
    primes p for which the Galois representation modulo p is not
    surjective (cut off at p=37 for CM curves for which this would
    otherwise contain all primes), 'galois_images', a list of strings
    encoding the image when not surjective, following Sutherland's
    coding scheme for subgroups of GL(2,p).  Note that these codes
    start with a 1 or 2 digit prime followed a letter in
    ['B','C','N','S'].

    Input line fields (4+); the first is a standard label of the form
    field-conductor-an where 'a' is the isogeny class (one or more
    letters), 'n' is the number ofe the curve in the class (from 1)
    and any remaining ones are galrep codes.

    label codes

    Sample input line (field='2.0.3.1', conductor='10000.0.100', class='a', number=1)

    2.0.3.1-10000.0.100-a1 2B 3B[2]

    """
    data = split(line)
    label = data[0] # single string
    field_label, conductor_label, c_label = data[0].split("-")
    iso_label = ''.join([c for c in c_label if c.isalpha()])
    number = ''.join([c for c in c_label if c.isdigit()])
    assert iso_label+number==c_label
    conductor_label = convert_conductor_label(field_label, conductor_label)
    print("Converting conductor label from {} to {}".format(data[0].split("-")[1], conductor_label))
    short_label = "%s-%s%s" % (conductor_label, iso_label, str(number))
    label = "%s-%s" % (field_label, short_label)
    image_codes = data[1:]
#    pr = [ int(s[:2]) if s[1].isdigit() else int(s[:1]) for s in image_codes]
    pr = [ int(split_galois_image_code(s)[0]) for s in image_codes]
    return label, {
        'non_surjective_primes': pr,
        'galois_images': image_codes,
    }




def readgalreps(base_path, filename):
    h = open(os.path.join(base_path, filename))
    print("opened {}".format(os.path.join(base_path, filename)))
    dat = {}
    for L in h.readlines():
        lab, dat1 = galrep(L)
        dat[lab] = dat1
    return dat

# Before using the following, define galrepdat using a command such as
#
# galrepdat=readgalreps("/home/jec/ecnf-data/", "nfcurves_galois_images.txt")
#
# then use rewrite like this:
# %runfile data_mgt/utilities/rewrite.py
# rewrite_collection(C.elliptic_curves, "nfcurves", "nfcurves.new", add_galrep_data_to_nfcurve)
#
galrepdat = {} # for pyflakes

def add_galrep_data_to_nfcurve(cu):
    if cu['label'] in galrepdat:
        cu.update(galrepdat[cu['label']])
    return cu

filename_base_list = ['curves', 'curve_data']

#

def upload_to_db(base_path, filename_suffix, insert=True, test=True):
    r""" Uses insert_one() if insert=True, which is faster but will fail if
    the label is already in the database; otherwise uses update_one()
    with upsert=True
    """
    curves_filename = 'curves.%s' % (filename_suffix)
    curve_data_filename = 'curve_data.%s' % (filename_suffix)
    isoclass_filename = 'isoclass.%s' % (filename_suffix)
    galrep_filename = 'galrep.%s' % (filename_suffix)
    file_list = [curves_filename, curve_data_filename, isoclass_filename, galrep_filename]
#    file_list = [isoclass_filename]
#    file_list = [curves_filename]
#    file_list = [curve_data_filename]
#    file_list = [galrep_filename]

    data_to_insert = {}  # will hold all the data to be inserted

    for f in file_list:
        if f==isoclass_filename: # dealt with differently
            continue
        try:
            h = open(os.path.join(base_path, f))
            print "opened %s" % os.path.join(base_path, f)
        except IOError:
            print "No file %s exists" % os.path.join(base_path, f)
            continue  # in case not all prefixes exist

        parse = globals()[f[:f.find('.')]]

        count = 0
        print "Starting to read lines from file %s" % f
        for line in h.readlines():
            #if count==20: break # for testing
            label, data = parse(line)
            if count % 100 == 0:
                print "read %s from %s (%s so far)" % (label, f, count)
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
    print("adding heights of gens")
    for val in vals:
        val = add_heights(val)

    if isoclass_filename in file_list: # code added March 2017, not yet tested
        print("processing isogeny matrices")
        isogmats = read1isogmats(base_path, filename_suffix)
        for val in vals:
            lab = val['label']
            #print("adding isog data for {}".format(lab))
            if lab in isogmats:
                val.update(isogmats[lab])
            else:
                print("error: label {} not in isogmats!".format(lab))

    if insert:
        if test:
            print("(not) inserting all data")
            #nfcurves.insert_many(vals)
            print("First 10 vals:")
            for v in vals[:10]:
                pprint.pprint(v)
        else:
            print("inserting all data ({} items)".format(len(vals)))
            nfcurves.insert_many(vals)
    else:
        count = 0
        print("inserting data one curve at a time...")
        for val in vals:
            #print val
            nfcurves.update_one({'label': val['label']}, {"$set": val}, upsert=True)
            count += 1
            if count % 100 == 0:
                print "inserted %s" % (val['label'])

#
#
# Code to download data from the database, (re)creating file curves.*,
# curve_data.*, isoclass.*
#
#



def make_isoclass_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from an isoclass file.

    Output line fields (15):

    field_label conductor_label iso_label number isogeny_matrix

    Sample output line:

    2.0.4.1 65.18.1 a 1 [[1,6,3,18,9,2],[6,1,2,3,6,3],[3,2,1,6,3,6],[18,3,6,1,2,9],[9,6,3,2,1,18],[2,3,6,9,18,1]]
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
        mat = str([list(ri) for ri in mat.rows()]).replace(" ", "")

    cond_lab = ec['conductor_label']

    output_fields = [ec['field_label'],
                     cond_lab,
                     ec['iso_label'],
                     str(ec['number']),
                     mat]
    return " ".join(output_fields)



##############
#
#  Indices needed for the nfcurves collection:
#
#  1. 'field_label'
#  2. 'degree'
#  3. 'number'
#  4. 'label'
#  5. 'class_label'
#  6. 'base_change'
#  7. 'isogeny_degrees'
#  8. 'torsion_order'
#  9. ('field_label', 'conductor_norm', 'conductor_label', 'iso_nlabel', 'number')
#
##############

def make_indices():
    for x in ['field_label', 'degree', 'number', 'label', 'base_change', 'isogeny_degrees', 'class_label', 'torsion_order']:
        nfcurves.create_index(x)
    nfcurves.create_index([(x,pymongo.ASCENDING) for x in ['field_label', 'conductor_norm', 'conductor_label', 'iso_nlabel', 'number']])

########################################################
#
# Script to check that data is complete and consistent
#
########################################################

def check_database_consistency(collection, field=None, degree=None, ignore_ranks=False):
    r""" Check that for given field (or all) every database entry has all
    the fields it should, and that these have the correct type.
    """
    str_type = type(unicode('abc'))
    int_type = type(int(1))
    float_type = type(float(1))
    list_type = type([1,2,3])
    #dict_type = type({'a':1})
    bool_type = type(True)

    keys_and_types = {'field_label':  str_type,
                      'degree': int_type,
                      'signature': list_type, # of ints
                      'abs_disc': int_type,
                      'label':  str_type,
                      'short_label':  str_type,
                      'class_label':  str_type,
                      'short_class_label':  str_type,
                      'conductor_label': str_type,
                      'conductor_ideal': str_type,
                      'conductor_norm': int_type,
                      'iso_label': str_type,
                      'iso_nlabel': int_type,
                      'number': int_type,
                      'ainvs': str_type,
                      'jinv': str_type,
                      'cm': int_type,
                      'ngens': int_type,
                      'rank': int_type,
                      'rank_bounds': list_type, # 2 ints
                      #'analytic_rank': int_type,
                      'torsion_order': int_type,
                      'torsion_structure': list_type, # 0,1,2 ints
                      'gens': list_type, # of strings
                      'torsion_gens': list_type, # of strings
                      #'sha_an': int_type,
                      'isogeny_matrix': list_type, # of lists of ints
                      'isogeny_degrees': list_type, # of ints
                      #'class_deg': int_type,
                      'non_surjective_primes': list_type, # of ints
                      #'non-maximal_primes': list_type, # of ints
                      'galois_images': list_type, # of strings
                      #'mod-p_images': list_type, # of strings
                      'equation': str_type,
                      'local_data': list_type, # of dicts
                      'non_min_p': list_type, # of strings
                      'minD': str_type,
                      'heights': list_type, # of floats
                      'reg': float_type, # or int(1)
                      'q_curve': bool_type,
                      'base_change': list_type, # of strings
    }

    key_set = Set(keys_and_types.keys())
#
#   Some keys are only used for the first curve in each class.
#   Currently only the isogeny matrix, but later there may be more.
#
    number_1_only_keys = ['isogeny_matrix'] # only present if 'number':1
#
#   As of April 2017 rank data is only computed for imaginary
#   quadratic fields so we need to be able to say to ignore the
#   associated keys.  Also (not yet implemented) if we compute rank
#   upper and lower bounds then the rank key is not set, and this
#   script should allow for that.
#
    rank_keys = ['analytic_rank', 'rank', 'rank_bounds', 'ngens', 'gens']
#
#   As of April 2017 we have mod p Galois representration data for all
#   curves except some of those over degree 6 fields since over these
#   fields the curves are still being found and uploaded, o we ignore
#   these keys over degree 6 fields for now.
#
    galrep_keys = ['galois_images', 'non_surjective_primes']
    print("key_set has {} keys".format(len(key_set)))

    query = {}
    if field is not None:
        query['field_label'] = field
    elif degree is not None:
        query['degree'] = int(degree)

    count=0
    for c in C.elliptic_curves.get_collection(collection).find(query):
        count +=1
        if count%1000==0:
            print("Checked {} entries...".format(count))
        expected_keys = key_set
        if ignore_ranks:
            expected_keys = expected_keys - rank_keys
        if c['number']!=1:
            expected_keys = expected_keys - number_1_only_keys
        if c['degree']==6:
            expected_keys = expected_keys - galrep_keys
        db_keys = Set([str(k) for k in c.keys()]) - ['_id', 'class_deg', 'class_size']
        if ignore_ranks:
            db_keys = db_keys - rank_keys
        if c['degree']==6:
            db_keys = db_keys - galrep_keys

        label = c['label']

        if db_keys == expected_keys:
            for k in db_keys:
                ktype = keys_and_types[k]
                if type(c[k]) != ktype and not k=='reg' and ktype==type(int):
                    print("Type mismatch for key {} in curve {}".format(k,label))
                    print(" in database: {}".format(type(c[k])))
                    print(" expected:    {}".format(keys_and_types[k]))
        else:
            print("keys mismatch for {}".format(label))
            diff1 = [k for k in expected_keys if not k in db_keys]
            diff2 = [k for k in db_keys if not k in expected_keys]
            if diff1: print("expected but absent:      {}".format(diff1))
            if diff2: print("not expected but present: {}".format(diff2))

# Functions to add isogeny_degrees fields to existing data
#
# 1. Read all curves with 'number':1 and return a dictionary with keys
# full curve labels and values the associated isogeny degree lists
# (sorted and with no repeats).

def make_isog_degree_dict(field=None):
    r""" If field is not None, only work on curve with this field_label
    (for testing), otherwise work on every curve.
    """
    query = {}
    query['number'] = int(1)
    if field:
        query['field_label'] = field
    isog_dict = {}
    for e in nfcurves.find(query):
        class_label = e['class_label']
        #print(class_label)
        isomat = e['isogeny_matrix']
        allisogdegs = dict([[n+1,sorted(list(set(row)))] for n,row in enumerate(isomat)])
        for n in range(len(isomat)):
            label = class_label+str(n+1)
            isog_dict[label] = {'isogeny_degrees': allisogdegs[n+1]}
    return isog_dict

#
# 2. Now set isog_dict = make_isog_degree_dict() and use the following
#

#isogdata = make_isog_degree_dict()
isogdata = {} # to keep pyflakes happy

def add_isogs_to_one(c):
    c.update(isogdata[c['label']])
    return c

#
# 3. in a call to rewrite_collection such as
#
#  %runfile data_mgt/utilities/rewrite.py
#  rewrite_collection(C.elliptic_curves,'nfcurves','nfcurves.new',add_isogs_to_one)

################################################################################
#
# Function to update the nfcurves.stats collection, to be run after adding data
#
################################################################################

def update_stats(verbose=True):
    from data_mgt.utilities.rewrite import update_attribute_stats
    from bson.code import Code
    ec = C.elliptic_curves
    ecdbstats = ec.nfcurves.stats

    # get list of degrees

    degrees = nfcurves.distinct('degree')
    if verbose:
        print("degrees: {}".format(degrees))

    # get list of signatures for each degree.  Note that it would not
    # work to use nfcurves.find({'degree':d}).distinct('signature')
    # since 'signature' is currently a list of integers an mongo would
    # return a list of integers, not a list of lists.  With hindsight
    # it would have been better to store the signature as a string.

    if verbose:
        print("Adding signatures_by_degree")
    reducer = Code("""function(key,values){return Array.sum(values);}""")
    attr = 'signature'
    mapper = Code("""function(){emit(""+this."""+attr+""",1);}""")
    sigs_by_deg = {}
    for d in degrees:
        sigs_by_deg[str(d)] = [ r['_id'] for r in nfcurves.inline_map_reduce(mapper,reducer,query={'degree':d})]
        if verbose:
            print("degree {} has signatures {}".format(d,sigs_by_deg[str(d)]))

    entry = {'_id': 'signatures_by_degree'}
    ecdbstats.delete_one(entry)
    entry.update(sigs_by_deg)
    ecdbstats.insert_one(entry)

    # get list of fields for each signature.  Simple code here faster than map/reduce

    if verbose:
        print("Adding fields_by_signature")
    from sage.misc.flatten import flatten
    sigs = flatten(sigs_by_deg.values())
    fields_by_sig = dict([sig,nfcurves.find({'signature':[int(x) for x in sig.split(",")]}).distinct('field_label')] for sig in sigs)
    entry = {'_id': 'fields_by_signature'}
    ecdbstats.delete_one(entry)
    entry.update(fields_by_sig)
    ecdbstats.insert_one(entry)

    # get list of fields for each degree

    if verbose:
        print("Adding fields_by_degree")
    fields_by_deg = dict([str(d),sorted(nfcurves.find({'degree':d}).distinct('field_label')) ] for d in degrees)
    entry = {'_id': 'fields_by_degree'}
    ecdbstats.delete_one(entry)
    entry.update(fields_by_deg)
    ecdbstats.insert_one(entry)

    fields = flatten(fields_by_deg.values())
    if verbose:
        print("{} fields, {} signatures, {} degrees".format(len(fields),len(sigs),len(degrees)))

    if verbose:
        print("Adding curve counts for torsion order, torsion structure")
    update_attribute_stats(ec, 'nfcurves', ['torsion_order', 'torsion_structure'])

    if verbose:
        print("Adding curve counts by degree, signature and field")
    update_attribute_stats(ec, 'nfcurves', ['degree', 'signature', 'field_label'])

    if verbose:
        print("Adding class counts by degree, signature and field")
    update_attribute_stats(ec, 'nfcurves', ['degree', 'signature', 'field_label'],
                           prefix="classes", filter={'number':int(1)})

    # conductor norm ranges:
    # total:
    if verbose:
        print("Adding curve and class counts and conductor range")
    norms = ec.nfcurves.distinct('conductor_norm')
    data = {'ncurves': ec.nfcurves.count(),
            'nclasses': ec.nfcurves.find({'number':1}).count(),
            'min_norm': min(norms),
            'max_norm': max(norms),
            }
    entry = {'_id': 'conductor_norm'}
    ecdbstats.delete_one(entry)
    entry.update(data)
    ecdbstats.insert_one(entry)

    # by degree:
    if verbose:
        print("Adding curve and class counts and conductor range, by degree")
    degree_data = {}
    for d in degrees:
        query = {'degree':d}
        res = nfcurves.find(query)
        ncurves = res.count()
        Ns = res.distinct('conductor_norm')
        min_norm = min(Ns)
        max_norm = max(Ns)
        query['number'] = 1
        nclasses = nfcurves.count(query)
        degree_data[str(d)] = {'ncurves':ncurves,
                               'nclasses':nclasses,
                               'min_norm':min_norm,
                               'max_norm':max_norm,
        }

    entry = {'_id': 'conductor_norm_by_degree'}
    ecdbstats.delete_one(entry)
    entry.update(degree_data)
    ecdbstats.insert_one(entry)

    # by signature:
    if verbose:
        print("Adding curve and class counts and conductor range, by signature")
    sig_data = {}
    for sig in sigs:
        query = {'signature': [int(c) for c in sig.split(",")]}
        res = nfcurves.find(query)
        ncurves = res.count()
        Ns = res.distinct('conductor_norm')
        min_norm = min(Ns)
        max_norm = max(Ns)
        query['number'] = 1
        nclasses = nfcurves.count(query)
        sig_data[sig] = {'ncurves':ncurves,
                               'nclasses':nclasses,
                               'min_norm':min_norm,
                               'max_norm':max_norm,
        }
    entry = {'_id': 'conductor_norm_by_signature'}
    ecdbstats.delete_one(entry)
    entry.update(sig_data)
    ecdbstats.insert_one(entry)

    # by field:
    if verbose:
        print("Adding curve and class counts and conductor range, by field")
    entry = {'_id': 'conductor_norm_by_field'}
    ecdbstats.delete_one(entry)
    field_data = {}
    for f in fields:
        ff = f.replace(".",":") # mongo does not allow "." in key strings
        query = {'field_label': f}
        res = nfcurves.find(query)
        ncurves = res.count()
        Ns = res.distinct('conductor_norm')
        min_norm = min(Ns)
        max_norm = max(Ns)
        query['number'] = 1
        nclasses = nfcurves.count(query)
        field_data[ff] = {'ncurves':ncurves,
                               'nclasses':nclasses,
                               'min_norm':min_norm,
                               'max_norm':max_norm,
        }
    entry = {'_id': 'conductor_norm_by_field'}
    ecdbstats.delete_one(entry)
    entry.update(field_data)
    ecdbstats.insert_one(entry)

def make_IQF_ideal_table(infile, insert=False):
    items = []
    n = 0
    for L in file(infile).readlines():
        n += 1
        f, old, new = L.split()
        item = {'fld':f, 'old':old, 'new':new}
        items.append(item)
    print("read {} lines from {}".format(n,infile))
    if insert:
        print("inserting into IQF_labels collection")
        C['elliptic_curves']['IQF_labels'].insert_many(items)
    else:
        print("No insertion, dummy run")


# function to give to rewrite_collection() to fix q_curve flags (only touches quadratic field so far)

def fix1_qcurve_flag(ec, verbose=False):
    """
    Update ec structure (from nfcurves collection) with the correct
    q_curves flag.  For degree >2 at present we only do trivial tests
    here which do not require any computation.
    """
    if ec['q_curve']: # keep old True values
        return ec

    # Easy sufficient tests in all degrees
    qc = False
    if ec['cm']:
        qc = True
    elif all(c=='0' for c in ec['jinv'].split(",")[1:]):
        qc = True

    if qc: # then we have just set it to True
        if ec['q_curve'] != qc:
            if verbose:
                print("{}: changing q_curve flag from {} to {}".format(ec['label'],ec['q_curve'],qc))
        ec['q_curve'] = qc
        return ec

    # else if degree != 2 just replace possibly false negatives with '?'
    if ec['degree'] > 2:
        qc = '?'
        # if ec['q_curve'] != qc:
        #     print("{}: changing q_curve flag from {} to {}".format(ec['label'],ec['q_curve'],qc))
        ec['q_curve'] = qc
        return ec

    # else (degree 2 only for now) do the work (knowing that E does
    # not have CM and j(E) is not in Q)

    K = FIELD(ec['field_label'])
    sigma = K.K().galois_group()[1]
    # Compute the Q-curve flag from scratch

    N = ideal_from_string(K.K(),ec['conductor_ideal'])
    if sigma(N)!=N:
        qc = False
    else: # construct and check the curve
        ainvsK = parse_ainvs(K.K(), ec['ainvs'])
        E = EllipticCurve(ainvsK)
        qc = is_Q_curve(E)
    if ec['q_curve'] != qc:
        if verbose:
            print("{}: changing q_curve flag from {} to {}".format(ec['label'],ec['q_curve'],qc))
    ec['q_curve'] = qc
    return ec

def is_Q_curve(E):
    """Test if an elliptic curve is a Q-curve.
    """
    jE =  E.j_invariant()
    if jE in QQ:
        return True
    if E.has_cm():
        return True
    K = E.base_field()
    if K.degree()>2:
        raise NotImplementedError("Only quadratic fields implemented so far")
    sigma = K.galois_group()[1]
    N = E.conductor()
    if N!=sigma(N):
        return False
    jEs = sigma(jE)
    C = E.isogeny_class()
    # check that the conjugate of j(E) is in the class:
    return any(E1.j_invariant()==jEs for E1 in C)

def check_Q_curves(field_label='2.2.5.1', min_norm=0, max_norm=None, fix=False, verbose=False):
    """Given a (quadratic) field label test all curves E over that field for being Q-curves.
    """
    query = {}
    query['field_label'] = field_label
    query['conductor_norm'] = {'$gte': int(min_norm)}
    if max_norm:
        query['conductor_norm']['$lte'] = int(max_norm)
    else:
        max_norm = 'infinity'
    cursor = nfcurves.find(query)
    # keep the curves and re-find them, else the cursor times out.
    curves = [ec['label'] for ec in cursor]
    ncurves = len(curves)
    print("Checking {} curves over field {}".format(ncurves,field_label))
    K = FIELD(field_label)
    sigma = K.K().galois_group()[1]
    bad1 = []
    bad2 = []
    count = 0
    for label in curves:
        count += 1
        if count%1000==0:
            print("checked {} curves ({}%)".format(count, 100.0*count/ncurves))
        ec = nfcurves.find_one({'label':label})
        assert label == ec['label']
        method = None
        # first check that j(E) is rational (no computation needed)
        jinv = ec['jinv']
        if all(c=='0' for c in jinv.split(",")[1:]):
            if verbose: print("{}: j in QQ".format(label))
            qc = True
            method = "j in Q"
        elif ec['cm']:
            if verbose: print("{}: CM".format(label))
            qc = True
            method = "CM"
        else: # construct and check the conductor
            if verbose:
                print("{}: checking conductor".format(label))
            N = ideal_from_string(K.K(),ec['conductor_ideal'])
            if sigma(N)!=N:
                qc = False
                method = "conductor"
            else: # construct and check the curve
                if verbose:
                    print("{}: checking isogenies".format(label))
                ainvsK = parse_ainvs(K.K(), ec['ainvs'])
                E = EllipticCurve(ainvsK)
                qc = is_Q_curve(E)
                method = "isogenies"
        db_qc = ec['q_curve']
        if qc and not db_qc:
            print("Curve {} is a Q-curve (using {}) but database thinks not".format(label, method))
            bad1 += [label]
        elif db_qc and not qc:
            print("Curve {} is not a Q-curve (using {}) but database thinks it is".format(label, method))
            bad2 += [label]
        else:
            if verbose:
                print("Curve {} OK (using {})".format(label, method))
    print("{} curves in the database are incorrectly labelled as being Q-curves".format(len(bad2)))
    print("{} curves in the database are incorrectly labelled as NOT being Q-curves".format(len(bad1)))
    return bad1, bad2
