
'''
script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text files including:
label, AL eigenvalues, AL fixed, base change, CM
added in extra bits (a_pp for bad primes)
'''
from pymongo.mongo_client import MongoClient
import pymongo
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb') # for read access.
hmfs = C.hmfs
forms = hmfs.forms
fields = C.numberfields.fields
hmffields = hmfs.fields
fieldlabels = hmffields.distinct('label')

def clean(A):
    st = str(A)
    return st.replace(' ','').replace('u\'','').replace('\'','')

for Flabel in fieldlabels:
    # sample Flabel  4.4.16448.2
    wanted_keys = ['label', 'level_ideal','is_CM','is_base_change','AL_eigenvalues','AL_eigenvalues_fixed']
    degree = Flabel.split('.')[0]
    print 'Working on',Flabel,'forms.'
    with open('/Users/d_yasaki/Desktop/data/'+Flabel+'-extra-plus.txt','w') as outfile:
        query = {'field_label':Flabel}
        Fquery = {'label':Flabel}
        coeffs = '['+fields.find_one(Fquery)['coeffs']+']'
        K = NumberField(PolynomialRing(QQ,'x')(sage_eval(coeffs)),'w')
        vars = {'w':K.0}
        degree = Flabel.split('.')[0]
        assert degree == str(K.degree())
        res = forms.find(query).sort([('level_norm', pymongo.ASCENDING), ('level_label', pymongo.ASCENDING), ('label_nsuffix', pymongo.ASCENDING)])
        res_labels = [f['label'] for f in res]
        assert len(res_labels) > 0
        for flabel in res_labels:
            f = forms.find_one({'label':flabel})
            for a in wanted_keys:
                if not a in f.keys():
                    f[a] = 'MISSING'
            Ndata = sage_eval(f['level_ideal'].replace('^','**'), locals = vars)
            N = K.ideal(Ndata)
            if len(f['AL_eigenvalues']) > 0 and not f['AL_eigenvalues'] == 'MISSING':
                ALdata_list = [[sage_eval(b.replace('^','**'), locals = vars) for b in a] for a in f['AL_eigenvalues']]
            else:
                ALdata_list = []
            change_ap = []
            for ALdata in ALdata_list:
                pp = K.ideal(ALdata[0])
                if N.valuation(pp) == 1:
                    # Need to change a_pp  !!!
                    # should be (-1)*AL_eval
                    change_ap.append([ALdata[0],-ALdata[1]])
            alldata = [clean(f[a]) for a in wanted_keys] + [clean(a) for a in change_ap]
            newdata = ':'.join(alldata)
            print flabel
            outfile.write(newdata + '\n')

