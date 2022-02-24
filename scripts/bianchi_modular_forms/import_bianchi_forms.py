# -*- coding: utf-8 -*-
r""" Import newforms to Bianchi database of newforms

Initial version (Warwick June 2017): John Cremona
Revised for postgres (2020)
May 2021: Replaced by scripts in https://github.com/JohnCremona/bianchi-progs/blob/master/bianchi.py

"""


from lmfdb import db
print("setting dims")
dims = db.bmf_dims
print("setting forms")
forms = db.bmf_forms


def curve_check(fld, min_norm=1, max_norm=None):
    nfcurves = db.ec_nfcurves
    # first check numbers
    norm_range = {}
    norm_range['$gte'] = min_norm
    if max_norm is not None:
        norm_range['$lte'] = max_norm
    print("Checking field {}, norm range {}".format(fld, norm_range))
    form_query = {'field_label':fld, 'dimension':1, 'level_norm':norm_range}
    curve_query = {'field_label':fld, 'number':1, 'conductor_norm':norm_range}
    nforms = forms.count(form_query)
    ncurves = len([c for c in nfcurves.search(curve_query) if 'CM' not in c['label']])
    if nforms == ncurves:
        print("# curves = # forms = {}".format(ncurves))
    else:
        print("# curves = {} but # forms = {}".format(ncurves, nforms))
    if nforms>ncurves:
        print("{} curves missing".format(nforms-ncurves))
    print("Checking whether there is a curve for each newform...")
    n = 0
    for f in forms.search(form_query):
        lab = f['label']
        nc = nfcurves.count({'class_label':lab})
        if nc==0:
            print("newform {} has no curve (bc={}, cm={})".format(lab,f['bc'],f['CM']))
            n +=1
    if n==0:
        print("no missing curves")
    else:
        print("{} missing curves listed".format(n))
    print("Checking whether there is a newform for each non-CM curve...")
    n = 0
    for f in nfcurves.search(curve_query):
        lab = f['class_label']
        if 'CM' in lab:
            continue
        nf = forms.count({'label':lab})
        if nf==0:
            print("curve class {} has no newform".format(lab))
            n +=1
    if n==0:
        print("no missing newforms")
    else:
        print("{} missing newforms listed".format(n))

