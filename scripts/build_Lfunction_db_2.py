# This builds a database of L-functions that occur (maybe on the fly) on the website
# 
import pymongo
import base

C = base.getDBConnection()
db = C.Lfunctions

from Lfunction import Lfunction, Lfunction_Dirichlet

# Iterators over L-functions. It would be nice to have all of the types of forms that appear on the site
def Dirichlet_Lfunctions_iterator(qMax):
    for q in [3..qMax]:
        for n in range(len(DirichletGroup(q))):
            yield Lfunction_Dirichlet(charactermodulus = q, characternumber = n)
 
def EC_iterator():
    data = set(_["label"] for _ in Lfunctions.ellcurves.curves.find({},fields=["label"]))
    for c in data:
        yield Lfunction_EC(c["label"])

def Lfunction_iterator(dirichlet_max = 100):
    yield RiemannZeta()
    for L in Dirichlet_Lfunctions_iterator(dirichlet_max):
        yield L
    for curve in EC_iterator():
        yield L

def inject_Lfunctions(it):
    for L in it:
        L.inject_database(["original_mathematical_object()"])
    
def build_indices():
    db.full_collection.create_index("level", "self_dual")

if __name__=="__main__":
    #build_indices()
    #remove_all()
    inject_Lfunctions(Dirichlet_Lfunctions_iterator(10))
    
