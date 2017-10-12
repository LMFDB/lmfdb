# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile scripts/higher_genus_w_automorphisms/import_cap_data.py

import lmfdb
from pymongo import MongoClient
from data_mgt.utilities.rewrite import (update_attribute_stats, update_joint_attribute_stats)


# Get database connection
C = MongoClient('localhost', 37010)
cap = C.curve_automorphisms

# Basic counts for these attributes:
print("Colelcting statistics on genus, dim, and r attributes.")
update_attribute_stats(cap, 'passports', ['genus', 'dim', 'r'])
update_joint_attribute_stats (cap, 'passports', ['genus','group'], prefix='bygroup', unflatten=True)
