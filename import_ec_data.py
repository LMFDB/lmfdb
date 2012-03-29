# -*- coding: utf-8 -*-
r"""
Import data from Cremona tables.
Note: This code can be run on all files in any order. Even if you rerun this code on previously entered files, it should have no affect. 
This code checks if the entry exists, if so returns that and updates with new information. If the entry does not exist then it creates it and 
returns that. 

Initial version (Paris 2010)
More tables Feb 2011 Gagan Sekhon
Needed importing code for Stein-Watkins 

After running this script, please remember to run import_EC_isogeny_data.py
"""


import os.path, gzip, re, sys, time, os, random,glob
import pymongo
import base
from sage.rings.all import ZZ

print "calling base._init()"
base._init(int(37010),'')
print "getting connection"
conn = base.getDBConnection()
print "setting curves"
curves = conn.elliptic_curves.curves

#The following ensure_index command checks if there is an index on label, conductor, rank and torsion. If there is no index it creates one. 
#Need: once torsion structure is computed, we should have an index on that too. 

curves.ensure_index('label')
curves.ensure_index('conductor')
curves.ensure_index('rank')
curves.ensure_index('torsion')

print "finished indices"

def parse_tgens(s):
    r"""
    Converts projective coordinates to affine coordinates for generator
    """  
    g1=s.replace('(', ' ').replace(')',' ').split(':')
    x,y,z = [ZZ(c) for c in g1]
    g=(x/z,y/z)
    return str(g)


def parse_ainvs(s):
#    return [int(a) for a in s[1:-1].split(',')]
    return [a for a in s[1:-1].split(',')]


#def parse_gens(s):
 #   return [int(a) for a in s[1:-1].split(':')]

whitespace = re.compile(r'\s+')
def split(line):
    return whitespace.split(line.strip())

def allbsd(line):
    r"""
    Parses allbsd files
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    ainvs=parse_ainvs(data[3])
    return label, {
        'conductor': int(data[0]),
        'iso': data[0]+data[1],
        'number': int(data[2]),
        'ainvs': ainvs,
        'rank': int(data[4]),
        'torsion': int(data[5]),
        'tamagawa_product': int(data[6]),
        'real_period': float(data[7]),
        'special_value': float(data[8]),
        'regulator': float(data[9]),
        'sha_an': float(data[10]),
    }

def allcurves(line):
    r"""
    Parses allcurves files
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    ainvs=parse_ainvs(data[3])
    return label, {
        'conductor': int(data[0]),
        'iso': data[0]+data[1],
        'number': int(data[2]),
        'ainvs': ainvs,
        'rank': int(data[4]),
        'torsion': int(data[5]),
    }
    
def allgens(line):
    r"""
    Parses allgens files
    """
    data = split(line)
    label = data[0] + data[1] + data[2]
    rank=int(data[4])
    torsion=len(eval(data[5]))
    ainvs=parse_ainvs(data[3])
    return label, {
            'conductor': int(data[0]),
            'iso': data[0]+data[1],
            'number': int(data[2]),
            'ainvs': ainvs,
            'rank': int(data[4]),
            'gens': ["(%s)" % gen[1:-1] for gen in data[6:6+rank]],
            'torsion_structure':["%s" %tor for tor in eval(data[5])],
            'torsion_generators':["%s" %parse_tgens(tgens[1:-1]) for tgens in data[6+rank:]],
            }
        
def allisog(line):
    data=split(line)
    ainvs=parse_ainvs(data[3])
    label = data[0] + data[1] + data[2]
    return label, ainvs,{
        'Curves_in_the_class':data[4],
        'Isogeny_matrix':data[5]
    } 
 

def intpts(line):
    r"""
    Parses intpts files
    """
    data=split(line)
    label=data[0]
    ainvs=parse_ainvs(data[1])
    return label,{
        'ainvs': ainvs,
        'x-coordinates_of_integral_points':data[2]
        }

