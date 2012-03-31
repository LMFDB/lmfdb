from math_classes import ArtinRepresentation

import base
base._init(int(37010),"")

# x is raw
# a is of type ArtinRepresentation

# if you want to do complex queries, and sort using pymongo's interface:
for x in ArtinRepresentation.collection().find():
    a = ArtinRepresentation(data = x)
    print a
    print a.Lfunction()
    
# if you want to list them all, using a wrapper to directly convert to ArtinRepresentation 
for a in ArtinRepresentation.find():
    print a
    print a.Lfunction()
    

