import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc
from lmfdb.db_backend import db

class UpdateFailed(Exception):
    """Raise for failure to update"""
    def __init__(self, message):
        mess = "Failed to update field "+message
        super(Exception, self).__init__(mess)

def update_fields(diff, storeRollback=True):
    """Update a record from a diff object.

    diff -- should be a fully qualified difference, containing db, table names and then a list of changes, each being a dict containing the item, the field and the new content. Item corresponds to an entry in an object, field to the piece of information this specifies (for example, type, description, example)
    e.g. {"db":"hgcwa","table":"hgcwa_passports","diffs":[{"item":"total_label","field":"type","content":"string"}]}
    If this is a record entry, then the 'item' field will be a record hash.
    storeRollback -- determine whether to store the undiff and diff to allow rollback of the change
    """

    try:
        if diff['table'] is not None:
            inv.log_dest.info("Updating descriptions for " + diff["table"])
        else:
            inv.log_dest.info("Updating descriptions for " + diff["db"])
        db_id = idc.get_db_id(diff["db"])
        rollback = None
        try:
            for change in diff["diffs"]:
                if ih.is_special_field(change["item"]):
                    if storeRollback:
                        rollback = capture_rollback(db_id, diff["db"], diff["table"], change)
                    change["item"] = change["item"][2:-2] #Trim special fields. TODO this should be done better somehow
                    updated = idc.update_table_data(db_id, diff["table"], change["item"], change["field"], change["content"])
                elif ih.is_toplevel_field(change["item"]):
                    #Here we have item == "toplevel", field the relevant field, and change the new value
                    if storeRollback:
                        rollback = capture_rollback(db_id, diff["db"], diff["table"], change)
                    #Only nice_name is currently an option
                    if(change["field"] not in ['nice_name', 'status']):
                        updated = {'err':True}
                    else:
                        if(diff["table"]):
                            if(change['field']) == 'nice_name':
                                new_nice = change['content']
                                new_stat = None
                            else:
                                new_nice = None
                                new_stat = ih.status_to_code(change['content'])
                            table_id = idc.get_table_id(diff['table'])
                            updated = idc.update_table(table_id, nice_name=new_nice, status=new_stat)
                        else:
                            #Is database nice_name
                            updated = idc.update_db(db_id, nice_name=change["content"])
                else:
                    table_id = idc.get_table_id(diff["table"])
                    if storeRollback:
                        rollback = capture_rollback(db_id, diff["db"], diff["table"], change, table_id = table_id)
                    updated = idc.update_field(table_id, change["item"], change["field"], change["content"], type="human")

                if updated['err']:
                    raise KeyError("Cannot update, item not present")
                else:
                    if storeRollback:
                        store_rollback(rollback)

        except Exception as e:
            inv.log_dest.error("Error applying diff "+ str(change)+' '+str(e))
            raise UpdateFailed(str(e))

    except Exception as e:
        inv.log_dest.error("Error updating fields "+ str(e))

def capture_rollback(db_id, db_name, table_name, change, table_id = None):
    """"Capture diff which will allow roll-back of edits

    db_id -- ID of DB change applies to
    db_name -- Name of DB change applies to
    table_name -- Name of table change applies to
    change -- The change to be made, as a diff item ( entry in diff['diffs'])

    table_id -- Supply if this is a field edit and so table_id is known
    Roll-backs can be applied using apply_rollback. Their format is a diff, with extra 'post' field storing the state after change, and the live field which should be unset if they are applied
    """

    #Fetch the current state
    if table_id is None and table_name is not None:
        current_record = idc.get_table(table_name)
    elif table_id is None:
        current_record = idc.get_db(db_name)
    else:
        current_record = idc.get_field(table_id, change['item'], type = 'human')
    if current_record is None:
        #Should not happen really, but if it does we can't do anything
        return None

    #Create a roll-back document
    field = change["field"]
    prior = change.copy()

    if table_id is None and table_name is not None:
        if ih.is_special_field(change["item"]):
            prior['content'] = current_record['data'][change["item"][2:-2]][field]
        elif ih.is_toplevel_field(change['item']):
            prior['content'] = current_record['data'][field]
        else:
            prior['content'] = current_record['data'][change["item"]][field]
    elif table_id is None:
        prior['content'] = current_record['data'][field]
    else:
        prior['content'] = current_record['data']['data'][field]

    #This can be applied like the diffs from the web-frontend, but has an extra field
    rollback_diff = {"db":db_name, "table":table_name, "diffs":[prior], "post":change, "live":True}

    return rollback_diff

def store_rollback(rollback_diff):
    """"Store a rollback to allow roll-back of edits

    rollback_diff -- rollback record to store
    Roll-backs can be applied using apply_rollback. Their format is a diff, with extra 'post' field
    """
    if not rollback_diff:
        return {'err':True}

    #Commit to db
    record = {'diff':rollback_diff}
    db.inv_rollback.insert_many([record])
    try:
        db.inv_rollback.insert_many([record])
        return {'err':False}
    except Exception as e:
        inv.log_dest.error("Error inserting new record" +str(e))
        return {'err':True}

def set_rollback_dead(rollback_doc):
    """Set rollback to dead (live = False) e.g. after application

    rollback_doc -- Rollback entry. Got using e.g. inv_db[inv.ALL_STRUC.rollback_human[inv.STR_NAME]].find_one()

    """
    raise NotImplementedError
    ##Because we're using nexted documents, we capture the entire record, modify and return
    #rollback_table = inv_db[inv.ALL_STRUC.rollback_human[inv.STR_NAME]]
    #id = rollback_doc['_id']
    #diff = rollback_doc.copy()
    #diff['diff']['live'] = False
    #rollback_table.find_and_modify(query={'_id':id}, update={"$set":diff}, upsert=False, full_response=True)


def apply_rollback(rollback_doc):
    """Apply a rollback given as a fetch from the rollbacks table

    rollback_doc -- Rollback entry. Got using e.g. inv_db[inv.ALL_STRUC.rollback_human[inv.STR_NAME]].find_one()

    Throws -- UpdateFailed if diff application failed
    """
    raise NotImplementedError
    #try:
    #    assert(rollback_doc['diff']['live'])
    #    update_fields(rollback_doc['diff'], storeRollback=False)
    #    set_rollback_dead(inv_db, rollback_doc)
    #except:
    #    raise
