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
   - 'dimension_data': (dict) each key is a weight (int), with value a
                       dict with keys 'cuspidal_dim', 'new_dim'

"""
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

# The following ensure_index command checks if there is an index on
# level norm, field_absdisc. If there is no index it creates one.

#dims.ensure_index('level_norm')
#dims.ensure_index('field_absdisc')

whitespace = re.compile(r'\s+')

def split(line):
    return whitespace.split(line.strip())

def dimtab(line):
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
    d, s, field_absdisc, n = [int(x) for x in field_label.split(".")]
    weight = int(data[1])
    #assert weight==2
    level_params = data[2].split(',')
    level_norm = int(level_params[0][1:])
    level_a = int(level_params[1])
    level_b = int(level_params[2][:-1])
    level_label = ".".join([str(level_norm),str(level_a), str(level_b)])
    label = '-'.join([field_label,level_label])
    cuspidal_dim = int(data[3])
    new_cuspidal_dim = int(data[4])
    dim_data = {str(weight): {'cuspidal_dim': cuspidal_dim, 'new_dim': new_cuspidal_dim}}
    return label, {
        'label': label,
        'field_label': field_label,
        'field_absdisc': field_absdisc,
        'level_label': level_label,
        'level_norm': level_norm,
        'dimension_data': dim_data,
    }

def dimtabeis(line):
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
    d, s, field_absdisc, n = [int(x) for x in field_label.split(".")]
    weight = int(data[1])
    level_params = data[2].split(',')
    level_norm = int(level_params[0][1:])
    level_a = int(level_params[1])
    level_b = int(level_params[2][:-1])
    level_label = ".".join([str(level_norm),str(level_a), str(level_b)])
    label = '-'.join([field_label,level_label])
    #all_dim = int(data[3]) # not used
    cuspidal_dim = int(data[4])
    new_cuspidal_dim = int(data[5])
    dim_data = {str(weight): {'cuspidal_dim': cuspidal_dim, 'new_dim': new_cuspidal_dim}}
    return label, {
        'label': label,
        'field_label': field_label,
        'field_absdisc': field_absdisc,
        'level_label': level_label,
        'level_norm': level_norm,
        'dimension_data': dim_data,
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
                    if key=='dimension_data':
                        print("Before update, space[{}] = {}".format(key,space[key]))
                        print("data[{}] = {}".format(key,data[key]))
                        space[key].update(data[key])
                        print("After update, space[{}] = {}".format(key,space[key]))
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
        print("inserting all data")
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
