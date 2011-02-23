import os.path, gzip, re, sys, time
import pymongo
from pymongo import Connection

curves = Connection(port=37010).ellcurves.curves
curves.create_index('label')
curves.create_index('conductor')
curves.create_index('rank')
curves.create_index('torsion')


def ainvs(s):
#    return [int(a) for a in s[1:-1].split(',')]
    return [a for a in s[1:-1].split(',')]

def parse_gens(s):
    return [int(a) for a in s[1:-1].split(':')]

whitespace = re.compile(r'\s+')
def split(line):
    return whitespace.split(line.strip())

def allbsd(line):
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
    data=split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'degree':data[3]
    }
    
def allisog(line):
    data=split(line)
    label = data[0] + data[1] + data[2]
    return label, {
        'Curves_in_the_class':data[4],
        'Isogeny_matrix':data[5]
    } 

def intpts(line):
    data=split(line)
    label=data[0]
    return label, {
    'x-coordinates_of_integral_points':data[2]
    }
        
def lookup_or_create(label):
    item = curves.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

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

