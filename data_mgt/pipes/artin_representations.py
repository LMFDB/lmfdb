from pipes import C

def artin_label_iterator(min_conductor = None, max_conductor = None):
    collection = C["limbo"]["artrep20130914"]
    for x in collection.find(
        {"Conductor_plus.len": {"$lt": 2}, "Sign": 1},{"Conductor": 1, "Dim": 1, "DBIndex": 1}):
        yield {"dimension": x["Dim"], "conductor": x["Conductor"], "tim_index": x["DBIndex"]}




