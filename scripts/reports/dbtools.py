def get_sample_record(collection, field_name):

    return collection.find_one({str(field_name):{'$exists':True,'$nin':[[], '']}})
