# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import comma, make_logger
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.db_backend import db

def field_data(s):
    r"""
    Returns full field data from field label.
    """
    deg, r1, abs_disc, n = [int(c) for c in s.split(".")]
    sig = [r1, (deg - r1) // 2]
    return [s, deg, sig, abs_disc]

def sort_field(F):
    r"""
    Returns data to sort by, from field label.
    """
    return [int(c) for c in F.split(".")]

logger = make_logger("ecnf")

def ecnf_summary():
    ecnfstats = db.ec_nfcurves.stats
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    deg_knowl = '<a knowl="nf.degree">degree</a>'
    data = ecnfstats.get_oldstat('conductor_norm')
    ncurves = comma(data['ncurves'])
    nclasses = comma(data['nclasses'])
    data = ecnfstats.get_oldstat('field_label')
    nfields = len(data['counts'])
    data = ecnfstats.get_oldstat('signatures_by_degree')
    maxdeg = max(int(d) for d in data if d!='_id')
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' in {} '.format(nclasses),
                    iso_knowl,
                    r', over {} '.format(nfields),
                    nf_knowl, ' (not including $\mathbb{Q}$) of ',
                    deg_knowl,
                    r' up to {}.'.format(maxdeg)])

def ecnf_field_summary(field):
    data = db.ec_nfcurves.stats.get_oldstat('conductor_norm_by_field')[field]
    ncurves = data['ncurves']
    s = '' if ncurves==1 else 's'
    ec_knowl = '<a knowl="ec">elliptic curve{}</a>'.format(s)
    nclasses = data['nclasses']
    s = '' if nclasses==1 else 'es'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny class{}</a>'.format(s)
    nf_knowl = '<a knowl="nf">number field</a>'
    max_norm = data['max_norm']
    s = '' if max_norm==1 else 's'
    cond_knowl = '<a knowl="ec.conductor">conductor{}</a>'.format(s)
    s = '' if max_norm==1 else 'up to '
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over the ',
                    nf_knowl,
                    r' {}, in {} '.format(field_pretty(field), nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm {} {}.'.format(s,data['max_norm'])])

def ecnf_signature_summary(sig):
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    r, s = [int(x) for x in sig.split(",")]
    d = r+2*s
    data = db.ec_nfcurves.stats.get_oldstat('conductor_norm_by_signature')[sig]
    ncurves = data['ncurves']
    nclasses = data['nclasses']
    max_norm = data['max_norm']
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of signature ({}) (degree {}), in {} '.format(sig, d, nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to {}.'.format(max_norm)])

def ecnf_degree_summary(d):
    ec_knowl = '<a knowl="ec">elliptic curves</a>'
    iso_knowl = '<a knowl="ec.isogeny_class">isogeny classes</a>'
    nf_knowl = '<a knowl="nf">number fields</a>'
    cond_knowl = '<a knowl="ec.conductor">conductors</a>'
    data = db.ec_nfcurves.stats.get_oldstat('conductor_norm_by_degree')[str(d)]
    ncurves = data['ncurves']
    nclasses = data['nclasses']
    max_norm = data['max_norm']
    return ''.join([r'The database currently contains {} '.format(ncurves),
                    ec_knowl,
                    r' defined over ',
                    nf_knowl,
                    r' of degree {}, in {} '.format(d, nclasses),
                    iso_knowl,
                    r', with ',
                    cond_knowl,
                    r' of norm up to {}.'.format(max_norm)])

@app.context_processor
def ctx_ecnf_summary():
    return {'ecnf_summary': ecnf_summary}
