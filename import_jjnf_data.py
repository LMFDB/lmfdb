import sys, time

from pymongo.connection import Connection
fields = Connection(port=37010).numberfields.fields

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

from done2  import quads # this reads in the list called quads

print "finished importing quads, number = %s"%len(quads)

for F in quads:
    print F
    t = time.time()
    d, sig, D, coeffs, h, cyc, GG = F
    absD = abs(D)
    data = {
        'degree': d,
        'signature': sig,
        'discriminant': D,
        'coefficients': coeffs,
        'class_number': h,
        'class_group': cyc,
        'galois_group': GG
    }

    index=1
    is_new = True
    for field in fields.find({'degree': d, 
                 'signature': sig,
                 'discriminant': D}):
        index +=1
        if field['coefficients'] == coeffs:
            is_new = False
            break

    if is_new:
        print "new field"
        label = base_label(d,sig[0],absD,index)
        info =  {'label': label}
        info.update(data)
        print "entering %s into database"%info
        fields.save(info)
    else:
        print "field already in database"
    if time.time() - t > 5:
        print "\t", label
        t = time.time()

