# -*- coding: utf-8 -*-
r""" Import newforms to Bianchi database of newforms

Initial version (Warwick June 2017): John Cremona

The database 'bmfs' has two collections: "dimensions" and "forms".
The "forms" collection entries have the following fields:

   - '_id':            (ObjectId): internal mongodb identifier
   - 'field_label':    (string) label of the number field, e.g. '2.0.4.1'
   - 'field_disc':     (int) absolute value of discriminant of the number field, e.g. 4
   - 'field_deg':      (int) degree of the number field, e.g. 4
   - 'level_label':    (string)  label of the level ideal, e.g. '[1,0,1]'
   - 'level_norm':     (int)  norm of the level ideal, e.g. 1
   - 'level_ideal':    (string)  defining data of the level ideal, e.g. [25,25,4*w-3]
   - 'level_gen':      (string)  generator of the level ideal, e.g. 7+4i
   - 'label_suffix':   (string) letter code for the newform at fixed level: a, b, c, ...
   - 'label_nsuffix':  (int) numerical version of label_suffix (1 for a, 2 for b etc)
   - 'short_label':    (string) 'level_label' + '-' + 'label_suffix'
   - 'label':          (string) 'field_label' + '-' + 'level_label'
   - 'dimension':      (int) degree of Hecke field (default 1)
   - 'hecke_poly':     (string) min poly in x of Hecke field (default 'x')
   - 'weight':         (int) weight
   - 'sfe':            (int) sign of functional equation
   - 'Lratio':         (string) ratio L(1)/period
   - 'is_base_change': (bool or '?') True iff form is base change from Q
   - 'is_CM':          (bool or '?') True iff form is CM
   - 'AL_eigs':        (list of ints) Atkin-Lehner eigenvalues
   - 'hecke_eigs':     (list of ints or strings) Atkin-Lehner eigenvalues

NB 1. Both AL_eigs and hecke_eigs are indexed by the primes in standard order
   2. hecke_eigs are ints if dimension=1, else strings

   3. Fields agree with those for Hilbert modular forms except:
     (a) is_base_change is boolean, not string ("yes"/"no")
     (b) is_CM is boolean, not string ("yes"/"no")
     (c) parallel_weight is not used as we only have one infinite place
     (d) field_disc replaces disc
     (e) field_deg replaces deg
     (f) hecke_eigs replaces hecke_eigenvalues
     (g) AL_eigs replaces AL_eigenvalues
     (h) hecke_poly replaces hecke_polynomial
     (i) sfe does not exist for HMFs
     (j) Lratio does not exist for HMFs
"""
from sage.all import polygen, QQ, ZZ, NumberField
import re
import os

from lmfdb.base import getDBConnection
print "getting connection"
C= getDBConnection()
print "authenticating on the elliptic_curves database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['bmfs'].authenticate(username, password)
print "setting bmfs"
bmfs = C.bmfs
print "setting dims"
dims = bmfs.dimensions
print "setting forms"
forms = bmfs.forms

whitespace = re.compile(r'\s+')

def split(line):
    return whitespace.split(line.strip())

from lmfdb.nfutils.psort import ideal_label

the_labels = {}

