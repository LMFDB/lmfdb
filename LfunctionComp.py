import re
import base
from pymongo import ASCENDING
import utils
logger = utils.make_logger("LFComp")

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
    
def nr_of_EC_in_isogeny_class(label):
    i = 1
    logger.debug(label)
    connection = base.getDBConnection()
    data = connection.elliptic_curves.curves.find_one({'label': label+ str(i)})
    logger.debug(str(data))
    while not data is None:
        i += 1
        data = connection.elliptic_curves.curves.find_one({'label': label+ str(i)})
    return i-1

def modform_from_EC(label):
     # This is only guaranteed up to 100
     N, iso, number = cremona_label_regex.match(label).groups()
     mod_form_iso=iso
     label_perm={'57b':'c', '57c':'b',
                '75a':'c', '75c':'a',
                '84a':'b', '84b':'a',
                '92a':'b', '94b':'a',
                '96a':'b', '96b':'a'}
     if label in label_perm:
         mod_form_iso=label_perm[label]
     return { 'level' : N, 'iso' : mod_form_iso}

def EC_from_modform(level, iso):
     # This is only guaranteed up to 100
     label = str(level) + iso
     EC_iso=iso
     label_perm={'57b':'c', '57c':'b',
                '75a':'c', '75c':'a',
                '84a':'b', '84b':'a',
                '92a':'b', '92b':'a',
                '96a':'b', '96b':'a'}
     if label in label_perm:
         EC_iso=label_perm[label]
     return str(level) + EC_iso


