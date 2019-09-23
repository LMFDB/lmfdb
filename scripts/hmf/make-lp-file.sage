'''
script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text that defines the Hecke polynomials for weight [2,2] HMFs over readl quadratic fields
'''
import os
import subprocess
import pymongo

#P = subprocess.Popen(["ssh","mongo","-N"])
_C = None

def makeDBconnection():
    global _C

    _C = pymongo.MongoClient("localhost:37010");
    #_C = pymongo.MongoClient("m0.lmfdb.xyz:27017");
    _C.admin.authenticate("lmfdb","lmfdb")
	
def getDBconnection():
    if _C is None:
        makeDBconnection()
    return _C

def get_hmf(label):
    C = getDBconnection()
    return C.hmfs.forms.find_one({ u'label' : label })

def get_hmf_field(label):
    C = getDBconnection()
    f = get_hmf(label)
    F = C.hmfs.fields.find_one({u'label':f['field_label']})
    return F

def get_field(label):
    C = getDBconnection()
    F = C.numberfields.fields.find_one({u'label':label})
    return F

def make_lp(form_label):
    f = get_hmf(form_label)
    prec = 350
    F_hmf = get_hmf_field(form_label)
    R = QQ['x']
    (x,) = R._first_ngens(1)
    K = NumberField(R(str(f['hecke_polynomial']).replace('^', '**')), 'e')
        # e = K.gens()[0]
    for emb in range(K.degree()):
        iota = K.complex_embeddings(prec)[emb] # a bit of overkill  
        
        # for level>1, calculate sign from Fricke involution and weight
        ALeigs = [al[1].replace('^', '**') for al in f['AL_eigenvalues']]
        # the above fixed a bug at
        # L/ModularForm/GL2/TotallyReal/2.2.104.1/holomorphic/2.2.104.1-5.2-c/0/0/
        # but now the sign is wrong (i.e., not of absolute value 1 *)
        AL_signs = [iota(K(str(al))) for al in ALeigs]
        # Compute Dirichlet coefficients
        hecke_eigenvalues = [iota(K(str(ae))) for ae in f['hecke_eigenvalues']]
        primes = [pp_str.split(', ') for pp_str in F_hmf['primes']]
        primes = [[int(pp[0][1:]), int(pp[1])] for pp in primes]
        primes = [[pp[0], pp[1], factor(pp[0])[0][1]] for pp in primes]
        
        PP = primes[-1][0]
        
        ppmidNN = [c[0].replace(' ','') for c in f['AL_eigenvalues']]   # removed extraneous spaces
        
        ratl_primes = [p for p in range(primes[-1][0] + 1) if is_prime(p)]
        CC = ComplexField(prec)
        RCC = CC['T']
        (T,) = RCC._first_ngens(1)
        heckepols = [RCC(1) for p in ratl_primes]
        # !!! DANGER primes are stored as strings!!!
        sanitized_F_hmf_primes = [pp.replace(' ','') for pp in F_hmf['primes']] # removed extraneous spaces
        for l in range(len(hecke_eigenvalues)):
            if sanitized_F_hmf_primes[l] in ppmidNN:
                heckepols[ratl_primes.index(primes[l][1])] *= (1 - hecke_eigenvalues[l] * (T ** primes[l][2]))
            else:
                heckepols[ratl_primes.index(primes[l][1])] *= (1 - hecke_eigenvalues[l]  * (T ** primes[l][2]) + primes[l][0]* (T ** (2 * primes[l][2]))) 
        # polynomials are computed.  Spit out to text file.
        with open(form_label + '-lpoly-' + str(emb) + '.txt','w') as outfile:
            for i in range(len(heckepols)):
                poly = heckepols[i]
                rat_p = ratl_primes[i]
                dataline =  str(rat_p)+','+str([[a.real_part(), a.imag_part()] for a in poly.coefficients(sparse = false)]) + '\n'
                outfile.write(dataline)
