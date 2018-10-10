# Functions for fetching L-function data from databases

from lmfdb.db_backend import db

def get_lfunction_by_Lhash(Lhash):
    Ldata = db.lfunc_lfunctions.lucky({'Lhash': Lhash})
    if Ldata is None:
        raise KeyError("Lhash '%s' not found in Lfunctions collection" % (Lhash,))
    return Ldata

def get_instances_by_Lhash(Lhash):
    return list(db.lfunc_instances.search({'Lhash': Lhash}))


# a temporary fix while we don't replace the old Lhash (=trace_hash)
def get_instances_by_trace_hash(trace_hash):
    res = []
    for Lhash in db.lfunc_lfunctions.search({'trace_hash': trace_hash}, projection = 'Lhash'):
        res += get_instances_by_Lhash(Lhash)
    # remove duplicates
    res.sort(key = lambda elt: elt['url'])
    no_duplicates = []
    previousurl = None
    for elt in res:
        if elt['url'] != previousurl:
            no_duplicates.append(elt)
            previousurl = elt['url']
    return no_duplicates


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



def getEllipticCurveData(label):
    return db.ec_curves.lucky({'lmfdb_label': label})

def getHmfData(label):
    from lmfdb.hilbert_modular_forms.hilbert_modular_form import get_hmf, get_hmf_field
    # return (None,None) if nothing is found i.e. if for does not exist in the database
    f = get_hmf(label)
    if f:
        return (f, get_hmf_field(f['field_label']))
    return (None, None)

def getHgmData(label):
    return db.hgm_motives.lookup(label)
