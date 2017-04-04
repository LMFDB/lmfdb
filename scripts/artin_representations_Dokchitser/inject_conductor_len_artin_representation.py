# Adds a field called field_len to objects in the_collection. It is based on the field called field
# It encodes the len of the string used
# This is kind of a hack for mongodb, see lmfdb.utils.len_val_fn for explanation

import sys
LMFDB_FOLDER = "../../../"
sys.path.append(LMFDB_FOLDER)
from lmfdb.artin_representations.math_classes import ArtinRepresentation
the_collection = ArtinRepresentation.collection()
print "Got", the_collection

field = "Conductor"

from lmfdb.utils import len_val_fn

new_field = field + "_plus"

print "Updating"
for x in the_collection.find():
    val = x[field]
    x[new_field] = len_val_fn(val)
    the_collection.save(x)
