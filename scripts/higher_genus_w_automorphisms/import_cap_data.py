# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile scripts/higher_genus_w_automorphisms/import_cap_data.py

import re
from lmfdb.base import getDBConnection
from pymongo import MongoClient
from data_mgt.utilities.rewrite import (update_attribute_stats, update_joint_attribute_stats)


def update_unique_count(db, coll, field):
    '''
    Finds the number of distinct values for field across every document in
    db[coll] collection, and adds an entry {_id : field, distinct : count} to
    the db[coll.stats] collection, where count is the number of distinct values
    for that field
    '''
    coll = str(coll)
    field = str(field)
    count = len(db[coll].distinct(field))
    doc = {'_id' : field, 'distinct':count}
    db[coll + '.stats'].replace_one({'_id':field}, doc, upsert=True)


# Get database connection
C = getDBConnection()
db = C.curve_automorphisms

############################
# Collect count statistics #
############################
print("Collecting statistics on genus and dim attributes...")
# update_attribute_stats(db, 'passports', ['genus', 'dim', 'passport_label', 'total_label'])
update_attribute_stats(db, 'passports', ['genus'])
update_attribute_stats(db, 'passports', ['dim'])

# Count unique number of entires
print("Counting number of unique entries for  passport_label and total_label attributes...")
update_unique_count(db, 'passports', 'passport_label')
update_unique_count(db, 'passports', 'total_label')

############################
# Collect joint statistics #
############################

print("Collecting statistics on unique families, refined passports, and generating vectors per genus.")
update_joint_attribute_stats (db, 'passports', ['genus','group'], prefix='bygenus', unflatten=True)
# TODO the group stats already provides this info, although it requires parsing the group string
# update_joint_attribute_stats (db, 'passports', ['genus','group_order'], prefix='bygenus', unflatten=True)
# Number of families per genus
update_joint_attribute_stats (db, 'passports', ['genus','label'], prefix='bygenus', unflatten=True)
# Number of refined passports per genus
update_joint_attribute_stats (db, 'passports', ['genus','passport_label'], prefix='bygenus', unflatten=True)
# Number of generating vectors per genus
update_joint_attribute_stats (db, 'passports', ['genus','total_label'], prefix='bygenus', unflatten=True)

# Number of generating vectors per dimension
update_joint_attribute_stats (db, 'passports', ['dim','total_label'], prefix='bydim', unflatten=True)

#############################################
#  Sort bygenus group counts by group order #
#############################################

for entry in db.passports.stats.find({'_id' : {'$regex':'^bygenus/\d+/group$'}}):
    groups = entry['counts']
    entry['counts'] = sorted(groups, key=lambda count: map(int, re.findall("\d+", count[0])))
    db.passports.stats.save(entry)

C.close()
