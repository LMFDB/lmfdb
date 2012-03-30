import base
base._init(37010,"")
from math_classes import ArtinRepresentation, NumberFieldGaloisGroup
from Lfunction import ArtinLfunction

a = ArtinRepresentation(1,"5",2)
b = ArtinRepresentation.find_one({'Dim': 1, 'DBIndex': 1, 'Conductor': '5'})
c = b.number_field_galois_group()
d = c.artin_representations()


l = ArtinLfunction("1","5","2")

#nf = l.artin.number_field_galois_group()
