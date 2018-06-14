# Functions for fetching L-function data from databases

from lmfdb import base
from lmfdb.db_backend import db
import pymongo
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB

def get_lfunction_by_Lhash(Lhash):
    Ldata = db.lfunc_lfunctions.lucky({'Lhash': Lhash})
    print Ldata.keys()
    if Ldata is None:
        raise KeyError("Lhash '%s' not found in Lfunctions collection" % (Lhash,))
    return fix_Ldata(Ldata);

def get_instances_by_Lhash(Lhash):
    return list(db.lfunc_instances.search({'Lhash': Lhash}, sort=["url"]))

def get_instance_by_url(url):
    return db.lfunc_instances.lucky({'url': url})

def get_lfunction_by_url(url):
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
    return db.ec_curves.lucky({'lmfdb_label': label})

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
    return db.hgm_motives.lookup(label)
