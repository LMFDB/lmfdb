# Functions for fetching L-function data from databases

from lmfdb import base
import pymongo
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB

def getEllipticCurveData(label):
    connection = base.getDBConnection()
    curves = connection.elliptic_curves.curves
    return curves.find_one({'lmfdb_label': label})
    
def getInstanceLdata(label,label_type="url"):
    db = base.getDBConnection().Lfunctions
    try:
        if label_type == "url":
            Lpointer = db.instances.find_one({'url': label})
            if not Lpointer:
                return None
            Lhash = Lpointer['Lhash']
            Ldata = db.Lfunctions.find_one({'Lhash': Lhash})
            # do not ignore this error, if the instances record exists the
            # Lhash should be there and we want to know if it is not
            if not Ldata:
                raise KeyError("Lhash '%s' in instances record for URL '%s' not found in Lfunctions collection" % (label, Lhash))
        elif label_type == "Lhash":
            Ldata = db.Lfunctions.find_one({'Lhash': label})
        else:
            raise ValueError("Invalid label_type = '%s', should be 'url' or 'Lhash'" % label)
            
        # Need to change this so it shows the nonvanishing derivative
        if Ldata['order_of_vanishing'] or 'leading_term' not in Ldata.keys():
            central_value = [0.5 + 0.5*Ldata['motivic_weight'], 0]
        else:
            central_value = [0.5 + 0.5*Ldata['motivic_weight'],Ldata['leading_term']]
        if 'values' not in Ldata:
            Ldata['values'] = [ central_value ]
        else:
            Ldata['values'] += [ central_value ]

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
    
