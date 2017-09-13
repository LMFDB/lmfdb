# -*- coding: utf-8 -*-
r""" Import data to Bianchi database of dimensions

Initial version (Bristol September 2013): John Cremona
Revised (Warwick June 2014): John Cremona

The database 'bmfs' has two collections: "dimensions" and "forms".
The "dimensions" collection entries have the following fields:

   - '_id':            (ObjectId): internal mongodb identifier
   - 'field_label':    (string) label of the number field, e.g. '2.0.4.1'
   - 'field_absdisc':  (int) absolute value of discriminant of the number field, e.g. 4
   - 'level_label':    (string)  label of the level ideal, e.g. '[1,0,1]'
   - 'level_norm':     (int)  norm of the level ideal, e.g. 1
   - 'level_ncusps':   (int) number of cusps for this level
   - 'label':          (string) 'field_label' + '-' + 'level_label'
   - 'gl2_dims':       (dict) each key is a weight (int), with value a
                         dict with keys 'cuspidal_dim', 'new_dim' (and possibly more)
   - 'sl2_dims':       (dict) each key is a weight (int), with value a
                         dict with keys 'cuspidal_dim', 'new_dim' (and possibly more)

"""
from sage.all import polygen, QQ, ZZ, NumberField

from lmfdb.base import getDBConnection
print "getting connection"
C= getDBConnection()
print "authenticating on the elliptic_curves database"
import yaml
import os
import re
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['bmfs'].authenticate(username, password)
print "setting bmfs"
bmfs = C.bmfs
print "setting dims"
dims = bmfs.dimensions

# The following ensure_index command checks if there is an index on
# level norm, field_absdisc. If there is no index it creates one.

#dims.ensure_index('level_norm')
#dims.ensure_index('field_absdisc')

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


def dimtab(line, gl_or_sl = "gl"):
    r""" Parses one line from a dimtab file.  Returns a complete entry
    for the dimensions collection.

    Input line fields:

    field_label weight level cusp-dim new-cusp-dim

    Sample input line:

    2.0.4.1 2 [1,0,1] 0 0
    """
    data = split(line)
    # Skip header lines
    if data[0] in ["Table","Field"]:  return '', {}

    field_label = data[0]
    K = field_from_label(field_label)
    d, s, field_absdisc, n = [int(x) for x in field_label.split(".")]
    weight = int(data[1])
    #assert weight==2
    level_params = data[2].split(',')
    level_norm = int(level_params[0][1:])
    level_a = int(level_params[1])
    level_b = int(level_params[2][:-1])
    level_label = ".".join([str(level_norm),str(level_a), str(level_b)])
    level_label = convert_ideal_label(K, level_label)
    label = '-'.join([field_label,level_label])
    cuspidal_dim = int(data[3])
    new_cuspidal_dim = int(data[4])
    dim_data = {str(weight): {'cuspidal_dim': cuspidal_dim, 'new_dim': new_cuspidal_dim}}
    dim_key = 'gl2_dims' if gl_or_sl == "gl" else 'sl2_dims'
    return label, {
        'label': label,
        'field_label': field_label,
        'field_absdisc': field_absdisc,
        'level_label': level_label,
        'level_norm': level_norm,
        dim_key: dim_data,
    }

def dimtabeis(line, gl_or_sl = "gl"):
    r""" Parses one line from a dimtabeis file.  Returns a complete entry
    for the dimensions collection.

    Input line fields:

    field weight level all-dim cusp-dim new-cusp-dim eis-dims

    Sample input line:

    11 	2 	[81,6,3] 	9 	2 	0 	7

    """
    if line[0] =="#":  return '', {}
    data = split(line)
    # Skip header lines
    if data[0] in ["Table","Field"]:  return '', {}

    field = int(data[0])
    field_label = "2.0.{}.1".format([0,4,8,3,0,0,0,7,0,0,0,11][field])
    K = field_from_label(field_label)
    d, s, field_absdisc, n = [int(x) for x in field_label.split(".")]
    weight = int(data[1])
    level_label = data[2]
    if "[" in level_label:
        level_label = ".".join([x for x in level_label[1:-1].split(',')])
    level_label = convert_ideal_label(K, level_label)
    level_norm = int(level_label.split(".")[0])
    label = '-'.join([field_label,level_label])
    #all_dim = int(data[3]) # not used
    cuspidal_dim = int(data[4])
    new_cuspidal_dim = int(data[5])
    dim_data = {str(weight): {'cuspidal_dim': cuspidal_dim, 'new_dim': new_cuspidal_dim}}
    dim_key = 'gl2_dims' if gl_or_sl == "gl" else 'sl2_dims'
    return label, {
        'label': label,
        'field_label': field_label,
        'field_absdisc': field_absdisc,
        'level_label': level_label,
        'level_norm': level_norm,
        dim_key: dim_data,
    }

