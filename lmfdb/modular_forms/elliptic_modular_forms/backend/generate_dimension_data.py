from sage.all import dimension_new_cusp_forms,DirichletGroup
import pymongo

dbport=37010

def generate_dimension_table_gamma0(maxN=100,maxk=12):
    C=pymongo.connection.Connection(port=int(37010))
    ms=C['modularforms']['Modular_symbols.files']
    print ms
    data=dict()
    for N in range(1,maxN):
        data[N]=dict()
        for k in range(2,maxk):
            dim=dimension_new_cusp_forms(N,k)
            finds=ms.find({'t':[int(N),int(k),int(0)]})
            print finds.count()
            in_db=finds.count()>0
            data[N][k]={'dimension':dim, 'in_db':in_db}
            #print N,k,data[N][k]
    return ms,data

def generate_dimension_table_gamma1(maxN=100,maxk=12,minN=3,mink=2):
    C=pymongo.connection.Connection(port=int(37010))
    ms=C['modularforms']['Modular_symbols.files']
    print ms
    data=dict()
    for N in range(minN,maxN+1):
        data[N]=dict()
        for k in range(mink,maxk+1):
            data[N][k]=dict()
            if N > 2:
                D=DirichletGroup(N)
                G=D.galois_orbits(reps_only=True)
                dimall=0
                in_db_all=True
                for xi,x in enumerate(G):
                    dim=dimension_new_cusp_forms(x,k)
                    dimall+=dim
                    finds=ms.find({'t':[int(N),int(k),int(xi)]})
                    in_db=finds.count()>0
                    if not in_db:
                        in_db_all=False
                    data[N][k][xi]={'dimension':dim, 'in_db':in_db}
            else:
                in_db_all=True
                # we only have the trivial character
                finds=ms.find({'t':[int(N),int(k),int(0)]})
                in_db=finds.count()>0
                if not in_db:
                    in_db_all=False
                dimall=dimension_new_cusp_forms(N,k)
                data[N][k][0]={'dimension':dimall, 'in_db':in_db}
            #print N,k,data[N][k]
            data[N][k][-1]={'dimension':dimall, 'in_db':in_db_all}
        print "Computed data for level ", N
    return ms,data


