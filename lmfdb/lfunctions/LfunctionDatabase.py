# Functions for fetching L-function data from databases

from lmfdb import base
import pymongo
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB

def db_lfunctions():
    return base.getDBConnection().Lfunctions.Lfunctions;

def db_instances():
    return base.getDBConnection().Lfunctions.instances;

def get_lfunction_by_Lhash(Lhash):
    Ldata = db_lfunctions().find_one({'Lhash': Lhash})
    # FIXME after merging dbs
    if not Ldata:
        Ldata = base.getDBConnection().Lfunctions.ecqd1_Lfunctions.find_one({'Lhash': Lhash})
    if not Ldata:
       return None
    else:
       return fix_Ldata(Ldata);

def get_instances_by_Lhash(Lhash):
    # FIXME after merging dbs
    return list(db_instances().find({'Lhash': Lhash})) + list(base.getDBConnection().Lfunctions.ecqd1_instances.find({'Lhash': Lhash}));

def get_instance_by_url(url):
    instance =  db_instances().find_one({'url': url})
    # FIXME after merging dbs
    if not instance:
        instance = base.getDBConnection().Lfunctions.ecqd1_instances.find_one({'url': url})
    return instance

def get_lfunction_by_url(url):
#    if url.startswith("EllipticCurve") and not url.startswith("EllipticCurve/Q/"):
#        Lfunctions =  base.getDBConnection().Lfunctions["ecqd1_Lfunctions"];
#        instances = base.getDBConnection().Lfunctions["ecqd1_instances"];

    instance = get_instance_by_url(url);
    if not instance:
        return None;

    Lhash = instance['Lhash']
    Ldata =  get_lfunction_by_Lhash(Lhash);
    if not Ldata:
        raise KeyError("Lhash '%s' in instances record for URL '%s' not found in Lfunctions collection" % (Lhash, url))
    return Ldata

def fix_Ldata(Ldata):
    if Ldata['order_of_vanishing'] or 'leading_term' not in Ldata.keys():
        central_value = [0.5 + 0.5*Ldata['motivic_weight'], 0]
    else:
        central_value = [0.5 + 0.5*Ldata['motivic_weight'], Ldata['leading_term']]
    if 'values' not in Ldata:
        Ldata['values'] = [ central_value ]
    else:
        Ldata['values'] += [ central_value ]
    return Ldata


def getEllipticCurveData(label):
    from lmfdb.elliptic_curves.web_ec import db_ec
    return db_ec().find_one({'lmfdb_label': label})
    
#FIXME this should be deprecated
def getInstanceLdata(label, label_type="url"):
    try:
        if label_type == "url":
            return get_lfunction_by_url(label);
        elif label_type == "Lhash":
            return get_lfunction_by_Lhash(label);
        else:
            raise ValueError("Invalid label_type = '%s', should be 'url' or 'Lhash'" % label)
    except ValueError:   
        Ldata = None

    return Ldata



def getHmfData(label):
    from lmfdb.hilbert_modular_forms.hilbert_modular_form import get_hmf, get_hmf_field
    # return (None,None) if nothing is found i.e. if for does not exist in the database
    f = get_hmf(label)
    if f:
        return (f, get_hmf_field(f['field_label']))
    return (None, None)

def getMaassDb():
    # NB although base.getDBConnection().PORT works it gives the
    # default port number of 27017 and not the actual one!
    if pymongo.version_tuple[0] < 3:
        host = base.getDBConnection().host
        port = base.getDBConnection().port
    else:
        host, port = base.getDBConnection().address
    return MaassDB(host=host, port=port)
    
def getHgmData(label):
    connection = base.getDBConnection()
    return connection.hgm.motives.find_one({'label': label})
    
