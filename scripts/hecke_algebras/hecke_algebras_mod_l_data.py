# -*- coding: utf-8 -*-
""" Complete the entries for l aidc orbits of Hecke algebra adding stucture data if needed.

Author: Samuele Anni
"""

import os

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['hecke_algebras'].authenticate('editor', password)
hecke_orb_l = C['hecke_algebras'].hecke_algebras_l_adic



def do_import(ll):
    field,structure,properties,operators= ll
    mykeys = ['field','structure','properties','operators']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
    for i in [0,1,3]:
        data['field'][i]=int(data['field'][i])
    data['field'][2]=str(data['field'][2])
    for i in [0,1]:
        data['structure'][i]=int(data['structure'][i])
    for i in [2,3]:
        data['structure'][i]=str(data['structure'][i])
    data['properties'][0]=[int(i) for i in data['properties'][0]]
    data['properties'][1]=int(data['properties'][1])
    data['operators']=[[int(i) for i in j] for j in data['operators']]
    return data


def check_mod_l_data(orbit_label, index, ell, ll, fix=False):
    query = {}
    query['orbit_label'] = str(orbit_label)
    query['ell'] = int(ell)
    query['index'] = int(index)

    orb_set = hecke_orb_l.find(query)
    print("%s Hecke orbits to examine with orbit label %s for ell = %s" % (orb_set.count(), orbit_label, ell))
    if orb_set.count() == 0:
        return None
    print("Checking whether the mod %s data is stored..." %ell)
    for o in orb_set:
        print("Testing orbit index %s" % o['index'])
        if 'structure' not in o.keys():
            print("NOT stored")
            if fix:
                d=do_import(ll);
                print d;
                hecke_orb_l.update({"_id": o["_id"]}, {"$set":{'field': d['field'], 'structure': d['structure'],'properties': d['properties'], 'operators': d['operators']}}, upsert=True)
                print("Fixed orbit label %s index %s" % (orbit_label, o['index']))
        else:
            print("Already stored")
