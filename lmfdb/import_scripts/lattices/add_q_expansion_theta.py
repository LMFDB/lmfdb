# -*- coding: utf-8 -*-
r""" Check presence if the first 150 coefficients of the q expansion of the theta series attached to an integral lattice are stored, and adds them otherwise.

Initial version: Samuele Anni

"""

import sys, time
import re
import json
import sage.all
from sage.all import os

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
C['Lattices'].authenticate('editor', '282a29103a17fbad')
lat = C.Lattices.lat

def check_add_Q_exp(dim, min_det=1, max_det=None, fix=False):
    count = 0
    query = {}
    query['dim'] = int(dim)
    query['det'] = {'$gte' : int(min_det)}
    if max_det:
        query['det']['$lte'] = int(max_det)
    else:
        max_det = oo
    lat_set = lat.find(query)
    print("%s lattices to examine of dimension %s and determinant between %s and %s."
          % (lat_set.count(), dim, min_det, max_det))
    if lat_set.count() == 0:
        return None
    print("checking wheter the q expansion is stored...")
    for l in lat_set:
        print("Testing form %s" % l['label'])
        if l['theta_series'] == None:
                print("q expansion NOT stored")
                if fix:
                    




fg = conjform(f, g, ig, cideals, cprimes, F)
                    if fg != None: #else: is a lift (self-conjugate), should have been detected
                        print("adding it : "+fg['label'])
                        forms.insert(fg)
                        count += 1
        else:
            print("q expansion stored")

    print("\nAdded "+str(count)+" new conjugate forms.")
    return None


#def fix_data_fields(min_level_norm=0, max_level_norm=None, fix=False):
#    r""" One-off utility to:
#    1. add degree and disc fields for each Hilbert newform
#    2. Change CM and base-change from "yes?" to "yes"
#    """
#    count = 0
#    query = {}
#    query['level_norm'] = {'$gte' : int(min_level_norm)}
#    if max_level_norm:
#        query['level_norm']['$lte'] = int(max_level_norm)
#    else:
#        max_level_norm = oo
#    forms_to_fix = forms.find(query)
#    print("%s forms to examine of level norm between %s and %s."
#          % (forms_to_fix.count(),min_level_norm,max_level_norm))
#    if forms_to_fix.count() == 0:
#        return None
#    for f in forms_to_fix:
#        count = count+1
#        if count%100==0: print("%s: %s" % (count, f['label']))
#        fix_data = {}
#        deg, r, disc, n = f['field_label'].split('.')
#        fix_data['deg'] = int(deg)
#        fix_data['disc'] = int(disc)
#        if f['is_CM'] == 'yes?':
#            fix_data['is_CM'] = 'yes'
#        if f['is_base_change'] == 'yes?':
#            fix_data['is_base_change'] = 'yes'
#        #print("using fixed data %s for form %s" % (fix_data,f['label']))
#        if fix:
#            forms.update({'label': f['label']}, {"$set": fix_data}, upsert=True)

#def fix_one_label(lab, reverse=False):
#    r""" If lab has length 1 do nothing.  If it has length 2 increment the
#    first letter (a to b to c to ... to z).  The lenths must be at
#    most 2 and if =2 it must start with 'a'..'y' (these are all which
#    were required).  If reverse==True the inverse operation is carried
#    out (z to y to ... to c to b to a).
#    """
#    if len(lab)!=2:
#        return lab
#    else:
#        if reverse:
#            return chr(ord(lab[0])-int(1))+lab[1]
#        else:
#            return chr(ord(lab[0])+int(1))+lab[1]

#def fix_labels(min_level_norm=0, max_level_norm=None, fix=False, reverse=False):
#    r""" One-off utility to correct labels 'aa'->'ba'->'ca', ..., 'az'->'bz'->'cz'
#    """
#    count = 0
#    query = {}
#    query['level_norm'] = {'$gte' : int(min_level_norm)}
#    if max_level_norm:
#        query['level_norm']['$lte'] = int(max_level_norm)
#    else:
#        max_level_norm = oo
#    forms_to_fix = forms.find(query)
#    print("%s forms to examine of level norm between %s and %s."
#          % (forms_to_fix.count(),min_level_norm,max_level_norm))
#    if forms_to_fix.count() == 0:
#        return None
#    for f in forms_to_fix:
#        count = count+1
#        if count%100==0: print("%s: %s" % (count, f['label']))
#        fix_data = {}
#        lab = f['label_suffix']
#        if len(lab)==1:
#            continue
#        if f['label'][-2:] != lab:
#            print("Incorrect label_suffix %s in form %s" % (lab,f['label']))
#            return
#        oldlab = lab
#        lab = fix_one_label(lab, reverse=reverse)
#        fix_data['label_suffix'] = lab
#        fix_data['label'] = f['label'].replace(oldlab,lab)
#        fix_data['short_label'] = f['short_label'].replace(oldlab,lab)
#        print("using fixed data %s for form %s" % (fix_data,f['label']))
#        if fix:
#            forms.update({'label': f['label']}, {"$set": fix_data}, upsert=True)

#        # find associated elliptic curve and fix that too (where appropriate)
#        if f['deg']==2 and f['dimension']==1:
#            label = f['label']
#            for e in nfcurves.find({'class_label':f['label']}):
#                fix_data = {}
#                fix_data['iso_label'] = lab
#                fix_data['label'] = e['label'].replace(oldlab,lab)
#                fix_data['short_label'] = e['short_label'].replace(oldlab,lab)
#                fix_data['class_label'] = e['class_label'].replace(oldlab,lab)
#                fix_data['short_class_label'] = e['short_class_label'].replace(oldlab,lab)
#                print("using fixed data %s for curve %s" % (fix_data,e['label']))
#                if fix:
#                    nfcurves.update({'label': e['label']}, {"$set": fix_data}, upsert=True)
#        else:
#            print("No elliptic curve to fix")

#def add_numeric_label_suffixes(min_level_norm=0, max_level_norm=None, fix=False):
#    r""" One-off utility to add a numeric conversion of the letter-coded
#    label suffixes 'a'->0', 'z'->25, 'ba'->26, etc. for sorting
#    purposes.
#    """
#    from sage.databases.cremona import class_to_int
#    count = 0
#    query = {}
#    query['level_norm'] = {'$gte' : int(min_level_norm)}
#    if max_level_norm:
#        query['level_norm']['$lte'] = int(max_level_norm)
#    else:
#        max_level_norm = oo
#    forms_to_fix = forms.find(query)
#    print("%s forms to examine of level norm between %s and %s."
#          % (forms_to_fix.count(),min_level_norm,max_level_norm))
#    for f in forms_to_fix:
#        count = count+1
#        if count%100==0: print("%s: %s" % (count, f['label']))
#        fix_data = {}
#        lab = f['label_suffix']
#        fix_data['label_nsuffix'] = class_to_int(lab)
#        #print("using fixed data %s for form %s" % (fix_data,f['label']))
#        if fix:
#            forms.update({'label': f['label']}, {"$set": fix_data}, upsert=True)


