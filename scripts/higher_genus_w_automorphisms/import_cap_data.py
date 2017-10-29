# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile scripts/higher_genus_w_automorphisms/import_cap_data.py

import lmfdb, re
from pymongo import MongoClient
from data_mgt.utilities.rewrite import (update_attribute_stats, update_joint_attribute_stats)


# Get database connection
C = MongoClient('localhost', 37010)
cap = C.curve_automorphisms

# Basic counts for these attributes:
print("Collecting statistics on genus and dim attributes...")
update_attribute_stats(cap, 'passports', ['genus', 'dim'])

# Collect joint statistics
print("Collecting statistics on unique families, refined passports, and generating vectors per genus.")
update_joint_attribute_stats (cap, 'passports', ['genus','group'], prefix='bygenus', unflatten=True)
# update_joint_attribute_stats (cap, 'passports', ['genus','group_order'], prefix='bygenus', unflatten=True)
# Number of families per genus
update_joint_attribute_stats (cap, 'passports', ['genus','label'], prefix='bygenus', unflatten=True)
# Number of refined passports per genus
update_joint_attribute_stats (cap, 'passports', ['genus','passport_label'], prefix='bygenus', unflatten=True)


# TODO May be redundant, already calculated in genus counts
# Number of generating vectors per genus
update_joint_attribute_stats (cap, 'passports', ['genus','total_label'], prefix='bygenus', unflatten=True)

#############################################
#  Sort bygenus group counts by group order #
#############################################

for entry in cap.passports.stats.find({'_id' : {'$regex':'^bygenus/\d+/group$'}}):
    groups = entry['counts']
    entry['counts'] = sorted(groups, key=lambda count: map(int, re.findall("\d+", count[0])))
    cap.passports.stats.save(entry)

C.close()
