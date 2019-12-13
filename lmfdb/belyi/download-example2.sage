from lmfdb import db
belyi = db.belyi_galmaps
load("lmfdb/belyi/download.sage")

#label = '5T4-[5,3,3]-5-311-311-g0-a'
#label = '6T13-[6,4,6]-6-42-321-g1-a'
label = '7T5-[7,7,4]-7-7-421-g2-a'
rec = belyi.lookup(label)
print download_string_magma(rec)
