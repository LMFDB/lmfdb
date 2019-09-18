import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc
from lmfdb import db as lmfdb_db

class UpdateFailed(Exception):
    """Raise for failure to update"""
    def __init__(self, message):
        mess = "Failed to update field "+message
        super(Exception, self).__init__(mess)

def update_fields(diff, storeRollback=True):
    """Update a record from a diff object.

    diff -- should be a fully qualified difference, containing db, collection names and then a list of changes, each being a dict containing the item, the field and the new content. Item corresponds to an entry in an object, field to the piece of information this specifies (for example, type, description, example)
    e.g. {"db":"curve_automorphisms","collection":"passports","diffs":[{"item":"total_label","field":"type","content":"string"}]}
    If this is a record entry, then the 'item' field will be a record hash.
    storeRollback -- determine whether to store the undiff and diff to allow rollback of the change
    """

    try:
        _id = idc.get_db_id(diff["db"])
        rollback = None

        storeRollback = False
        try:
            for change in diff["diffs"]:
                if ih.is_special_field(change["item"]):
                    if storeRollback:
                        rollback = capture_rollback(_id['id'], diff["db"], diff["collection"], change)
                    change["item"] = change["item"][2:-2] #Trim special fields. TODO this should be done better somehow
                    updated = idc.update_coll_data(_id['id'], diff["collection"], change["item"], change["field"], change["content"])
                elif ih.is_toplevel_field(change["item"]):
                    #Here we have item == "toplevel", field the relevant field, and change the new value
                    if storeRollback:
                        rollback = capture_rollback(_id['id'], diff["db"], diff["collection"], change)
                    #Only nice_name is currently an option
                    print(change['field'])
                    if(change["field"] not in ['nice_name', 'status']):
                        updated = {'err':True}
                    else:
                        if(diff["collection"]):
                            if(change['field']) == 'nice_name':
                                new_nice = change['content']
                                new_stat = None
                            else:
                                new_nice = None
                                new_stat = ih.status_to_code(change['content'])
                            c_id = idc.get_coll_id(_id['id'], diff['collection'])
                            updated = idc.update_coll(c_id['id'], nice_name=new_nice, status=new_stat)
                        else:
                            #Is database nice_name
                            print(_id)
                            updated = idc.update_db(_id['id'], nice_name=change["content"])
                else:
                    _c_id = idc.get_coll_id(_id['id'], diff["collection"])
                    if storeRollback:
                        rollback = capture_rollback(_id['id'], diff["db"], diff["collection"], change, coll_id = _c_id['id'])
                    succeeded = False
                    #if it looks like a record, try treating as one
                    #If this fails try it as a field
                    if ih.is_probable_record_hash(change['item']):
                        updated = idc.update_record_description(_c_id['id'], {'hash':change["item"], change["field"]:change["content"]})
                        if updated['err'] == False:
                            succeeded = True;
                    if not succeeded:
                        updated = idc.update_field(_c_id['id'], change["item"], change["field"], change["content"], type="human")

                if updated['err']:
                    raise KeyError("Cannot update, item not present")
                else:
                    if storeRollback:
                        store_rollback(rollback)

        except Exception as e:
            raise UpdateFailed(str(e))

    except Exception as e:
        #inv.log_dest.error("Error updating fields "+ str(e))
        pass

def capture_rollback(db_id, db_name, coll_name, change, coll_id = None):
    """"Capture diff which will allow roll-back of edits

    db_id -- ID of DB change applies to
    db_name -- Name of DB change applies to
    coll_name -- Name of collection change applies to
    change -- The change to be made, as a diff item ( entry in diff['diffs'])

    coll_id -- Supply if this is a field edit and so coll_id is known
    Roll-backs can be applied using apply_rollback. Their format is a diff, with extra 'post' field storing the state after change, and the live field which should be unset if they are applied
    """

    return {}

    is_record = False
    #Fetch the current state
    if coll_id is None and coll_name is not None:
        current_record = idc.get_coll(db_id, coll_name)
    elif coll_id is None:
        current_record = idc.get_db(db_name)
    else:
        try:
            current_record = idc.get_field(coll_id, change['item'], type = 'human')
            #Try as a field first
            assert current_record is not None and current_record['err'] is False
        except:
            #Now try as a record
            current_record = idc.get_record(coll_id, change['item'])
            is_record = True
    if current_record is None:
        #Should not happen really, but if it does we can't do anything
        return None

    #Create a roll-back document
    field = change["field"]
    prior = change.copy()

    if coll_id is None and coll_name is not None:
        if ih.is_special_field(change["item"]):
            prior['content'] = current_record['data'][change["item"][2:-2]][field]
        elif ih.is_toplevel_field(change['item']):
            prior['content'] = current_record['data'][field]
        else:
            prior['content'] = current_record['data'][change["item"]][field]
    elif coll_id is None:
        prior['content'] = current_record['data'][field]
    elif is_record:
        prior['content'] = current_record['data'][field]
    else:
        prior['content'] = current_record['data']['data'][field]

    #This can be applied like the diffs from the web-frontend, but has an extra field
    rollback_diff = {"db":db_name, "collection":coll_name, "diffs":[prior], "post":change, "live":True}

    return rollback_diff

def store_rollback(rollback_diff):
    """"Store a rollback to allow roll-back of edits

    rollback_diff -- rollback record to store
    Roll-backs can be applied using apply_rollback. Their format is a diff, with extra 'post' field
    """
    if not rollback_diff:
        return {'err':True, 'id':0}

    return {'err':True, 'id':0}

    #Commit to db
    table = 'inv_rollbacks'
    fields = inv.ALL_STRUC.rollback_human[inv.STR_CONTENT]
    record = {fields[1]:rollback_diff}
    try:
        _id = None
        lmfdb_db[table].upsert(record)
        return {'err':False, 'id':_id}
    except:
        return {'err':True, 'id':0}

def set_rollback_dead(rollback_doc):
    """Set rollback to dead (live = False) e.g. after application

    rollback_doc -- Rollback entry.

    """
    return
    #Because we're using nexted documents, we capture the entire record, modify and return
    # rollback_coll = db['inv_rollback']
    # id = rollback_doc['_id']
    # diff = rollback_doc.copy()
    # diff['diff']['live'] = False
    #TODO fix this, assuming we keep the rollback at all
    #rollback_coll.find_and_modify(query={'_id':id}, update={"$set":diff}, upsert=False, full_response=True)


def apply_rollback(rollback_doc):
    """Apply a rollback given as a fetch from the rollbacks table

    rollback_doc -- Rollback entry.

    Throws -- UpdateFailed if diff application failed
    """
    try:
        assert(rollback_doc['diff']['live'])
        update_fields(rollback_doc['diff'], storeRollback=False)
        set_rollback_dead(rollback_doc)
    except:
        raise
#TODO is raise missing a specifier?
