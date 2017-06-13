'''
script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text files describing the number of a_p that are in that database.  Modify as needed. 
'''
from pymongo.mongo_client import MongoClient
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb')
hmfs = C.hmfs
forms = hmfs.forms
fields = hmfs.fields
flabels = fields.distinct('label')
with open('numap2-done-fields.txt','w') as donefile:
    with open('hmf-numap-Np-missing.txt','w') as datafile:
        for flabel in flabels:
            F = fields.find_one({'label':flabel})
            primes = F['primes']
            for f in forms.find({'field_label':flabel}):
                num_ap = len(f['hecke_eigenvalues'])
                discrepancy = len(primes) - num_ap
                Np = F['primes'][num_ap - 1].split(',')[0][1:]  #already a string
                datafile.write(':'.join([f['label'],str(num_ap),Np,str(discrepancy)])+'\n')
            donefile.write(flabel+'\n')
