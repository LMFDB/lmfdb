# This script links the nfgal database of Tim Dokchitser's data to the other number field database
# It works by computing the polredabs of a defining polynomial of the field, and looking it up in the other number field database
# If that canonical form is in the number field database, this scripts adds a "label" field in Tim's database
# If not, it does nothing

import sys
sys.path.append("../")

print "Importing sage in base"
import base
from lmfdb.math_classes import NumberFieldGaloisGroup as NF
print "Sage loaded"

print "getting connection"
base._init(37010, "")
print "I have it"

base.getDBConnection()

for nf_dict in NF.collection().find({"label": {"$exists": False}}):
    from copy import deepcopy
    nf_dict2 = deepcopy(nf_dict)
    nf = NF(data=nf_dict)
    print nf.polynomial()
    if int(nf.polynomial()[0]) != -45 and len(nf.polynomial()) != 9:
        # This is needed to avoid a bug that appears sometimes with pari(x^8-45).polredabs()
        # It looks like this bug was fixed upstream in an upcoming release of pari
        print nf.polredabs()
        if nf.label():
            print nf.label()
            nf_dict2["label"] = nf.label()
            NF.collection().save(nf_dict2)
        else:
            print "No label added!"

print "Done, in ", NF.collection()
