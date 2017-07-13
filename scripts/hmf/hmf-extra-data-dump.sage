
'''
script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text files including:
label, AL eigenvalues, AL fixed, base change, CM
'''
from pymongo.mongo_client import MongoClient
import pymongo
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb') # for read access.
hmfs = C.hmfs
forms = hmfs.forms
fields = hmfs.fields
fieldlabels = fields.distinct('label')

def clean(A):
    st = str(A)
    return st.replace(' ','').replace('u\'','').replace('\'','')

AL_text = set()
for Flabel in fieldlabels:
    # sample Flabel  4.4.16448.2
    wanted_keys = ['label', 'level_ideal','is_CM','is_base_change','AL_eigenvalues','AL_eigenvalues_fixed']
    degree = Flabel.split('.')[0]
    with open('data/'+degree+'/'+Flabel+'-extra.txt','w') as outfile:
        query = {'field_label':Flabel}
        res = forms.search.find(query).sort([('level_norm', pymongo.ASCENDING), ('level_label', pymongo.ASCENDING), ('label_nsuffix', pymongo.ASCENDING)])
        res_labels = [f['label'] for f in res]
        for flabel in res_labels:
            f = forms.find_one({'label':flabel})
            for a in wanted_keys:
                if not a in f.keys():
                    f[a] = 'MISSING'
                    with open('missing_data.txt','w') as missing_file:
                        dataline = ':'.join([flabel,a])
                        print 'MISSING',flabel,a
            dataline = ':'.join([clean(f[a]) for a in wanted_keys])
            AL_text.add(dataline.split(':')[-1])
            print dataline
            outfile.write(dataline + '\n')
with open('AL_text.txt','w') as ALfile:
    ALfile.write(str(AL_text))
        
