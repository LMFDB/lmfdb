# -*- coding: utf-8 -*-
import sys, time

import sage.all
from sage.all import gap

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

def tf(val):
  if val:
    return 1
  return 0

from jjgals  import gals # this reads in the list called quads

print "finished importing gals, number = %s"%len(gals)

#for deg in [3,4,5]:
for deg in range(1,len(gals)):
#for deg in None:
  d = gals[deg]
  for myg in range(len(d)):
    n=deg+1
    t = myg+1
    g = gap.TransitiveGroup(n, t)
    gal = d[myg]
    solv = tf(g.IsSolvable())
    prim = tf(g.IsPrimitive())
    cyc = tf(g.IsCyclic())
    ab = tf(g.IsAbelian())
    pretty = None
    if len(gal)>700 :
      pretty = gal[700]
    data = {
        'n': n,
        't': t,
        'cyc': cyc,
        'ab': ab,
        'solv': solv,
        'prim': prim,
        'parity': gal[2],
        'order': gal[1],
        'name': gal[4],
        'auts': gal[3],
        'repns': gal[6],
        'resolve': gal[5],
        'subs': gal[7],
        'pretty': pretty
    }

    label = base_label(n,t)
    group = groups.find_one({'label': label})

    if group:
        print "old group"
        if 'pretty' in group:
          del data['pretty']
        group.update(data)
        print "entering %s"%group
        groups.save(group)
    else:
        print "new group"
        info =  {'label': label}
        info.update(data)
        print "entering %s into database"%info
        groups.save(info)

