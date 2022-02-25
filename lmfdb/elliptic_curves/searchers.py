from lmfdb.api2.utils import build_description


def get_searchers():
    desc = {}
    build_description(desc, name='test', h_name='test', type='', desc=None,
        db_name='elliptic_curves', coll_name='curvedata', field_name='label')
    return desc


def ec_simple_label_search(search, baseurl, label):
    lmfdb_label = None

    if '.' in label:
        lmfdb_label = label

    spliturl = label.split('/')
    if len(spliturl) == 3:
        lmfdb_label = spliturl[0] + '.' + spliturl[1] + spliturl[2]

    if lmfdb_label:
        search['query'] = {'lmfdb_label': lmfdb_label}
    else:
        search['query'] = {'label': label}