# NOT USED NOW!
def lookup_or_create(label, ainvs):
    r"""
    This function looks for the label, if there is an entry with that label then that entry is returned. If there is no entry with this label then a new 
    one is created and returned. 
    This prevents accidental duplications.
    """
    item=curves.find_one({'ainvs':ainvs})
    if item is None:
        return {'label':label,'ainvs':ainvs}
    elif item['label']==label: 
        print label
        return item
    else:
        print "Label in DB differs from label provided", item['label'], label
        swlabel=item['label']
        item.update({'label':label, 'swlabel':swlabel})
        curves.save(item)
        return item

#filename_base_list = ['allcurves', 'allbsd', 'allgens', 'allisog', 'intpts']
filename_base_list = ['allcurves', 'allbsd', 'allgens', 'intpts']
filename_base_list = ['allcurves']

def cmp_label(lab1,lab2):
    from sage.databases.cremona import parse_cremona_label, class_to_int
#    print lab1,lab2
    a,b,c = parse_cremona_label(lab1)
    id1 = int(a),class_to_int(b),int(c)
    a,b,c = parse_cremona_label(lab2)
    id2 = int(a),class_to_int(b),int(c)
    return cmp(id1,id2)

def comp_dict_by_label(d1,d2):
    return cmp_label(d1['label'],d2['label'])

def upload_to_db(base_path,min_N, max_N):
    allcurves_filename = 'allcurves.%s-%s'%(min_N,max_N)
    allbsd_filename = 'allbsd.%s-%s'%(min_N,max_N)
    allgens_filename = 'allgens.%s-%s'%(min_N,max_N)
    intpts_filename = 'intpts.%s-%s'%(min_N,max_N)
    file_list = [allcurves_filename, allbsd_filename, allgens_filename, intpts_filename]

    data_to_insert = {} # will hold all the data to be inserted

    for f in file_list:
        h = open(os.path.join(base_path,f))
        print "opened %s"%os.path.join(base_path,f)

        parse =  globals()[f[:f.find('.')]]

        t = time.time()
        count=0
        for line in h.readlines():
            label, data = parse(line)
            # if count%5000==0:
            #     print label
            count += 1
            if not data_to_insert.has_key(label):
                data_to_insert[label] = {'label': label}
            curve = data_to_insert[label]
            for key in data:
                if curve.has_key(key):
                    if curve[key] != data[key]:
                        raise RuntimeError, "Inconsistent data for %s"%label
                else:
                    curve[key] = data[key]
        print "finished reading %s lines from file"%count
    
    from cPickle import dumps
    #print len(dumps(data_to_insert.values()))
    vals = data_to_insert.values()
    vals.sort(cmp=comp_dict_by_label)
    count = 0
    for val in vals:
        curves.update({'label':val['label']}, val, upsert=True)
        count += 1
        if count%5000==0: print "inserted %s"%(val['label'])
    #curves.insert(data_to_insert.values())

#this code actually reads all the files and calls the appropriate function. 
# for path in sys.argv[1:]:
#     print path
#     for file in glob.glob( os.path.join(path, '*.*') ):
#         filename = os.path.basename(file)
#         base = filename[:filename.find('.')]
#         if base not in filename_base_list:
#             print "Ignoring", file
#             continue
#         print "parsing ",file
#         parse = globals()[base]
#         h = gzip.open(file) if filename[-3:] == '.gz' else open(file)
#         t = time.time()
#         for line in h.readlines():
#             label, ainvs, data = parse(line)
#             info = lookup_or_create(label,ainvs)
#             for key in data:
#                 if key not in info:
#                     if key!='gens':
#                         print "key %s not in database for label %s"%(key,label)
#                 elif data[key]!=info[key]:
#                     if not key in ['torsion_generators','torsion_structure','iso']:
#                         print "data for %s for %s differs: %s vs. %s"%(key,label,data[key],info[key])

#             # info.update(data)
#             # curves.save(info)
#             # if time.time() - t > 5:
#             #     print "\t", label
#             #     t = time.time()


