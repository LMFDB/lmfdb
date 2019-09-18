from lmfdb.backend.database import db

def get_sample_record(collection, field_name):
    """ Function to get a sample, non-empty record from a collection 
        collection - MongoDB collection object
        field_name - name of field to find sample record from

        returns sample record
    """
    return collection.find_one({str(field_name):{'$exists':True,'$nin':[[], '']}})

def get_pg_sample_record(table, field_name):
    """ Function to get a sample, non-empty record from a table
        table - Postgres table name
        field_name - name of field to find sample record from

        returns sample record
    """

    return db[table].lucky({str(field_name):{'$exists':True}})