def SL2dimtab(line):
    r""" Parses one line from a SL2dimtab file.  Returns a complete entry
    for the dimensions collection.

    Input line fields:

    field weight level cusp-dim new-cusp-dim

    Sample input line:

    2.0.11.1 2 [121,0,11] 5 3

    """
    #print line
    if line[0] =="#":
        return '', {}
    data = split(line)

    field_label = data[0]
    K = field_from_label(field_label)
    d, s, field_absdisc, n = [int(x) for x in field_label.split(".")]
    weight = int(data[1])
    level_params = data[2].split(',')
    level_norm = int(level_params[0][1:])
    level_a = int(level_params[1])
    level_b = int(level_params[2][:-1])
    level_label = ".".join([str(level_norm),str(level_a), str(level_b)])
    level_label = convert_ideal_label(K, level_label)
    label = '-'.join([field_label,level_label])
    #all_dim = int(data[3]) # not used
    cuspidal_dim = int(data[3])
    new_cuspidal_dim = int(data[4])
    dim_data = {str(weight): {'cuspidal_dim': cuspidal_dim, 'new_dim': new_cuspidal_dim}}
    dim_key = 'sl2_dims'
    return label, {
        'label': label,
        'field_label': field_label,
        'field_absdisc': field_absdisc,
        'level_label': level_label,
        'level_norm': level_norm,
        dim_key: dim_data,
    }


def upload_to_db(base_path, filename, insert=True):
    #dims_filename = ".".join(['dimtab',suffix])
    dims_filename = filename
    file_list = [dims_filename]

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
            if count%5000==0:
                print "read %s" % label
            count += 1
            if label not in data_to_insert:
                data_to_insert[label] = {'label': label}
            space = data_to_insert[label]
            for key in data:
                if key in space:
                    if key in ['gl2_dims', 'sl2_dims']:
                        print("------------------------------------------------------")
                        print("Before update, space[{}] = {}".format(key,space[key]))
                        print("data[{}] = {}".format(key,data[key]))
                        space[key].update(data[key])
                        print("------------------------------------------------------")
                        print("After update, space[{}] = {}".format(key,space[key]))
                        print("------------------------------------------------------")
                    else:
                        if space[key] != data[key]:
                            print("space[{}] = {}".format(key,space[key]))
                            print("data[{}] = {}".format(key,data[key]))
                            raise RuntimeError("Inconsistent data for %s" % label)
                else:
                    space[key] = data[key]
        print "finished reading %s lines from file" % count

    vals = data_to_insert.values()
    if insert:
        print("inserting all data ({} items)".format(len(vals)))
        dims.insert_many(vals)
    else:
        count = 0
        print("inserting data one at a time...")
        for val in vals:
            #print val
            dims.update_one({'label': val['label']}, {"$set": val}, upsert=True)
            count += 1
            if count % 100 == 0:
                print "inserted %s" % (val['label'])

def make_indices():
    from pymongo import ASCENDING
    dims.create_index('field_label')
    dims.create_index([('field_label',ASCENDING),
                        ('level_label',ASCENDING)])
    dims.create_index([('field_label',ASCENDING),
                        ('gl2_dims',ASCENDING)])
    dims.create_index([('field_label',ASCENDING),
                        ('sl2_dims',ASCENDING)])

def update_stats():
    # We don't yet have proper stats info for bmfs.  When we do it will  be created / updated here
    fields = dims.distinct('field_label')
    print("fields: {}".format(fields))

