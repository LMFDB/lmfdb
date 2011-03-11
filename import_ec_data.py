r"""
Import data from Cremona tables.
Note: This code can be run on all files in any order. Even if you rerun this code on previously entered files, it should have no affect. 
This code checks if the entry exists, if so returns that and updates with new information. If the entry does not exist then it creates it and 
returns that. 

Initial version (Paris 2010)
More tables Feb 2010 Gagan Sekhon
Needed importing code for Stein-Watkins 
"""


import os.path, gzip, re, sys, time
import pymongo
import base

conn = base.getDBConnection()
curves = conn.ellcurves.curves
#The following ensure_index command checks if there is an index on label, conductor, rank and torsion. If there is no index it creates one. 
#Need: once torsion structure is computed, we should have an index on that too. 

curves.ensure_index('label')
curves.ensure_index('conductor')
curves.ensure_index('rank')
curves.ensure_index('torsion')
curves.ensure_index('torsion_structure')


def ainvs(s):
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
    return label, {
        'conductor': int(data[0]),
        'iso': data[1],
        'number': int(data[2]),
        'ainvs': ainvs(data[3]),
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
    return label, {
        'conductor': int(data[0]),
        'iso': data[1],
        'number': int(data[2]),
        'ainvs': ainvs(data[3]),
        'rank': int(data[4]),
        'torsion': int(data[5]),
    }

def allgens(line):
r"""
Parses allgens files
"""
    data = split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'conductor': int(data[0]),
        'iso': data[1],
        'number': int(data[2]),
        'ainvs': ainvs(data[3]),
        'rank': int(data[4]),
        'gens': ["(%s)" % gen[1:-1] for gen in data[5:]],
    }

def degphi(line):
r"""
Parses degphi files
"""
    data=split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'degree':data[3]
    }
    
def allisog(line):
r"""
Parses allisog files
"""
    data=split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'Curves_in_the_class':data[4],
        'Isogeny_matrix':data[5]
    } 

def intpts(line):
r"""
Parses intpts files
"""
    data=split(line)
    label=data[0]
    return label, {
    'x-coordinates_of_integral_points':data[2]
    }
        
def lookup_or_create(label):
r"""
This function looks for the label, if there is an entry with that label then that entry is returned. If there is no entry with this label then a new 
one is created and returned. 
This prevents accidental duplications.
"""
    item = curves.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

#this code actually reads all the files and calls the appropriate function. 
for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    base = filename[:filename.find('.')]
    if base not in globals():
        print "Ignoring", path
        continue
    parse = globals()[base]
    h = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    t = time.time()
    for line in h.readlines():
        label, data = parse(line)
        info = lookup_or_create(label)
        info.update(data)
        curves.save(info)
        if time.time() - t > 5:
            print "\t", label
            t = time.time()

