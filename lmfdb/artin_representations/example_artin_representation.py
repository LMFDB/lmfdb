from lmfdb.artin_representations.math_classes import ArtinRepresentation
from lmfdb.website import dbport

import base
base._init(dbport, "")

# x is raw
# a is of type ArtinRepresentation

# all the artin reps that come out of this are safe to appear on the website
# their L functions need to be fixed however

# if you want to do complex queries, and sort using pymongo's interface:
for x in ArtinRepresentation.collection().find():
    a = ArtinRepresentation(data=x)
    print a
    try:
        print a.Lfunction()
    except NotImplementedError or SyntaxError:
        print "Need CYC types and sign"

# if you want to list them all, using a wrapper to directly convert to ArtinRepresentation
for a in ArtinRepresentation.find():
    print a
    try:
        print a.Lfunction()
    except NotImplementedError or SyntaxError:
        print "Need CYC types"
