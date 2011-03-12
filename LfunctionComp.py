import re

cremona_label_regex = re.compile(r'(\d+)([a-z])+(\d*)')

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
         print 'min max', Nmin,Nmax
         for i in range(Nmin,Nmax+1):
                 ans.append([i,characterlist(i,type)])
         return(ans)

def isogenyclasstable(Nmin,Nmax):
    iso_dict = {}
    from sage.schemes.elliptic_curves.ell_rational_field import cremona_curves 
    from sage.misc.misc import srange
    for E in cremona_curves(srange(Nmin,Nmax)):        
        cond = int(cremona_label_regex.match(E.label()).groups()[0])
        iso_dict[cond] = []
    for E in cremona_curves(srange(Nmin,Nmax)):
        cond = int(cremona_label_regex.match(E.label()).groups()[0])
        id = cremona_label_regex.match(E.label()).groups()[1]
        iso_dict[cond].append(str(cond)+id)
    for cond in iso_dict:
        iso_dict[cond] = set(iso_dict[cond])
    return iso_dict
    
