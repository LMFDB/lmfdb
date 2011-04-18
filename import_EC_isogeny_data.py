import os.path, gzip, re, sys, time
import pymongo
import base

conn = base.getDBConnection()
isogeny=conn.ellcurves.isogeny
curves=conn.ellcurves.curves

def allisog(line):
    r"""
    Parses allisog files
    """
    data=split(line)
    label = data[0] + data[1]
    label_of_curves_in_the_class=[a['label'] for a in curves.find({'iso':label})]
    E=EllipticCurve(eval(data[3]))
    return label, {
        'ainvs_for_optimal_curve':data[3]
        'label_of_curves_in_the_class':label_of_curves_in_the_class,
        'isogeny_matrix':str(list(E.isogeny_class()[-1]))
    }
    
def lookup_or_create_isogeny(label):
    item = isogeny.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item    
        

def degphi(line):
    r"""
    Parses degphi files
    """
    data=split(line)
    label = data[0] + data[1]
    return label, {
        'degree':data[3]
    }
            
def allcurves(line):
    r"""
    Parses degphi files
    """
    data=split(line)
    label = data[0] + data[1]
    if int(data[2])==1:
        return label, {
            'rank':data[4]
    else:
        return
    }

 
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
            label, data = parse(line)
            info = lookup_or_create_isogeny(label)
            if info=None:
                continue
            else:
                info.update(data)
                isogeny.save(info)
                if time.time() - t > 5:
                    print "\t", label
                    t = time.time()
    