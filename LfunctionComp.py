import re
import base
from pymongo import ASCENDING

from elliptic_curve import cremona_label_regex

def characterlist(N,type):
     from sage.modular.dirichlet import DirichletGroup
     G = DirichletGroup(N)
     primitive = []
     all = []
     for i in range(len(G)):
         if G[i].is_primitive():
              primitive.append(i)
         all.append(i)
     if type=="primitive":
         return(primitive)
     else:
         return(all)

         #else:
          #    nonprimitive.append(i+1)
     #return primitive, nonprimitive
     return N, output

def charactertable(Nmin,Nmax,type):
         ans=[]
         logging.info('min %s, max %s' % (Nmin,Nmax))
         for i in range(Nmin,Nmax+1):
                 ans.append([i,characterlist(i,type)])
         return(ans)

def isogenyclasstable(Nmin,Nmax):
    iso_list = []

    query = {'number': 1, 'conductor': {'$lte': Nmax, '$gte': Nmin}}

    # Get all the curves and sort them according to conductor
    cursor = base.getDBConnection().elliptic_curves.curves.find(query)
    res = cursor.sort([('conductor', ASCENDING), ('lmfdb_label', ASCENDING)])

    iso_list = [E['lmfdb_iso'] for E in res]

    return iso_list
    
