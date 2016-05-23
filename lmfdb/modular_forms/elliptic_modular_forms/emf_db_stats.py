def anum(a):
    return sum([26**i*(ord(a[len(a)-i-1])-ord('a')+1) for i in range(len(a))])

def check_orbit_list(a):
    return set([anum(c) for c in a]) == set(range(1,len(a)+1))

version = 1.3
trivial_only = False
print "Statistics for emf version %.1f with trivial character" % version
from pymongo import MongoClient
conn = MongoClient(host='localhost',port=int(37010))
assert conn.admin.authenticate('lmfdb','lmfdb')
mf = conn.modularforms2
spaces = mf.webmodformspace
forms = mf.webnewforms
vspaces = spaces.find({'version':float(version)})
if trivial_only:
    tspaces = spaces.find({'version':float(version),'character':int(1)})
    uspaces = spaces.find({'version':float(version),'character':int(1),'dimension_new_cusp_forms':{'$gt':int(0)}})
    print "%d of %d spaces have trivial character, of which %d are nonempty" % (tspaces.count(), vspaces.count(), uspaces.count())
else:
    uspaces = spaces.find({'version':float(version),'dimension_new_cusp_forms':{'$gt':int(0)}})
    print "%d of %d spaces are nonempty" % (uspaces.count(), vspaces.count())
stab = dict()
for s in uspaces:
    stab[s['space_label']] = (s['hecke_orbits'],s['dimension_new_cusp_forms'])
    if not check_orbit_list(s['hecke_orbits']):
        print "Space %s has a bad list of Hecke orbits: %s" % (s['space_label'], s['hecke_orbits'])
for label in stab:
    orbits = forms.find({'version':float(version),'parent':label})
    olabels = [r['label'] for r in orbits]
    if len(olabels) == 0:
        print "No Hecke orbit data for space %s of dimension %d with %d Hecke orbits" % (label, stab[label][1], len(stab[label][0]))
        continue
    if len(olabels) != len(stab[label][0]) or set(olabels) != set(stab[label][0]):
        print "Hecke orbit data in webnewforms for space %s is incomplete or inconsistent" % label
        print "    %s versus %s" % (olabels,stab[label][0])
        continue
    orbits = orbits.rewind()
    odims = [r['dimension'] for r in orbits] 
    if sum(odims) != stab[label][1]:
        print "Hecke orbit dimensions %s do not sum to %d for space %s" % (odims, stab[label][1], label)
