import pymongo

C = pymongo.Connection("localhost", port = int(37010))

def iterator(database_name, collection_name, selector = {}):
    collection = C[database_name][collection_name]
    for x in collection.find(selector):
        yield x

def populator(database_name, collection_name):
    # One L function at a time !!!
    collection = C[database_name][collection_name]
    return lambda data : collection.insert(data)
    

