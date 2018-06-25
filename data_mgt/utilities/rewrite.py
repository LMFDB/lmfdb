# -*- coding: utf-8 -*-
import time

def rewrite_collection(db, incoll, outcoll, func, batchsize=1000, reindex=True, filter=None, projection=None):
    """
    
    Pipes an existing collection to a new collection via a user specified function
    that may update records as the pass through.
    
    All indexes will be recreated (in lex order), unless reindex is set to false.
    The parameter outcoll must be the name of a collection that does not exist,
    rewrite_collection will not overwrite an existing collection.
    
    Required arguments:
    
     db: a mongo db to which the caller has write access
     
     incoll: name of an existing collection in db
     
     outcoll: name of the output collection (must not exist)
     
     func: function that takes a mongo db document (dictionary) and returns a (possibly) updated version of it
     
    Optional arguments:
 
      batchsize: number of records to process at once
      
      reindex: whether or not to recreate indexes (if false, no indexes will be created, you must create them)
      
      filter: pymongo filter you may use to select a subset of the input records
      
      projection: pymongo projection you may use to select a subset of fields in each record
 
    For collections with large records, you will likely want to specify a batchsize less than 1000
    (the total size of a batch should be less than 16MB)

    Example usage:
    
        rewrite_collection(db,"old_stuff","new_stuff",lambda x: x)

    """
    if outcoll in db.collection_names():
        print "Collection %s already exists in database %s, please drop it first" % (outcoll, db.name)
        return
    if not incoll in db.collection_names():
        print "Collection %s not found in database %s" % (incoll, db.name)
        return
    start = time.time()
    inrecs = db[incoll].find(filter, projection)
    db.create_collection(outcoll)
    outrecs = []
    incnt = 0
    outcnt = 0
    tot = inrecs.count()
    for r in inrecs:
        incnt += 1
        rec = func(r)
        if rec:
            outcnt += 1
            outrecs.append(rec)
        if len(outrecs) >= batchsize:
            db[outcoll].insert_many(outrecs)
            print "%d of %d records (%.1f percent) processed in %.3f secs" % (incnt, tot, 100.0*incnt/tot,time.time()-start)
            outrecs=[]
    if outrecs:
        db[outcoll].insert_many(outrecs)
    assert db[outcoll].count() == outcnt
    print "Inserted %d records of %d records in %.3f secs" % (outcnt, incnt, time.time()-start)
    if reindex:
        reindex_collection(db,incoll,outcoll)
    print "Rewrote %s to %s, total time %.3f secs" % (incoll, outcoll, time.time()-start)

def reindex_collection(db, incoll, outcoll):
    """
    
    Creates indexes on outcoll matching those that exist on incoll.
    Indexes are created in lexicographic order.
    
    Required arguments:
    
     db: a mongo db to which the caller has write access
     
     incoll: the name of an existing collection in db whose index information will be used
     
     outcoll: the name of an existing collection in db on which indexes will be created
    
    """
    indexes = db[incoll].index_information()
    keys = [(k,indexes[k]['key']) for k in indexes if k != '_id_']
    keys.sort() # sort indexes by keyname so (attr1) < (attr1,attr2) < (attr1,attr2,attr3) < ...
    for i in range(len(keys)):
        now = time.time()
        key = [(a[0],int(1) if a[1] > 0 else int(-1)) for a in keys[i][1]] # deal with legacy floats (1.0 vs 1)
        db[outcoll].create_index(key)
        print "created index %s in %.3f secs" % (keys[i][0], time.time()-now)

def add_counter(rec=None):
    if not rec:
        old_num = add_counter.num
        add_counter.num = 0
        return old_num
    add_counter.num += 1
    rec['num'] = int(add_counter.num)
    return rec
add_counter.num = 0

def create_random_object_index(db, coll, filter=None):
    """

    Creates (or recreates) a collection named incoll.rand used to support fast random object access.
    
    Required arguments:

        db: a mongo db to which the caller has write access
        
        coll: the name of an existing collection in db (string)
     
    Optional arugments:
    
     filter: pymongo filter string you may use to restrict random object access to a subset of records
    
    
    The new collection consists of records with "_id" taken from coll and a sequentially assigned "num"
    (starting at 1) with an index on num.

    """
    outcoll = coll+".rand"
    if outcoll in db.collection_names():
        print "Dropping existing collection %s in db %s" % (outcoll,db.name)
        db[outcoll].drop()
    add_counter() # reset counter
    rewrite_collection (db, coll, outcoll, add_counter, reindex=False, filter=filter, projection={'_id':True})
    db[outcoll].create_index('num')

