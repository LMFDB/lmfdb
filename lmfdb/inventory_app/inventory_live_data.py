
from scripts.reports.jsonify_db_structure import get_lmfdb_collections as glc
import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc

#Function to get list a list of all available db/collections
def get_db_lists():
    """Get list of all available DBs and Collections"""

    return glc()

def get_uid():
    """Get a uid for a scrape process"""

    return 10

def trigger_scrape(db, coll):

    return True

def get_progress(uid):

    return 100
