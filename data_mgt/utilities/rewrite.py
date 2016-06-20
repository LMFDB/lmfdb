import time

# rewrite_collection(db,incoll,outcoll,func)
#
# function to pipe an existing collection to a new collection through a user specified function
# that may update records as the pass through.  All indexes will be recreated (in lex order),
# unless reindex is set to false.
#
# Arguments:
#
#    db: should be a mongo database to which the caller has write access (authenticate as editor)
#    incoll: the name of the input collection in db
#    outcoll: the name of the output collection (must not already exist in db)
#    func: filter that takes a mongo db document (dictionary) and returns a (possibly) updated version of it
#
# Example usage: rewrite_collection(db,"old_stuff","new_stuff",lambda x: x)
#
# For collections with large records, you will want to specify a batchsize smaller than 1000
#
def rewrite_collection(db,incoll,outcoll,func, batchsize=1000, reindex=True, filter=None, projection=None):
    if outcoll in db.collection_names():
        print "Collection %s already exists in database %s, please drop it first" % (outcoll, db.name)
        return
    if not incoll in db.collection_names():
        print "Collection %s not found in database %s" % (coll, db.name)
        return
    start = time.time()
    inrecs = db[incoll].find(filter, projection)
    db.create_collection(outcoll)
    outrecs = []
    cnt = 0
    tot = inrecs.count()
    for r in inrecs:
        outrecs.append(func(r))
        cnt += 1
        if len(outrecs) >= batchsize:
            db[outcoll].insert_many(outrecs)
            print "%d of %d records (%.1f percent) inserted in %.3f secs"%(cnt,tot,100.0*cnt/tot,time.time()-start)
            outrecs=[]
    if outrecs:
        db[outcoll].insert_many(outrecs)
    assert db[outcoll].count() == tot
    print "inserted %d records in %.3f secs"%(cnt, time.time()-start)
    if reindex:
        reindex_collection(db,incoll,outcoll)
    print "Rewrote %s to %s, total time %.3f secs"%(incoll, outcoll, time.time()-start)

# reindex_collection(db,incoll,outcoll)
#
# Take indexes from incoll and create them in outcoll (in lex order).
#
def reindex_collection(db,incoll,outcoll):
    indexes = db[incoll].index_information()
    keys = [(k,indexes[k]['key']) for k in indexes if k != '_id_']
    keys.sort() # sort indexes by keyname so (attr1) < (attr1,attr2) < (attr1,attr2,attr3) < ...
    for i in range(len(keys)):
        now = time.time()
        key = [(a[0],int(1) if a[1] > 0 else int(-1)) for a in keys[i][1]] # deal with legacy floats (1.0 vs 1)
        db[outcoll].create_index(key)
        print "created index %s in %.3f secs"%(keys[i][0],time.time()-now)

def add_counter(rec=None):
    if not rec:
        old_num = add_counter.num
        add_counter.num = 0
        return old_num
    add_counter.num += 1
    rec['num'] = add_counter.num
    return rec
add_counter.num = 0

# create_random_object_index(db,coll)
#
# Creates (or recreates) a collection named coll.rand used to support fast random object access
# The new collection consists of records with "_id" taken from coll and a sequentially assigned "num" (starting at 1)
# An index is created on num which can be used to efficiently generate random object ids in coll
#
def create_random_object_index(db,incoll):
    outcoll = incoll+".rand"
    if outcoll in db.collection_names():
        print "Dropping existing collection %s in db %s" % (outcoll,db.name)
        db[outcoll].drop()
    add_counter() # reset counter
    rewrite_collection (db, incoll, outcoll, add_counter, reindex=False, projection={'_id':True})
    db[outcoll].create_index('num')
