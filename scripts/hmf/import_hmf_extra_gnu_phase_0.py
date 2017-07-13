# -*- coding: utf-8 -*-
Dan_test = True
import os.path

from sage.interfaces.magma import magma

from sage.all import ZZ, Rationals, PolynomialRing
if Dan_test:
    from pymongo.mongo_client import MongoClient
    C = MongoClient(port=int(37010))
    C['admin'].authenticate('lmfdb','lmfdb')
else:
    from lmfdb.lmfdb.base import getDBConnection
    C= getDBConnection()
    C['admin'].authenticate('lmfdb', 'lmfdb') # read-only

from check_conjugates import fix_one_label
from sage.databases.cremona import class_to_int

print "getting connection"
import yaml

if Dan_test:
    import sys
    from sage.all import preparse
    sys.path.append('/Users/d_yasaki/repos/lmfdb/lmfdb/scripts/hmf')
    pw_dict = yaml.load(open(os.path.join(os.getcwd(), "../../passwords.yaml")))
    username = pw_dict['data']['username']
    password = pw_dict['data']['password']
    C['hmfs'].authenticate(username, password)
else:
    import sage.misc.preparser
    from sage.misc.preparser import preparse
    pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
    username = pw_dict['data']['username']
    password = pw_dict['data']['password']
    C['hmfs'].authenticate(username, password)

hmf_forms = C.hmfs.forms_dan
hmf_fields = C.hmfs.fields

def parseALstring(s):
    # Drop first char bracket
    #in [[4,2,1/2*w^3-2*w],-1],[[191,191,-w^3-2*w^2+5*w+7],-1]] 
    #out ['[[4', '2', '1/2*w^3-2*w]', '-1]', '[[191', '191', '-w^3-2*w^2+5*w+7]', '-1]]']
    if s == '[]':
        return []
    s = s[1:-1]
    sm = s.split(',')
    outlist = []
    #print s, sm
    assert len(sm) % 4 == 0
    for i in range(len(sm)/4):
        outlist += [[sm[4*i][1:]+","+sm[4*i+1]+","+sm[4*i+2], sm[4*i+3][:-1]]]
    return outlist


def import_extra_data(hmf_extra_filename, fileprefix=None, ferrors=None, test=True):
    ''' 
    put in docstring
    '''
    if ferrors==None:
        if Dan_test:
            ferrors = file('/Users/d_yasaki/repos/lmfdb/lmfdb/scripts/hmf/fixing-permuted-primes/import_extra.err', 'a')
        else:
            ferrors = file('/home/jvoight/lmfdb/backups/import_data.err', 'a')
    field_label = hmf_extra_filename.split('-')[0]
    if fileprefix==None:
        fileprefix="."
    hmff = file(os.path.join(fileprefix,hmf_extra_filename))

    with hmff as infile:
        # assumes the input filename starts with the field label.
        F = hmf_fields.find_one({'label':field_label})
        assert F is not None
        clean_primes = [p.replace(' ','') for p in F['primes']]
        for line in infile:
            # sample line - 4.4.1600.1-25.1-a:[25,5,w^2-3]:no:yes:[[[25,5,w^2-3],1]]:done:[[25,5,w^2-3],-1]
            line_keys = ['label', 'level_ideal','is_CM','is_base_change','AL_eigenvalues','AL_eigenvalues_fixed'] 
            data = line.split(':')
            label = data[0]
            f = hmf_forms.find_one({'label':label})
            if f is None:
                continue
            assert f['field_label'] == field_label
            f['AL_eigenvalues'] = parseALstring(data[line_keys.index('AL_eigenvalues')])
            enter_keys = ['is_CM','is_base_change','AL_eigenvalues_fixed']
            for k in enter_keys:  
                f[k] = data[line_keys.index(k)]
            # need to fix some aps:  data[-1]
            # adjust f['hecke_eigenvalues']
            if len(data) > 6:
                # there are ap to fix
                for apfix in data[6:]:
                    pp = apfix.rstrip()[1:-1].split('],')[0] + ']'
                    ap = apfix.rstrip()[1:-1].split('],')[1]
                    if not ap in {'1','-1'}:
                        print '?????   ',ap,label
                    assert ap in {'1','-1'}
                    if clean_primes.index(pp) < len(f['hecke_eigenvalues']):
                        assert f['hecke_eigenvalues'][clean_primes.index(pp)] in {'0','1','-1'}
                        f['hecke_eigenvalues'][clean_primes.index(pp)] = ap
                    else:
                        print '!!! a_pp not corrected since not many stored !!!'
            if not test:
                print label
                hmf_forms.save(f)  
            else:
                print f


'''
Only used because the AL_eigenvalue parser was returning '[]' instead of [].  I fixed the 157 forms that were affected.
def onetimefix(test= True):
    tofix = hmf_forms.find({'AL_eigenvalues':'[]'})
    tofixlabels = tofix.distinct('label')
    for l in tofixlabels:
        f = hmf_forms.find_one({'label':l})
        assert f['AL_eigenvalues'] == '[]'
        f['AL_eigenvalues'] = []
        
        if not test:
            print l
            hmf_forms.save(f)
        else:
            print l
'''
