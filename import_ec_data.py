r"""
Import data from Cremona tables.
Note: This code can be run on all files in any order. Even if you rerun this code on previously entered files, it should have no affect. 
This code checks if the entry exists, if so returns that and updates with new information. If the entry does not exist then it creates it and 
returns that. 

Initial version (Paris 2010)
More tables Feb 2010 Gagan Sekhon
Needed importing code for Stein-Watkins 
"""


import os.path, gzip, re, sys, time, os, random,glob
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


def parse_tgens(s):
    r"""
    Converts projective coordinates to affine coordinates for generator
    """  
    g1=s.replace('(', ' ').replace(')',' ').split(':')
    g=[eval(g1[0]),eval(g1[1])]
    return str(tuple(g))


def ainvs_1(s):
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
    ainvs=ainvs_1(data[3])
    return label,ainvs, {
        'conductor': int(data[0]),
        'iso': data[0]+data[1],
        'number': int(data[2]),
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
    ainvs=ainvs(data[3])
    return label,ainvs, {
        'conductor': int(data[0]),
        'iso': data[0]+data[1],
        'number': int(data[2]),
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
    ainvs=ainvs(data[3])
    if torsion>0:
        return label,ainvs, {
            'conductor': int(data[0]),
            'iso': data[0]+data[1],
            'number': int(data[2]),
            'rank': int(data[4]),
            'gens': ["(%s)" % gen[1:-1] for gen in data[6:6+rank]],
            'torsion_structure':["%s" %tor for tor in eval(data[5])],
            'torsion_generators':["%s" %parse_tgens(tgens[1:-1]) for tgens in data[6+rank:]],
        }
    else:
        return label,ainvs, {
            'conductor': int(data[0]),
            'iso': data[0]+data[1],
            'number': int(data[2]),
            'rank': int(data[4]),
            'gens': ["(%s)" % gen[1:-1] for gen in data[6:6+rank]],
            'torsion_structure':[],
            'torsion_generators':["(%s)" %parse_tgens(tgens[1:-1]) for tgens in data[6+rank:]],
        }
        
#def degphi(line):
#    data=split(line)
#    label = data[0] + data[1] + data[2]
#    return label, {
#        'degree':data[3]
#    }
    
def allisog(line):
    data=split(line)
    ainvs=ainvs(data[3])
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
    ainvs=ainvs(data[1])
    return label, ainvs,{
    'x-coordinates_of_integral_points':data[2]
    }
        
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
        print item['label'], label
        swlabel=item['label']
        item.update({'label':label, 'swlabel':swlabel})
        curves.save(item)
        return item
        
#this code actually reads all the files and calls the appropriate function. 
for path in sys.argv[1:]:
    print path
    for file in glob.glob( os.path.join(path, '*.*') ):
        filename = os.path.basename(file)
        base = filename[:filename.find('.')]
        if base not in globals():
            print "Ignoring", file
            continue
        parse = globals()[base]
        h = gzip.open(file) if filename[-3:] == '.gz' else open(file)
        t = time.time()
        for line in h.readlines():
            label, ainvs, data = parse(line)
            info = lookup_or_create(label,ainvs)
            info.update(data)
            curves.save(info)
            if time.time() - t > 5:
                print "\t", label
                t = time.time()
