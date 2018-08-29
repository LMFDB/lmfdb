# -*- coding: utf-8 -*-
r""" Correct in_db flags for modular forms dimension tables.

Initial version (University of Warwick 2015) Aurel Page

"""

import os
import sys
sys.path.append("../../../..")
import yaml
from lmfdb.base import getDBConnection
from web_modform_space import WebModFormSpace_cached
from sage.all import Infinity

C = getDBConnection()
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml"))) #FIXME
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['modularforms2'].authenticate(username, password)
C['numberfields'].authenticate(username, password)

print "setting db_mf and db_dim"
db_mf = C.modularforms2
db_dim = db_mf.dimension_table

def check_inwdb(dimdata):
    level = dimdata['level']
    weight = dimdata['weight']
    character = dimdata.get('cchi',1)
    try:
        WMFS = WebModFormSpace_cached(level = level, weight = weight, cuspidal=True,character = character)
    except (RuntimeError,ValueError):
        return int(0)
    if WMFS == None:
        return int(0)
    #print WMFS, WMFS.dimension_new_cusp_forms, WMFS.hecke_orbits
    dim = dimdata['d_newf']
    if WMFS.dimension_new_cusp_forms != dim:
        return int(0)
    if dim>0 and WMFS.hecke_orbits == {}:
        return int(0)
    return int(1)

def correct_inwdb(dimdata, fix=False):
    is_in_wdb = check_inwdb(dimdata)
    if not dimdata.has_key('in_wdb'):
        print "this dimdata has no in_wdb field level:", dimdata['level'], "weight:", dimdata['weight']
        return
    print "dimdata:", dimdata['in_wdb'], "correct:", is_in_wdb
    if is_in_wdb != dimdata['in_wdb']:
        dimdata['in_wdb'] = is_in_wdb
        query = {'_id':dimdata['_id']}
        if fix:
            print "fixing"
            db_dim.update(query,dimdata)
        else:
            print "Not fixing:{0},{1}".format(query,dimdata)

def correct_all_inwdb(maxlevel=Infinity, maxweight=Infinity, fix=False):
    query = {}
    if maxlevel < Infinity:
        query['level'] = {'$lt':int(maxlevel+1)}
    if maxweight < Infinity:
        query['weight'] = {'$lt':int(maxweight+1)}
    dims = db_dim.find(query)
    for dimdata in dims:
        print dimdata
        correct_inwdb(dimdata, fix=fix)
