import os.path, gzip, re, sys, time
import pymongo
import base

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


#load "/home/john/trnf.py"
assert len(deg6fields)==429
assert len(deg7fields)==147
assert len(deg8fields)==164
assert len(deg9fields)==15
assert len(deg10fields)==792

R = PolynomialRing(QQ,'x')
global old_D
global ind
global GGlist

def process(f):
    global old_D
    global ind
    global GGlist
    D = f[0]           # the discriminant
    if D==old_D:       # repeat, increment index 
        ind = ind+1
    else:              # new discriminant, reset index to 1
        ind = 1
        old_D = D
        
    coeffs = f[1]
    r1 = len(coeffs)-1
    d = int(r1)
    sig = [d,0]
    F = NumberField(R(coeffs),'a')
    assert F.discriminant() == D
    h = int(F.class_number())
    cyc = [int(i) for i in F.class_group().invariants()]
    label = base_label(d,r1,D,ind)
    G = F.galois_group('pari').group()
    if d<10:
        GG = eval(str(G)[11:][:-12])
    else:
        GG = eval(str(G)[11:][:-13])
    if d==6:
        if GG[2] in [1,3,5,7,11,13,16]: GG[2]=1
        if GG[2] in [2,6]: GG[2]=2
    if d==7:
        if GG==[5040, -1, 7, 'S7']:
            GG = [5040, -1, 1, 'S7']
        if GG==[14, -1, 2, 'D(7) = 7:2']:
            GG = [14, -1, 1, 'D(7) = 7:2']
    if G.is_abelian(): print GG
#    print GG
#    GGlist = GGlist.union(Set([tuple(GG)]))
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
    item = None
#    item = fields.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

for batch in [deg6fields, deg7fields, deg8fields, deg9fields, deg10fields]:
    t = time.time()
    global GGlist
    global old_D
    global ind
    old_D = 0
    ind = 0
    GGlist = Set([])
    for data in batch:
#        print "parsing data ",data
        label, data = process(data)
#        print "base label = ",label
        info = lookup_or_create(label)
        info.update(data)
#        print info
#        fields.insert(info)
#        fields.remove(info)
        if time.time() - t > 5:
            print "\t", label
            t = time.time()

