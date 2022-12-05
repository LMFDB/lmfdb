# -*- coding: utf-8 -*-
r""" Functions to check consistency of data between elliptic curves and
Bianchi Modular Forms databases:  """


# 2020-04-15: first version by JEC

from sage.all import EllipticCurve, polygen, QQ, NumberField
from lmfdb import db
from lmfdb.nfutils.psort import primes_iter
from lmfdb.ecnf.WebEllipticCurve import parse_ainvs

print("setting nfcurves")
nfcurves = db.ec_nfcurves

print("setting bmf forms")
forms = db.bmf_forms

fields = ['2.0.{}.1'.format(d) for d in [4,8,3,7,11]]
x = polygen(QQ)

polys = {'2.0.4.1': x**2+1, '2.0.8.1': x**2+2, '2.0.3.1': x**2-x+1,
         '2.0.7.1': x**2-x+2, '2.0.11.1': x**2-x+3, }

gen_names = {'2.0.4.1': 'i', '2.0.8.1': 't', '2.0.3.1': 'w',
             '2.0.7.1': 'a', '2.0.11.1': 'a', }

false_curves = {'2.0.4.1': ['34225.7-a', '34225.7-b', '34225.3-a', '34225.3-b'],
                
                '2.0.8.1': ['5625.1-b', '5625.3-b', '6561.5-a', '6561.5-d',
                            '21609.1-b', '21609.1-c', '21609.3-b', '21609.3-c'],

                '2.0.3.1': ['67081.3-a', '67081.3-b', '67081.7-a', '67081.7-b', '61009.1-a',
                            '61009.1-b', '61009.9-a', '61009.9-b', '123201.1-b', '123201.1-c',
                            '123201.3-b', '123201.3-c', '5625.1-a', '6561.1-b', '30625.1-a',
                            '30625.3-a', '50625.1-c', '50625.1-d', '65536.1-b', '65536.1-e', '104976.1-a'],

                '2.0.7.1': ['10000.1-b', '10000.5-b', '30625.1-c', '30625.1-e', '30625.1-d',
                            '40000.1-b', '40000.7-b'],

                '2.0.11.1': [] }
                

def field_from_label(lab):
    r"""
    Returns a number field from its LMFDB label. IQF only.

    INPUT:

    - ``s`` (string)-- an LMFDB field label of the form 2.0.d.1

    OUTPUT:

    A number field, Q(sqrt(-d)) with standard defining polynomial
    """
    K = NumberField(polys[lab], gen_names[lab])
    print("Created field from label {}: {}".format(lab,K))
    return K

# check_curves() is adapted from the hmf_check_find function
# find_curves().  For IQ fields it does no curve searching but does
# check whether there is a curve matching each Bianchi newform in the
# database.  Here 'matching' means same label, conductor=label and ap
# agree.  This must allow for the valid non-existence of curves for
# some newforms.
    
