# -*- coding: utf-8 -*-
r""" Checking that knowls only cross-reference existing knowls

Initial version (Bristol March 2016)

"""
import os.path
import os

from lmfdb.website import DEFAULT_DB_PORT as dbport
from pymongo.mongo_client import MongoClient
print "getting connection"
C= MongoClient(port=dbport)
print "authenticating on the knowledge database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['knowledge'].authenticate(username, password)
print "setting knowls"
knowls = C.knowledge.knowls

cats = knowls.distinct('cat')
print("There are %s categories of knowl in the database" % len(cats))

def check_knowls(cat='ec', verbose=False):
    cat_knowls = knowls.find({'cat': cat})
    if verbose:
        print("%s knowls in category %s" % (cat_knowls.count(),cat))
    for k in cat_knowls:
        if verbose:
            print("Checking knowl %s" % k['_id'])
        cont = k['content']
        i = 0
        while (i>=0):
            i = cont.find("KNOWL_INC")
            if i>=0:
                offset = 10
            else:    
                i = cont.find("KNOWL")
                if i>=0:
                    offset=6
            if (i>=0):
                cont = cont[i+offset:]
                qu = cont[0]
                j = cont.find(qu,1)
                ref = cont[1:j]
                if verbose:
                    print("..cites %s" % ref)
                cont = cont[j+1:]
                the_ref = knowls.find_one({'_id':ref})
                if the_ref==None:
                    print("Non-existing reference to %s in knowl %s" % (ref,k['_id']))
                elif verbose:
                    print("--- found")

"""
Result of running

sage: for cat in cats:
    check_knowls(cat, verbose=False)

on 30 March 2016:

Non-existing reference to ag.base_change in knowl ag.geom_simple
Non-existing reference to ag.dual_variety in knowl ag.ppav
Non-existing reference to doc.LMFDB.database in knowl doc.lmfdb.contextualize
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to ag.good_reduction in knowl g2c.lfunction
Non-existing reference to hgm.tame in knowl hgm.conductor
Non-existing reference to lfunction.normalization in knowl lfunction.central_value
Non-existing reference to mf.elliptic.hecke_operator in knowl mf.elliptic.coefficient_field
Non-existing reference to test.nonexisting in knowl test.text
"""
