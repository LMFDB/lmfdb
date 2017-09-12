# -*- coding: utf-8 -*-
""" Complete the entries for orbits of a given Hecke algebra.

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
hecke_orb = C['hecke_algebras'].hecke_algebras_orbits


def do_import(ll):
    Zbasis,discriminant,disc_fac,Qbasis,Qalg_gen=ll
    mykeys = ['Zbasis','discriminant','disc_fac','Qbasis','Qalg_gen']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
    data['Zbasis']=[[str(i) for i in j] for j in data['Zbasis']]
    data['discriminant']=str(data['discriminant'])
    data['disc_fac']=[[str(i) for i in j] for j in data['disc_fac']]
    data['Qbasis']=[int(i) for i in data['Qbasis']]
    data['Qalg_gen']=[int(i) for i in data['Qalg_gen']]
    return data


def check_orbit_data(orbit_label, ll, fix=False):
    query = {}
    query['orbit_label'] = str(orbit_label)

    if hecke_orb.find(query).count()>1:
        print "Check the orbit %s: multiple label assigned" %orbit_label
    else:
        orb = hecke_orb.find_one(query)
        print("Hecke orbit with label %s" % (orbit_label))
        if orb is None:
            print "No orbit"
            return None
        print "Checking whether the data is stored..." 
        if 'Zbasis' not in orb.keys():
            print("NOT stored")
            if fix:
                d=do_import(ll);
                hecke_orb.update({"_id": orb["_id"]}, {"$set":{'Zbasis':d['Zbasis'],'discriminant':d['discriminant'],'disc_fac':d['disc_fac'],'Qbasis':d['Qbasis'],'Qalg_gen':d['Qalg_gen']}}, upsert=True)
                print("Fixed orbit label %s" % (orbit_label))
        else:
            print("Already stored")
