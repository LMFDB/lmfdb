# -*- coding: utf-8 -*-
import sys, time
import bson
import sage.all
from sage.all import *

sys.path.append("../")
import base
from pymongo.connection import Connection
base._init(37010,"")
C = base.getDBConnection()
import pymongo

gr = C.transitivegroups.groups


saving = True

def make_label(n,t):
  return str(n)+'T'+str(t)

# Data comes as a list of lists
from outlist  import li # this reads in the list called li

tot = len(li)
print "finished importing li, number = %s"% tot
count = 0

n=0
for F in li:
  n += 1
  for g in F:
    count += 1
    print "%d"% count
    t, order, parity, auts, name, res, other, subs = g
    lab = make_label(n,t)
    g1 = gr.find_one({'label': lab})

    if g1 is None:
      print "new group %s" % lab
      myg = gap.TransitiveGroup(n,t)
      ab = 1 if myg.IsAbelian() else 0
      cyc = 1 if myg.IsCyclic() else 0
      prim = 1 if myg.IsPrimitive() else 0
      solv = 1 if myg.IsSolvable() else 0
      info =  {
        'label': lab,
        'n': n,
        't': t,
        'auts': auts,
        'order': order,
        'parity': parity,
        'ab': ab,
        'prim': prim,
        'cyc': cyc,
        'solv': solv,
        'subs': subs,
        'repns': other,
        'resolve': res,
        'pretty': None,
        'name': name
        }
      if saving:
        print "Saved"
        gr.save(info)
    else:
      print "group %s already in database" % lab

