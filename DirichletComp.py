import re

#cremona_label_regex = re.compile(r'(\d+)([a-z])+(\d*)')

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

    
