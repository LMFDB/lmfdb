# Adds a field called field_len to objects in the_collection. It is based on the field called field
# It encodes the len of the string used

import math_classes
the_collection = ArtinRepresentation.collection()
field = "Conductor"

new_field = field + "_plus"

import bson

for x in the_collection.find():
    val = x[field]
    x[new_field] = bson.SON([("len",len(val)),("val",val)])
    the_collection.save(x)
    