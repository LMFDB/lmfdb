# -*- coding: utf-8 -*-
r""" Import torsion growth data (as computed by Enrique Gonzalez).

Initial version (Warwick November 2017)

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
from sage.all import ZZ, PolynomialRing, QQ, NumberField

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
fields = C.numberfields.fields

Qx = PolynomialRing(QQ,'x')

def str_to_list(s):
    """
    Input: string representing list of ints, e.g. '', '2', '2,4', '5,4,3,2,1'
    """
    s = s.replace("[","").replace("]","")
    if s == '':
        return []
    else:
        return [int(c) for c in s.split(",")]

def poly_to_str(f):
    return str(f.coefficients(sparse=False)).replace(" ", "")[1:-1]


def find_field(pol, verbose=False):
    """
    pol is a string holding a list of coefficients, constant first, 1 last, e.g. '-2,0,1'

    Looks up this defining polynomial kn LMFDB and returns its label, or None
    """
    coeffs = str_to_list(pol)
    deg = len(coeffs)-1
    if deg==2:
        c, b, a = coeffs
        d = ZZ(b*b-4*a*c).squarefree_part()
        D = d if (d-1)%4==0 else 4*d
        absD = D.abs()
        s = 0 if d<0 else 2
        return '2.{}.{}.1'.format(s,absD)

    from lmfdb.number_fields.number_field import poly_to_field_label
    poly = Qx(coeffs)
    Flabel = poly_to_field_label(poly)
    if Flabel==None:
        print("********* field with polynomial {} is not in the database!".format(poly))
        K = NumberField(poly, 'a')
        poly = K.optimized_representation()[0].defining_polynomial()
        print("********* using optimised polynomial {}".format(poly))
        return poly_to_str(poly)
    else:
        if verbose:
            print("{} has label {}".format(pol,Flabel))
        return Flabel

def get_degree(label_or_coeffs):
    """Input: string, either a number field label or a list of
    coefficients of a defining polynomial, e.g. '-2,0,2'
    """
    if '.' in label_or_coeffs:
        return int(label_or_coeffs.split(".")[0])
    else:
        return label_or_coeffs.count(',')

def onefieldtor(dat, degree):
    """
    Input: string e.g. [2,6][4,-1,1], where the first list is a torsion structure and the second is a list of polynomial coefficients.
    """
    tor, pol = dat.split("][")
    tor = tor[1:]
    pol = pol[:-1]
    d = get_degree(pol)
    if d != int(degree):
        return None
    F = find_field(pol)
    return [F,tor]

def onefieldxtor(dat):
    """Input: string e.g. [2,6]:4,-1,1, where the first list is a torsion
    structure and the second is a list of polynomial coefficients, or
    [2,6]:2.2.5.1 with the second part an LMFDB field label.
    """
    T, F = dat.split(":")
    T = T[1:-1]
    return [F,T]

def read_line(line, degree, debug=0):
    r""" Parses one line from input file.  Returns a dict containing ...

    Sample line: 14a1 [6] [3,6][1,1,1] [2,6][2,-1,1]

    Fields: label (single field, Cremona label)
            T     (torsion over Q, [], or [n] with n>1 or [m,n] with 1<m|n)

            0 or more items of the form TF (with no space between)
            with T as above and F a list of integers of length d>=2
            containing the coefficients of a monic polynomial of
            degree d defining a number field.

    Note: in each file d is fixed and contained in the filename
    (e.g. growth2.000000-399999) but can be recovered from any line
    with >2 fields from the length of the coefficient lists.

    """
    if debug: print("Parsing input line {} in degree {}".format(line, degree))
    fields = line.split()
    clabel = fields[0]
    # The data file contains the torsion over Q, but we do not use it
    # Qt = str_to_list(fields[1]) # string representing list of ints of length <=2

    tordata = [onefieldtor(dat, degree) for dat in fields[2:]]
    if debug: print("before degree check, tordata = {}".format(tordata))
    tordata = [t for t in tordata if t!=None]
    if debug: print("after  degree check, tordata = {}".format(tordata))
    data = dict(tordata)

    if debug: print("label {}, data {}".format(clabel,data))
    return clabel, data

def read_xline(line, degree, debug=0):
    r""" Parses one line from input file.  Returns a dict containing ...

    Sample line: 14a1 [3,6]:1,1,1 [2,6]:2.2.5.1

    Fields: label (single field, Cremona label)

            0 or more items of the form T:F (with no space between)
            with T as above and F either a list of integers of length d+1>=3
            containing the coefficients of a monic polynomial of
            degree d defining a number field, or an LMFDB field label e.g. 2.2.5.1

    Note: in each file d is fixed and contained in the filename
    (e.g. growth2x.000000-399999) but can be recovered from any line
    with >1 fields from the field data.

    """
    if debug: print("Parsing input line {} in degree {}".format(line, degree))
    fields = line.split()
    clabel = fields[0]

    tordata = [onefieldxtor(dat) for dat in fields[1:]]
    data = dict(tordata)

    if debug: print("label {}, data {}".format(clabel,data))
    return clabel, data

# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile lmfdb/elliptic_curves/import_torsion_data.py
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
        #if data['torsion_growth']label]
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

def add_iw_data1(C, tor_data):
    """Add fields to a single curve record in the db.
    """
    C.update(tor_data[C['label']])
    return C

def read_torsion_growth_data(base_path, filename, degree, maxlines=0):
    f = os.path.join(base_path, filename)
    h = open(f)
    print "opened %s" % f

    tor_data = {}
    count = 0

    for line in h.readlines():
        count += 1
        if count%10000==0:
            print "read %s lines" % count
        if maxlines and count>maxlines:
            break
        label, data = read_line(line,degree,0)
        tor_data[label] = data

    print("finished reading {} lines from file".format(count))
    return tor_data

def read_xtorsion_growth_data(base_path, filename, degree, maxlines=0):
    f = os.path.join(base_path, filename)
    h = open(f)
    print "opened %s" % f

    tor_data = {}
    count = 0

    for line in h.readlines():
        count += 1
        if count%10000==0:
            print "read %s lines" % count
        if maxlines and count>maxlines:
            break
        label, data = read_xline(line,degree,0)
        tor_data[label] = data

    print("finished reading {} lines from file".format(count))
    return tor_data

# for use with the rewrite script in data_mgt/utilities/rewrite.py we
# need to give it the old and new collection names (e.g. curves and
# curves.new) and a function taking one mongodb record (dictionary) and
# returning a possible changed version of it.

#  The following returns such a function, only applying it to curves with conductors in a given range

def tor_data_update(N1, N2, base_path, maxlines=0):
    tordata = {}
    degrees = [str(d) for d in range(2,8)]
    for d in degrees:
        f = "growth{}.000000-399999".format(d)
        tordata[d] = read_torsion_growth_data(base_path, f, d, maxlines)
    def update_function(C):
        N = int(C['conductor'])
        if N1 <= N <= N2:
            label = C['label']
            tdeg = [d for d in degrees if tordata[d][label]]
            C['tor_degs'] = [int(d) for d in tdeg]
            tor_gro = {}
            for d in tdeg:
                td = tordata[d][label]
                td = dict([(F.replace(".",":"),T) for F,T in td.items()])
                tor_gro.update(td)
            C['tor_gro'] = tor_gro
            C['tor_fields'] = [F.replace(":",".") for F in tor_gro.keys()]
        return C
    return tordata, update_function

def tor_xdata_update(N1, N2, base_path, degrees=None, overwrite=False, maxlines=0):
    tordata = {}
    if degrees == None:
        degrees = [str(d) for d in range(2,8)]
    else:
        degrees = [str(d) for d in degrees]
    for d in degrees:
        f = "growth{}x.000000-399999".format(d)
        tordata[d] = read_xtorsion_growth_data(base_path, f, d, maxlines)
    def update_function(C):
        N = int(C['conductor'])
        if N1 <= N <= N2:
            label = C['label']

            tdeg = [d for d in degrees if tordata[d][label]]
            td = [int(d) for d in tdeg]
            if 'tor_degs' in C and not overwrite:
                C['tor_degs'].append(td)
            else:
                C['tor_degs'] = td

            tor_gro = {}
            for d in tdeg:
                td = tordata[d][label]
                td = dict([(F.replace(".",":"),T) for F,T in td.items()])
                tor_gro.update(td)
            if 'tor_gro' in C and not overwrite:
                C['tor_gro'].update(tor_gro)
            else:
                C['tor_gro'] = tor_gro

            tf = [F.replace(":",".") for F in tor_gro.keys()]
            if 'tor_fields' in C and not overwrite:
                C['tor_fields'].append(tf)
            else:
                C['tor_fields'] = tf
        return C
    return tordata, update_function

def write_tordata(tordata, base_path='', degrees = None, maxlines=0):
    if degrees == None:
        degrees = [str(d) for d in range(2,8)]
    else:
        degrees = [str(d) for d in degrees]

    for d in degrees:
        f = os.path.join(base_path, "growth{}x.000000-399999".format(d))
        h = open(f, mode='w')
        print "opened {}".format(f)
        td = tordata[d]
        count = 0
        for lab, dat in td.iteritems():
            h.write(" ".join([lab]+["[{}]:{}".format(T,F.replace(":",".")) for F,T in dat.items()]) + "\n")
            count +=1
            if count==maxlines:
                break
        h.close()
