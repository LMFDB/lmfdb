# Functions for fetching L-function data from databases

from lmfdb import db

def get_lfunction_by_Lhash(Lhash, **kwargs):
    Ldata = db.lfunc_lfunctions.lucky({'Lhash': Lhash}, **kwargs)
    if Ldata is None:
        raise KeyError("Lhash '%s' not found in Lfunctions collection" % (Lhash,))
    return Ldata

def get_instances_by_Lhash(Lhash):
    return list(db.lfunc_instances.search({'Lhash': Lhash}, sort=[]))

def get_multiples_by_Lhash(Lhash):
    return list(db.lfunc_instances.search({'Lhash_array': {'$contains': Lhash.split(',')}}, sort=[]))


# a temporary fix while we don't replace the old Lhash (=trace_hash)
# there are trace hash collisions out there, we need the degree to distinguish them
def get_instances_by_trace_hash(degree, trace_hash):
    # this is only relevant to find L-funs for ECQ or G2C
    if degree not in [2, 4]:
        return []
    def ECNF_convert_old_url(oldurl):
        from lmfdb.ecnf.WebEllipticCurve import convert_IQF_label
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
    for Lhash in db.lfunc_lfunctions.search({'trace_hash': trace_hash, 'degree' : degree}, projection='Lhash', sort=[]):
        for elt in get_instances_by_Lhash(Lhash):
            if elt['type'] == 'ECQP':
                continue
            if elt['type'] == 'ECNF':
                elt['url'] = ECNF_convert_old_url(elt['url'])
            if elt not in res:
                res.append(elt)
    return res


def get_instances_by_Lhash_and_trace_hash(Lhash, degree, trace_hash):
    instances = get_instances_by_Lhash(Lhash)
    if trace_hash:
        instances += get_instances_by_trace_hash(degree, trace_hash)
    return instances

def get_multiples_by_Lhash_and_trace_hash(Lhash, degree, trace_hash):
    instances = [elt for elt in get_multiples_by_Lhash(Lhash)
                 if elt['Lhash'] != Lhash]

    if trace_hash:
        # is usually a number
        trace_hash = str(trace_hash)
        # use trace_hash as an Lhash
        instances += [elt for elt in get_multiples_by_Lhash(trace_hash)
                      if elt['Lhash'] != Lhash and elt['Lhash'] !=trace_hash ]
        # a temporary fix while we don't replace the old Lhash (=trace_hash)
        # the only thing that we might be missing are genus 2 L-functions
        # hence, self.degree = 2, self.type = CMF
        if degree == 2:
            # our only hope is to find the missing genus 2 curve with a CMF
            for Lhash in set(elt['Lhash'] for elt in instances
                             if elt['type'] == 'CMF'):
                other_trace_hash = db.lfunc_lfunctions.lucky(
                    {'Lhash': Lhash, 'degree': 4}, 'trace_hash')
                if other_trace_hash is not None:
                    # names_and_urls will remove duplicates
                    instances.extend(get_instances_by_trace_hash(
                        4, str(other_trace_hash)))

    return instances

def get_factors_instances(Lhash, degree, trace_hash):
        # objects for the factors
        instances = []
        if "," in Lhash:
            for factor_Lhash in set(Lhash.split(",")):
                elt = db.lfunc_lfunctions.lucky({'Lhash': factor_Lhash},
                                                ['trace_hash', 'degree'])
                # names_and_urls will remove duplicates
                instances.extend(
                        get_instances_by_Lhash_and_trace_hash(factor_Lhash,
                            elt['degree'],
                            elt.get('trace_hash', None)))
        # try to get factors as EC, this only arises for G2C
        for elt in db.lfunc_instances.search(
                {'Lhash': Lhash, 'type':'ECQP'}, 'url'):
                if '|' in elt:
                    for url in elt.split('|'):
                        url = url.rstrip('/')
                        # Lhash = trace_hash
                        instances.extend(get_instances_by_trace_hash(2, db.lfunc_instances.lucky({'url': url}, 'Lhash')))

        # or we need to use the trace_hash to find other factorizations
        if str(trace_hash) == Lhash:
            for elt in db.lfunc_lfunctions.search(
                    {'trace_hash': trace_hash, 'degree': degree}, 'Lhash'):
                instances.extend(get_factors_instances(elt, None, None))
        return instances




def get_instance_by_url(url):
    return db.lfunc_instances.lucky({'url': url})

def get_lfunction_by_url(url, **kwargs):
    instance = get_instance_by_url(url)
    if not instance:
        return None
    Lhash = instance['Lhash']
    Ldata = get_lfunction_by_Lhash(Lhash, **kwargs)
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