def check_curves(field_label='2.0.4.1', min_norm=0, max_norm=None, label=None, check_ap = False, verbose=False):
    r"""Go through all Bianchi Modular Forms with the given field label,
    assumed imaginary quadratic (i.e. '2.0.d.1' with d in
    {4,8,3,7,11}), check whether an elliptic curve exists with the
    same label.  If so, and if check_ap is True, check that the a_P agree.

    """
    if field_label not in fields:
        print("No BMF data available for field {}".format(field_label))
        return
    else:
        K = field_from_label(field_label)
    print("Checking forms over {}, norms from {} to {}".format(field_label,min_norm,max_norm))
    query = {}
    query['field_label'] = field_label
    query['dimension'] = 1  # only look at rational newforms
    if label:
        print("looking for {} only".format(label))
        query['short_label'] = label # e.g. '91.1-a'
    else:
        query['level_norm'] = {'$gte': int(min_norm)}
        if max_norm:
            query['level_norm']['$lte'] = int(max_norm)
    cursor = forms.search(query, sort=['level_norm'])
    labels = [f['short_label'] for f in cursor]
    nforms = len(labels)
    print("found {} newforms".format(nforms))
    labels = [lab for lab in labels if lab not in false_curves[field_label]]
    nforms = len(labels)
    print("  of which {} should have associated curves (not false ones)".format(nforms))
    nfound = 0
    nnotfound = 0
    nok = 0
    missing_curves = []
    mismatches = []
    
    primes = list(primes_iter(K,maxnorm=1000)) if check_ap else []
    curve_ap = {}  # curve_ap[conductor_label] will be a dict iso -> ap
    form_ap = {}  # form_ap[conductor_label]  will be a dict iso -> ap

    # Now look at all newforms, check that there is an elliptic
    # curve of the same label, and if so compare ap-lists.  The
    # dicts curve_ap and form_ap store these when there is
    # disagreement: e.g. curve_ap[conductor_label][iso_label] =
    # aplist.

    print("checking {} newforms".format(nforms))
    n = 0
    for curve_label in labels:
        n += 1
        if n%100==0:
            perc = 100.0*n/nforms
            print("{} forms checked ({}%)".format(n,perc))
        # We find the forms again since otherwise the cursor might timeout during the loop.
        label = "-".join([field_label,curve_label])
        if verbose:
            print("newform and isogeny class label {}".format(label))
        f = forms.lucky({'label':label})
        if f:
            if verbose:
                print("found newform with label {}".format(label))
        else:
            print("no newform in database has label {}!".format(label))
            continue
        ec = nfcurves.lucky({'class_label': label, 'number': 1})
        if ec:
            if verbose:
                print("curve with label %s found in the database" % curve_label)
            nfound += 1
            if not check_ap:
                continue
            ainvsK = parse_ainvs(K, ec['ainvs'])
            if verbose:
                print("E = {}".format(ainvsK))
            E = EllipticCurve(ainvsK)
            if verbose:
                print("constructed elliptic curve {}".format(E.ainvs()))
            good_flags = [E.has_good_reduction(P) for P in primes]
            good_primes = [P for (P, flag) in zip(primes, good_flags) if flag]
            if verbose:
                print("{} good primes".format(len(good_primes)))
            f_aplist = f['hecke_eigs']
            f_aplist = [ap for ap, flag in zip(f_aplist, good_flags) if flag]
            nap = len(f_aplist)
            if verbose:
                print("recovered {} ap from BMF".format(nap))
            aplist = [E.reduction(P).trace_of_frobenius() for P in good_primes[:nap]]
            if verbose:
                print("computed {} ap from elliptic curve".format(nap))
            if aplist[:nap] == f_aplist[:nap]:
                nok += 1
                if verbose:
                    print("Curve {} and newform agree! (checked {} ap)".format(ec['short_label'],nap))
            else:
                print("Curve {} does NOT agree with newform".format(ec['short_label']))
                mismatches.append(label)
                if verbose:
                    for P,aPf,aPc in zip(good_primes[:nap], f_aplist[:nap], aplist[:nap]):
                        if aPf!=aPc:
                            print("P = {} with norm {}".format(P,P.norm().factor()))
                            print("ap from curve: %s" % aPc)
                            print("ap from  form: %s" % aPf)
                if not ec['conductor_label'] in curve_ap:
                    curve_ap[ec['conductor_label']] = {}
                    form_ap[ec['conductor_label']] = {}
                curve_ap[ec['conductor_label']][ec['iso_label']] = aplist
                form_ap[ec['conductor_label']][f['label_suffix']] = f_aplist
        else:
            if verbose:
                print("No curve with label %s found in the database!" % curve_label)
            missing_curves.append(f['short_label'])
            nnotfound += 1

    # Report progress:

    n = nfound + nnotfound
    if nnotfound:
        print("Out of %s newforms, %s curves were found in the database and %s were not found" % (n, nfound, nnotfound))
    else:
        print("Out of %s newforms, all %s had curves with the same label and ap" % (n, nfound))
    if nfound == nok:
        print("All curves agree with matching newforms")
    else:
        print("%s curves agree with matching newforms, %s do not" % (nok, nfound - nok))
    if nnotfound:
        print("%s missing curves" % len(missing_curves))
    else:
        pass
    if mismatches:
        print("{} form-curve pairs had inconsistent ap:".format(len(mismatches)))
        print(mismatches)

    