def update_attribute_stats(db, coll, attributes, prefix=None, filter=None, nocounts=False, wrapper=None):
    """
    
    Creates or updates statistic record in coll.stats for the specified attribute or list of attributes.
    The collection coll.stats will be created if it does not already exist.  Returns the number of stats records created
    
    Required arguments:

        db: a mongo db to which the caller has write access
        
        coll: the name of an existing collection in db
        
        attributes: a string or list of strings specifying attributes whose statistics will be collected, each attribute will get its own statistics record (use update_joint_attribute_stats for joint statistics)

    Optional arugments:
    
        prefix: string used to prefix attribute name when constructing stats record identifier; this can be used to distinguish stats for the same attribute that were collected using different filters
        
        filter: pymongo filter that may be used to restrict stats to a subset of records
        
        nocounts: only the min and max of the specified attribute or attributes will be stored, not individual counts by value
        
        wrapper: string specifying a javascript function that computes a derived attribute, must be of the form 'function f(rec){...};'
                 the wrapper function will be passed the entire document, if specified only one attribute should be specified, not a list

    Each statistics record contains a list of [value,count] pairs, where value is a string and count is an integer, one for each distinct value of the specified attribute
    as well as the min, max, and the total number of records matching filter (all the records in the colleciton if filter=None)
    
    NOTE: pymongo will raise an error if the size of a statistics recrod exceeds 16MB
    
    Existing stats records for the same attribute will be overwritten (but only if they have the same prefix, if specified).
    
    EXAMPLES:
    
    To create a statistic record with counts of elliptic curves over Q in the LMFDB with a given rank, one could use:
    
        sage: import lmfdb
        
        sage: db = lmfdb.base.getDBConnection().elliptic_curves
        
        sage: db.authenticate('editor','password')

        sage: update_attribute_stats (db, "curves", "rank")

    This will result in the following record being inserted/replaced in the collection curves.stats:
    
        {'_id': 'rank', 'counts': [[0,956086], [1,1246537], [2,274346], [3,6679], [4,1]], 'max': 4, 'min': 0, 'total': 2483649}

    To count isogney classes rather than curves, one could instead use:
    
        sage: update_attribute_stats (db, "curves", "rank", prefix='class', filter={'number':int(1)})
        
    which will create the record:
    
        {'_id': 'class/rank', 'counts': [[0,639862], [1,875337], [2,219508], [3,6294], [4,1]], 'max': 4, 'min': 0, 'total': 1741002}

    To create a record with counts of elliptic curves over Q that fall within a given conductor range, say in blocks of 10000, one could use:
    
        sage: update_attribute_stats (db, "curves", "cond_ranges", wrapper=
              "function f(rec){return 10000*Math.ceil(rec.cond/10000);};")
        
    which will create the record:
    
        {'_id': 'cond_ranges', 'counts': [[10000,64687], [20000,67848], ..., [400000,58170]], 'max': 400000, 'min': 10000, 'total': 2483649}

    """
    from bson.code import Code
    
    statscoll = coll + ".stats"
    if isinstance(attributes,basestring):
        attributes = [attributes]
    total = db[coll].find(filter).count()
    if nocounts:
        reducer = Code("function(key,values){return values.reduce(function r(a,b){return { min: a.min < b.min ? a.min : b.min, max : a.max > b.max ? a.max : b.max}; });}")
    else:
        reducer = Code("function(key,values){return Array.sum(values);}")
    for attr in attributes:
        id = prefix + '/' + attr if prefix else attr
        stats = { '_id':id, 'total':total}
        if total:
            if nocounts:
                mapper = Code("function(){emit('minmax',{min:this."+attr+",max:this."+attr+"});}")
                minmax = db[coll].inline_map_reduce(mapper,reducer,query=filter)
                min = minmax[0]['value']['min']
                max = minmax[0]['value']['max']
                # javascript reducer will convert ints to floats, convert them back if we can
                if type(min) == float and min.is_integer() and type(max) == float and max.is_integer():
                    min,max = int(min),int(max)
                stats["min"],stats["max"] = min,max
            else:
                if wrapper:
                    # try to protect caller from themselves
                    assert wrapper.startswith("function f(rec){") and wrapper.endswith("};") and len(attributes) == 1
                    mapper = Code("function(){"+wrapper+"emit(''+f(this),1);}")
                else:
                    mapper = Code("function(){emit(''+this."+attr+",1);}")
                counts = [ [r['_id'],int(r['value'])] for r in db[coll].inline_map_reduce(mapper,reducer,query=filter)]
                # convert numeric value back to numeric values if possible so they sort correctly
                try:
                    if all([c[0] == unicode(int(c[0])) for c in counts]):
                        counts = [[int(c[0]),c[1]] for c in counts]
                except:
                    pass
                if type(counts[0][0]) == unicode:
                    try:
                        if all([c[0] == unicode(float(c[0])) for c in counts]):
                            counts = [[float(c[0]),c[1]] for c in counts]
                    except:
                        pass
                counts.sort()
                stats['counts'] = counts
                stats['min'],stats['max'] = counts[0][0],counts[-1][0]
        db[statscoll].replace_one({'_id':id}, stats, upsert=True)

