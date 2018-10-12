# Functions for fetching L-function data from databases

from lmfdb.db_backend import db
from lmfdb.ecnf.WebEllipticCurve import convert_IQF_label

def get_lfunction_by_Lhash(Lhash):
    Ldata = db.lfunc_lfunctions.lucky({'Lhash': Lhash})
    if Ldata is None:
        raise KeyError("Lhash '%s' not found in Lfunctions collection" % (Lhash,))
    return Ldata

def get_instances_by_Lhash(Lhash):
    return list(db.lfunc_instances.search({'Lhash': Lhash}))



# a temporary fix while we don't replace the old Lhash (=trace_hash)
# there are trace hash collisions out there, we need the degree to distinguish them
def get_instances_by_trace_hash(degree, trace_hash):
    def ECNF_convert_old_url(oldurl):
        # EllipticCurve/2.0.4.1/[4160,64,8]/a/
        if '[' not in oldurl:
            return oldurl
        ec, fld, cond, iso =  oldurl.rstrip('/').split('/')
        assert ec == 'EllipticCurve'
        if cond[0] == '[' and cond[-1] == ']':
            cond = convert_IQF_label(fld, cond)
            return '/'.join([ec, fld, cond, iso])
        else:
            return oldurl

    res = []
    for Lhash in db.lfunc_lfunctions.search({'trace_hash': trace_hash, 'degree' : degree}, projection = 'Lhash'):
        for elt in get_instances_by_Lhash(Lhash):
            if elt['type'] == 'ECQP':
                continue
            if elt['type'] == 'ECNF':
                elt['url'] = ECNF_convert_old_url(elt['url'])
            if elt not in res:
                res.append(elt)
    return res


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
