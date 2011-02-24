import os.path, gzip, re, sys, time, base

fields = base.getDBConnection().numberfields.fields
fields.ensure_index('degree')
fields.ensure_index('galois_group')
fields.ensure_index('signature')
fields.ensure_index('discriminant')
fields.ensure_index('class_number')
fields.ensure_index([('degree',pymongo.ASCENDING),('discriminant',pymongo.DESCENDING)])
fields.ensure_index([('degree',pymongo.ASCENDING),('discriminant',pymongo.ASCENDING)])



def coeffs(s):
    return [a for a in s[1:-1].split(',')]

def base_label(d,r1,D,ind):
    return str(d)+"."+str(r1)+"."+str(abs(D))+"."+str(ind)

def parse_xall(line):
    data = eval(line)
    d, r1, GG, D, ind, coeffs, h, cyc = eval(line)
    label = base_label(d,r1,D,ind)
    sig = [r1,(d-r1)/2]   
    return label, {
        'degree': d,
        'signature': sig,
        'discriminant': D,
        'coefficients': coeffs,
        'class_number': h,
        'class_group': cyc,
        'galois_group': GG
    }


def lookup_or_create(label):
    item = None # fields.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    h = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    t = time.time()
    for line in h.readlines():
#        print "parsing line ",line
        label, data = parse_xall(line)
#        print "base label = ",label
        info = lookup_or_create(label)
        info.update(data)
        fields.save(info)
        if time.time() - t > 5:
            print "\t", label
            t = time.time()