def update_joint_attribute_stats(db, coll, attributes, prefix=None, filter=None, unflatten=False):
    """
    
    Creates or updates joint statistic record in coll.stats for the specified attributes.
    The collection coll.stats will be created if it does not already exist.
    
    Required arguments:

        db: a mongo db to which the caller has write access
        
        coll: the name of an existing collection in db
        
        attributes: a list of strings specifying attributes whose joint statistics will be collected

    Optional arugments:
    
        prefix: string used to prefix attribute name when constructing stats record identifier; this can be used to distinguish stats for the same attribute that were collected using different filters
        
        filter: pymongo filter that may be used to restrict stats to a subset of records
        
        unflatten: if true, rather than creating a single record with counts for each combination of values for attributes[0],...,attributes[-1],
        a separate stats record will be created for each distinct value of attributes[0] with counts for combinations of values for attributes[1],...,attributes[-1].

    The joint statistics record contains a list of [jointvalue,count] where jointvalue is a colon-delimited string of attribute values and count is an integer,
    one for each distinct combination of values of the specified attributes    
    NOTE: pymongo will raise an error if the size of this list exceeds 16MB

    Any existing stats record for the same combination of attribute will be overwritten (but only if they have the same prefix, if specified).
    
    EXAMPLES:
    
    To create a statistic records with torsion counts organized by rank for elliptic curves over Q one could use
    
        sage: import lmfdb
        
        sage: db = lmfdb.base.getDBConnection().elliptic_curves
        
        sage: db.authenticate('editor','password')

        sage: update_joint_attribute_stats (db, 'curves', ['rank','torsion'], prefix='byrank', unflatten=True)

    This will result in the following records being inserted/replaced in the collection curves.stats:
    
        {'_id': 'byrank/0/torsion', 'counts': [[1,477703], [2,404596], ..., [16,3]], 'max': 16, 'min': 1, 'total': 956086}
        
        {'_id': 'byrank/1/torsion', 'counts': [[1,679194], [2,485681], ..., [16,3]], 'max': 16, 'min': 1, 'total': 1246537}
        
        {'_id': 'byrank/2/torsion', 'counts': [[1,186326], [2,78532], ..., [12, 1]], 'max': 12, 'min': 1, 'total': 274346}
        
        {'_id': 'byrank/3/torsion', 'counts': [[1,6018], [2,635], [3,11], [4,15]], 'max': 4, 'min': 1, 'total': 6679}
        
        {'_id': 'byrank/4/torsion', 'counts': [[1,1]], 'max': 1, 'min': 1, 'total': 1}

    """
    from bson.code import Code
    
    statscoll = coll + ".stats"
    if isinstance(attributes,basestring):
        attributes = [attributes]
    assert len(attributes) > 1
    total = db[coll].find(filter).count()
    reducer = Code("function(key,values){return Array.sum(values);}")
    mapper = Code("function(){emit(''+"+"+\':\'+".join(["this."+attr for attr in attributes])+",1);}")
    counts = sorted([ [r['_id'],int(r['value'])] for r in db[coll].inline_map_reduce(mapper,reducer,query=filter)])
    if unflatten:
        if not counts:
            return
        lastval = None
        vcounts = []; vtotal = 0
        counts.append(['sentinel',-1])
        for pair in counts:
            values = pair[0].split(':')
            if lastval and (values[0] != lastval or pair[1] < 0):
                # convert numeric value back to numeric values if possible so they sort correctly
                try:
                    if all([c[0] == unicode(int(c[0])) for c in vcounts]):
                        vcounts = sorted([[int(c[0]),c[1]] for c in vcounts])
                except:
                    pass
                if type(vcounts[0][0]) == unicode:
                    try:
                        if all([c[0] == unicode(float(c[0])) for c in vcounts]):
                            vcounts = sorted([[float(c[0]),c[1]] for c in vcounts])
                    except:
                        pass
                min, max = vcounts[0][0], vcounts[-1][0]
                vkey = prefix + "/" if prefix else ""
                vkey += lastval + "/" + ":".join(attributes[1:])
                db[statscoll].delete_one({'_id':vkey})
                db[statscoll].insert_one({'_id':vkey, 'total':int(vtotal), 'counts':vcounts, 'min':min, 'max':max})
                vcounts = []; vtotal = 0
            vtotal += pair[1]
            vcounts.append([':'.join(values[1:]),pair[1]])
            lastval = values[0]
    else:
        jointkey = prefix + '/' + ':'.join(attributes) if prefix else ':'.join(attributes)
        min, max = (counts[0][0], counts[-1][0]) if counts else (None, None)
        db[statscoll].delete_one({'_id':jointkey})
        db[statscoll].insert_one({'_id':jointkey, 'total':total, 'counts':counts, 'min':min, 'max':max})

