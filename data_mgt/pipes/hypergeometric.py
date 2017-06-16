from pipes import C

def hypergeometric_label_iterator(min_conductor = 0, max_conductor = 10**3):
    collection = C["hgm"]["motives"]
    for x in collection.find({
            "cond": {
                "$lt": int(max_conductor),
                "$gt": int(min_conductor)
                }}, 
            {"label": 1}):
        yield x["label"]
