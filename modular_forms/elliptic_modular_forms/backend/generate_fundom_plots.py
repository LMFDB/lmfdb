
import pymongo
from sage.all import dumps
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
dbport=37010

def generate_fundom_plots(minN=1,maxN=10,group='Gamma0'):
    C=pymongo.connection.Connection(port=int(37010))
    gps=C['SL2Zsubgroups']['groups']
    for N in range(minN,maxN+1):
        if group=='Gamma0':
            G=Gamma0(N)
            grouptype=int(0)
        else:
            G=Gamma1(N)
            grouptype=int(1)
        dom=draw_fundamental_domain(N,group)
        filename='domain' + str(N) + '.png'
        save(dom,filename)
        data=open(filename).read()
        idins=gps.insert({'level':int(N), 'index':int(G.index()), 'G':pymongo.binary.Binary(dumps(G)), 'domain':pymongo.binary.Binary(data), 'type':grouptype})
        print "inserted: ", N, " ", idins
        
        
        
