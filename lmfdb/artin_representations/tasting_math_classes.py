# This is not a unittest, just a quick script

print "importing base"
from lmfdb import base
from lmfdb.website import dbport
print ".....done"
print "initializing connection"
base._init(dbport, "")
print ".....done"

print "math_classes, Lfunction"
from math_classes import ArtinRepresentation, NumberFieldGaloisGroup
assert ArtinRepresentation and NumberFieldGaloisGroup # silence pyflakes
from Lfunction import ArtinLfunction
assert ArtinLfunction # silence pyflakes
print ".....done"

# a = ArtinRepresentation(1,"5",2)
# b = ArtinRepresentation.find_one({'Dim': 1, 'DBIndex': 1, 'Conductor': '5'})
# c = b.number_field_galois_group()
# d = c.artin_representations()


# l = ArtinLfunction(dimension = "1", conductor = "5", tim_index = "2")
###
## this was run during nosetests, should not, anyway it is not a
## nice test
##
###k = 0
###
###for x in ArtinRepresentation.find():
###    try:
###        tmp = [x.local_factor(p) for p in [11, 13, 17, 19, 23] if not self.is_bad_prime(p)]
###        print tmp
###        print x
###    except:
###        pass
###    k += 1
###    if k > 100:
###        break

# nf = l.artin.number_field_galois_group()
