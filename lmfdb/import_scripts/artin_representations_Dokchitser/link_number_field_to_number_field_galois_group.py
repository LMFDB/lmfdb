# This script links the nfgal database of Tim Dokchitser's data to the other number field database
# It works by computing the polredabs of a defining polynomial of the field, and looking it up in the other number field database
# (Admittedly, often the defining polynomial is already polredabs'd)
# If that canonical form is in the number field database, this scripts adds a "label" field in Tim's database
# If not, it does nothing

# This could be improved by working in two passes: one to compute the polredabs and store it, one to link to the other database. 
# This would be at the expense of further deviating from Tim's original data submission

import sys
LMFDB_FOLDER = "../../../"
sys.path.append(LMFDB_FOLDER)

print "Importing sage in base"
import lmfdb.base as base
from lmfdb.artin_representations.math_classes import NumberFieldGaloisGroup as NF
print "Sage loaded"

print "getting connection"
base._init(37010, "")
print "I have it"

base.getDBConnection()

# Doing an iteration on degrees, so it is easier to stop the script and restart it again
for degree in range(1,100):
    total = NF.collection().find({"TransitiveDegree":degree, "label": {"$exists": False}}).count()
    tmp = 0

    for nf_dict in NF.collection().find({"TransitiveDegree":degree, "label": {"$exists": False}}).sort("QpRts-p", -1):
        tmp += 1
        print tmp, " out of ", total, " at degree ", degree, " (with QpRts-p ", nf_dict["QpRts-p"], ")"
        from copy import deepcopy
        nf_dict2 = deepcopy(nf_dict)
        nf = NF(data=nf_dict)
        #if True:
        if int(nf.polynomial()[0]) != -45 and len(nf.polynomial()) != 9:
            # This is needed to avoid a bug that appears sometimes with pari(x^8-45).polredabs()
            # It looks like this bug was fixed upstream in an upcoming release of pari
            if nf.label():
                print nf.polynomial(), nf.polredabs(), nf.label()
                nf_dict2["label"] = nf.label()
                NF.collection().save(nf_dict2)
            else:
                print nf.polynomial(), "No label added!"

print "Done, in ", NF.collection()
