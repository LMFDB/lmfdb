import sys, time

from pymongo.connection import Connection
groups = Connection(port=37010).transitivegroups.groups

groups.ensure_index('n')
groups.ensure_index('t')

# Import information in the a database of transitive groups

def base_label(n,t):
    return str(n)+"T"+str(t)

def lookup_or_create(label):
    item = None # fields.find_one({'label': label})
    if item is None:
        return {'label': label}
    else:
        return item

from jjgals  import gals # this reads in the list called quads

print "finished importing gals, number = %s"%len(gals)

for deg in range(len(gals)):
  d = gals[deg]
  for g in range(len(d)):
    gal = d[g]
    print gal
    cyc = gal[0]
    ab = gal[1]
    solv = gal[2]
    prim = gal[3]
    parity = gal[4]
    order = gal[5]
    name = gal[6]
    n=deg+1
    t = g+1
    pretty = None
    if len(gal)>7 :
      pretty = gal[7]
    data = {
        'n': n,
        't': t,
        'cyc': cyc,
        'ab': ab,
        'solv': solv,
        'prim': prim,
        'parity': parity,
        'order': order,
        'name': name,
        'pretty': pretty
    }

    label = base_label(n,t)
    group = groups.find_one({'label': label})

    if group:
        print "old group"
        group.update(data)
        groups.save(group)
    else:
        print "new group"
        info =  {'label': label}
        info.update(data)
        print "entering %s into database"%info
        groups.save(info)

