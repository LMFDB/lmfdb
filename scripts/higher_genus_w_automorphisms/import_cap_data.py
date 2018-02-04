# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile scripts/higher_genus_w_automorphisms/import_cap_data.py

import re
from lmfdb.base import getDBConnection
from data_mgt.utilities.rewrite import (update_attribute_stats, update_joint_attribute_stats)


def update_unique_count(db, coll, attribute):
    '''
    Finds the number of distinct values for attribute across every document in
    db[coll] collection, and adds an entry {_id : attribute, distinct : count} to
    the db[coll.stats] collection, where count is the number of distinct values
    for that attribute
    '''
    coll = str(coll)
    attribute = str(attribute)
    count = len(db[coll].distinct(attribute))
    doc = {'_id' : attribute, 'distinct':count}
    db[coll + '.stats'].replace_one({'_id':attribute}, doc, upsert=True)

def update_joint_unique_count(db, coll, primary_attribute, secondary_attribute, prefix=None):
    '''
    For each distinct primary_attribute in db[coll], the function finds the number
    of distinct values of secondary_attribute in db[coll] with that primary_attribute value.
    The function then adds an entry
      {_id : prefix + primary_attribute/secondary_attribute, distinct : counts}
    to db[coll.stats], where counts is a dictionary where the keys are possible values for
    primary_attribute which map to the number of distinct values for secondary_attribute.
    Note: due to limitations of MongoDB, the keys are string representations of the attributes.

    Required arguments:

        db: a mongo db to which the caller has write access

        coll: the name of an existing collection in db

        primary_attribute: a string holding the primary attribute

        secondary_attribute: a string holding the secondary attribute

    Optional arguments:

        prefix: string used to prefix document id

    For example:
    If [1,2] is the list of unique values for 'dim', and there are 5 unique values
    for 'total_label' across all entries with dim=1, and 7 unique values for
    'total_label' across all entries with dim=2, then
      update_joint_unique_count(db, 'passports', 'dim', 'total_label', prefix='by')
    add the entry
      {'_id'  :'bydim/total_label',
       unique : {'1':5, '2':7} }
    to db[coll.stats].
    '''
    pa = str(primary_attribute)
    sa = str(secondary_attribute)
    unique_pa = db[coll].distinct(pa)
    unique_pa.sort()

    unique_counts = {}
    for attr in unique_pa:
        num_unique_sa = len(db[coll].find({pa:attr}).distinct(sa))
        unique_counts[str(attr)] = num_unique_sa

    attr_str = pa + '/' + sa
    doc_id = prefix + attr_str if prefix else attr_str
    doc = {
        '_id' : doc_id,
        'distinct' : unique_counts,
    }
    db[coll + '.stats'].replace_one({'_id':doc_id}, doc, upsert=True)


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
# Unique groups per genus
update_joint_attribute_stats (db, 'passports', ['genus','group'], prefix='bygenus', unflatten=True)
# TODO the group stats already provides this info, although it requires parsing the group string
# update_joint_attribute_stats (db, 'passports', ['genus','group_order'], prefix='bygenus', unflatten=True)

# Number of families per genus
update_joint_unique_count(db, 'passports', 'genus', 'label', prefix='by')

# Number of refined passports per genus
update_joint_unique_count(db, 'passports', 'genus', 'passport_label', prefix='by')

# Number of generating vectors per genus
update_joint_unique_count(db, 'passports', 'genus', 'total_label', prefix='by')

# Number of generating vectors per dimension
update_joint_unique_count(db, 'passports', 'dim', 'total_label', prefix='by')


#############################################
#  Sort bygenus group counts by group order #
#############################################

for entry in db.passports.stats.find({'_id' : {'$regex':'^bygenus/\d+/group$'}}):
    groups = entry['counts']
    entry['counts'] = sorted(groups, key=lambda count: map(int, re.findall("\d+", count[0])))
    db.passports.stats.replace_one({'_id':entry['_id']}, entry)

C.close()