def convert_ideal_label(K, lab):
    """An ideal label of the form N.c.d is converted to N.i.  Here N.c.d
    defines the ideal I with Z-basis [a, c+d*w] where w is the standard
    generator of K, N=N(I) and a=N/d.  The standard label is N.i where I is the i'th ideal of norm N in the standard ordering.
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

the_fields = {}

def field_from_label(lab):
    r"""
    Returns a number field from its LMFDB label.  Only for 5 IQFs at present.
    """
    global the_fields
    if lab in the_fields:
        return the_fields[lab]
    x = polygen(QQ)
    deg, s, abs_disc, _ = lab.split(".")
    assert deg == '2'
    assert s == '0'
    d = -ZZ(abs_disc)
    t = d%4
    assert t in [0,1]
    pol = x**2 - t*x + (t-d)//4
    K = NumberField(pol, 'a')
    print "Created field from label %s: %s" % (lab,K)
    the_fields[lab] = K
    return K

def numerify_iso_label(lab):
    from sage.databases.cremona import class_to_int
    return class_to_int(lab.lower())


def newforms(line):
    r""" Parses one line from a newforms file.  Returns a complete entry
    for the forms collection. This is only for rational newforms of
    weight 2.

    Input line fields:

    field_label level_label level_suffix level_ideal wt bc cm sign Lratio AL_eigs pol hecke_eigs

    Sample input line:

    2.0.4.1 65.18.1 a (7+4i) 2 0 ? 1 1 [1,-1] x [0,0,-1,-2,1,-4,0,6,6,-6,2,2,6,0,-4,6,-6,-10,-10,2,2,6,6,-10,8]

    NB We expect 3-component HNF-style labels for ideals (N.c.d) but will convert to LMFDB labels N.i on input.
    """
    # skip comment lines
    if line[0] == '#':  return '', {}
    data = split(line)
    # base field
    field_label = data[0]
    K = field_from_label(field_label)
    field_disc = - int(field_label.split(".")[2])
    field_deg = 2
    # level
    level_label = convert_ideal_label(K, data[1])
    level_norm = int(level_label.split(".")[0])
    level_ideal = data[3]
    level_gen =  level_ideal[1:-1] # strip (,)

    label_suffix = data[2]
    label_nsuffix = numerify_iso_label(label_suffix)
    short_label = '-'.join([level_label, label_suffix])
    label = '-'.join([field_label, short_label])
    weight = int(data[4])
    bc = data[5]
    if bc!='?': bc=int(bc)
    cm = data[6]
    if cm!='?': bc=int(cm)
    sfe = int(data[7]) # sign
    Lratio = data[8]   # string representing rational number
    dimension = 1
    AL_eigs = [int(x) for x in data[9][1:-1].split(",")]
    hecke_poly = data[10]
    hecke_eigs = [int(x) for x in data[11][1:-1].split(",")]

    return label, {
        'label': label,
        'field_label': field_label,
        'field_disc': field_disc,
        'field_deg': field_deg,
        'level_label': level_label,
        'level_norm': level_norm,
        'level_ideal': level_ideal,
        'level_gen': level_gen,
        'label_suffix': label_suffix,
        'label_nsuffix': label_nsuffix,
        'short_label': short_label,
        'label': label,
        'dimension': dimension,
        'hecke_poly': hecke_poly,
        'weight': weight,
        'sfe': sfe,
        'Lratio': Lratio,
        'is_base_change': bc,
        'is_CM': cm,
        'AL_eigs': AL_eigs,
        'hecke_eigs': hecke_eigs,
    }

def upload_to_db(base_path, filename_suffix, insert=True):
    forms_filename = ".".join(["newforms",filename_suffix])
    file_list = [forms_filename]

    data_to_insert = {}  # will hold all the data to be inserted

    for f in file_list:
        h = open(os.path.join(base_path, f))
        print "opened %s" % os.path.join(base_path, f)

        parse = globals()[f[:f.find('.')]]

        count = 0
        for line in h.readlines():
            if line[0]=='#':
                continue
            label, data = parse(line)
            if label=='':
                continue
            if count%500==0:
                print "read %s" % label
            count += 1
            if label not in data_to_insert:
                data_to_insert[label] = {'label': label}
            old_data = data_to_insert[label]
            for key in data:
                if key in old_data:
                    if old_data[key] != data[key]:
                        print("key = {}".format(key))
                        print("old_data[key] = {}".format(old_data[key]))
                        print("data[key] = {}".format(data[key]))
                        raise RuntimeError("Inconsistent data for %s" % label)
                else:
                    old_data[key] = data[key]
        print "finished reading %s lines from file" % count

    vals = data_to_insert.values()
    if insert:
        print("inserting all data")
        forms.insert_many(vals)
    else:
        count = 0
        print("inserting data one at a time...")
        for val in vals:
            print val
            forms.update_one({'label': val['label']}, {"$set": val}, upsert=True)
            count += 1
            if count % 100 == 0:
                print "inserted %s" % (val['label'])
