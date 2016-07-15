from pipes import C
from operator import itemgetter


def ec_iterator(min_conductor = 0, max_conductor = 10**3):
    collection = C["elliptic_curves"]["curves"]
    for x in collection.find({
            "conductor": {
                "$lt": int(max_conductor),
                "$gt": int(min_conductor)
                }}, 
            {"lmfdb_label": 1}):
        yield x

def isogeny_iterator(min_conductor = 0, max_conductor = 10**3):
    collection = C["elliptic_curves"]["isogeny_classes"]
    for x in collection.find({
            "conductor":{
                "$lt": int(max_conductor), 
                "$gt": int(min_conductor)}}, 
            {"label": 1}):
        yield x

ec_label_iterator = lambda min_conductor, max_conductor : map(
    itemgetter("lmfdb_label"), 
    ec_iterator(
        min_conductor = min_conductor, 
        max_conductor = max_conductor))
    
isogeny_label_iterator = lambda min_conductor, max_conductor : map(
    itemgetter("label"), 
    isogeny_iterator(
        max_conductor = max_conductor))

ec_isogeny_label_iterator = lambda min_conductor, max_conductor: map(
        lambda label: label[:-1]+"."+label[-1]+"1", 
        isogeny_label_iterator(
            min_conductor = min_conductor,
            max_conductor = max_conductor))