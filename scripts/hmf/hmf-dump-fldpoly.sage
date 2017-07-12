'''
script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text files including:
label, AL eigenvalues, AL fixed, base change, CM, with a_PP for bad primes appended.
'''
from pymongo.mongo_client import MongoClient
import pymongo
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb') # for read access.
hmfs = C.hmfs
fields = hmfs.fields
#fieldlabels = fields.distinct('label')
fields = C.numberfields.fields

def clean(A):
    st = str(A)
    return st.replace(' ','').replace('u\'','').replace('\'','')
fieldlabels = [
'4.4.1600.1',
'4.4.2304.1',
'4.4.4225.1',
'4.4.7056.1',
'4.4.7168.1',
'4.4.7225.1',
'4.4.9248.1',
'4.4.11025.1',
'4.4.12400.1',
'4.4.12544.1',
'4.4.13824.1',
'4.4.14336.1',
'4.4.17424.1',
'5.5.180769.1',
'6.6.1134389.1',
'4.4.19600.1',
'6.6.1528713.1',
'6.6.905177.1'
]
for Flabel in fieldlabels:
    # sample Flabel  4.4.16448.2
        query = {'label':Flabel}
        coeffs = '['+fields.find_one(query)['coeffs']+']'
        #sage: fields.find_one()['coeffs']
        #u'-2625040,6270,0,1'
        K = NumberField(PolynomialRing(QQ,'x')(sage_eval(coeffs)),'w')
        vars = {'w':K.0}
        degree = Flabel.split('.')[0]
        assert degree == str(K.degree())
        with open('data/'+degree+'/'+Flabel+'-extra.txt','r') as infile:
            with open('data/'+degree+'/'+Flabel+'-extra-plus.txt','w') as outfile:
                for line in infile:
                    # sample 3.3.1016.1-2.1-a:[2,2,w]:no:no:[[[2,2,w],-1]]:done
                    Ndata = sage_eval(line.split(':')[1].replace('^','**'), locals = vars)
                    N = K.ideal(Ndata)
                    ALdata_list = sage_eval(line.split(':')[4].replace('^','**'), locals = vars)
                    change_ap = []
                    for ALdata in ALdata_list:
                        pp = K.ideal(ALdata[0])
                        if N.valuation(pp) == 1:
                            # Need to change a_pp  !!!
                            # should be (-1)*AL_eval
                            change_ap.append([ALdata[0],-ALdata[1]])
                    alldata = [line.rstrip()] + [clean(a) for a in change_ap]
                    newdata = ':'.join(alldata)
                    outfile.write(newdata+'\n')
