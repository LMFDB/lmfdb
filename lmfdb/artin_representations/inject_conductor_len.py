# Adds a field called field_len to objects in the_collection. It is based on the field called field
# It encodes the len of the string used

import sys
sys.path.append("../")
import base
base._init(37010, "")
from lmfdb.math_classes import ArtinRepresentation
the_collection = ArtinRepresentation.collection()
print "Got", the_collection

field = "Conductor"

from utils import len_val_fn

new_field = field + "_plus"


for x in the_collection.find():
    val = x[field]
    x[new_field] = len_val_fn(val)
    the_collection.save(x)
