from pipes import iterator, C
from operator import itemgetter

def artin_label_iterator():
    collection = C["limbo"]["artrep20130914"]
    for x in collection.find(
        {"Conductor_plus.len": {"$lt": 2}},{"Conductor": 1, "Dim": 1, "DBIndex": 1}):
        yield {"dimension": x["Dim"], "conductor": x["Conductor"], "tim_index": x["DBIndex"]}




