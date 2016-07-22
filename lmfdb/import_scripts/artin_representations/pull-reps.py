
pw_filename = "../../../xyzzy"
password = open(pw_filename, "r").readlines()[0].strip()

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
C['artin'].authenticate('editor', password)
C['numberfields'].authenticate('editor', password)
C['limbo'].authenticate('editor', password)

art=C.artin
rep=art.representations
nfgal=art.field_data

print "rep is artin representations"
print "nfgal is the nfgalois group database"

artargs = {'Dim': {'$gte': 2, '$lte': 9}, 'Hide': 0}
allarts=rep.find(artargs)

logfile=open("artlist", "w")

for a in allarts:
  print "."
  baselabel = str(a['Baselabel'])
  numconj = len(a['GaloisConjugates'])
  for j in range(numconj):
    logfile.write(baselabel+'c'+str(j+1)+"\n")

logfile.close()
