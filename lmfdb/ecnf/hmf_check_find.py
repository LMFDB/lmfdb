# -*- coding: utf-8 -*-
r""" Functions to check consistency of data between elliptic curves and
Hilbert Modular Forms databases:  """

import os.path
import gzip
import re
import sys
import time
import os
import random
import glob
import pymongo
from lmfdb.base import _init as init
from lmfdb.base import getDBConnection
from sage.rings.all import ZZ, QQ
from sage.databases.cremona import cremona_to_lmfdb

print "calling base._init()"
dbport = 37010
init(dbport, '')
print "getting connection"
conn = getDBConnection()
print "setting nfcurves"
nfcurves = conn.elliptic_curves.nfcurves
qcurves = conn.elliptic_curves.curves

#
#
# Code to check conductor labels agree with Hilbert Modular Form level
# labels for a real quadratic field.  So far run on all curves over
# Q(sqrt(5)).
#
#

from lmfdb.hilbert_modular_forms.hilbert_field import HilbertNumberField


def make_conductor(ecnfdata, hfield):
    N, c, d = [ZZ(c) for c in ecnfdata['conductor_ideal'][1:-1].split(',')]
    return hfield.K().ideal([N // d, c + d * hfield.K().gen()])


def check_ideal_labels(field_label='2.2.5.1', min_norm=0, max_norm=None, fix=False, verbose=False):
    r""" Go through all curves with the given field label, assumed totally
    real, check whether the ideal label agrees with the level_label of
    the associated Hilbert Modular Form.
    """
    hmfs = conn.hmfs
    forms = hmfs.forms
    fields = hmfs.fields
    query = {}
    query['field_label'] = field_label
    query['conductor_norm'] = {'$gte': int(min_norm)}
    if max_norm:
        query['conductor_norm']['$lte'] = int(max_norm)
    else:
        max_norm = 'infinity'
    cursor = nfcurves.find(query)
    nfound = 0
    nnotfound = 0
    K = HilbertNumberField(field_label)
    # NB We used to have 20 in the next line but that is insufficient
    # to distinguish the a_p for forms 2.2.12.1-150.1-a and
    # 2.2.12.1-150.1-b !
    primes = [P['ideal'] for P in K.primes_iter(30)]
    remap = {}  # remap[old_label] = new_label

    for ec in cursor:
        fix_needed = False
        cond_label = ec['conductor_label']
        if cond_label in remap:
            new_cond_label = remap[cond_label]
            fix_needed = (cond_label != new_cond_label)
            if not fix_needed:
                if verbose:
                    print("conductor label %s ok" % cond_label)
        else:
            conductor = make_conductor(ec, K)
            level = K.ideal(cond_label)
            new_cond_label = K.ideal_label(conductor)
            remap[cond_label] = new_cond_label
            fix_needed = (cond_label != new_cond_label)

        if fix_needed:
            print("conductor label for curve %s is wrong, should be %s not %s" % (ec['label'], new_cond_label, cond_label))
            if fix:
                iso = ec['iso_label']
                num = str(ec['number'])
                newlabeldata = {}
                newlabeldata['conductor_label'] = new_cond_label
                newlabeldata['short_class_label'] = '-'.join([new_cond_label, iso])
                newlabeldata['short_label'] = ''.join([newlabeldata['short_class_label'], num])
                newlabeldata['class_label'] = '-'.join([field_label,
                                                        newlabeldata['short_class_label']])
                newlabeldata['label'] = '-'.join([field_label,
                                                  newlabeldata['short_label']])
                nfcurves.update({'_id': ec['_id']}, {"$set": newlabeldata}, upsert=True)
        else:
            if verbose:
                print("conductor label %s ok" % cond_label)

    return dict([(k, remap[k]) for k in remap if not k == remap[k]])

#
#
# Code to check isogeny class labels agree with Hilbert Modular Form
# labels of each level, for a real quadratic field.  Tested on all
# curves over Q(sqrt(5)).
#
#


def check_curve_labels(field_label='2.2.5.1', min_norm=0, max_norm=None, fix=False, verbose=False):
    r""" Go through all curves with the given field label, assumed totally
    real, test whether a Hilbert Modular Form exists with the same
    label.
    """
    hmfs = conn.hmfs
    forms = hmfs.forms
    fields = hmfs.fields
    query = {}
    query['field_label'] = field_label
    query['number'] = 1  # only look at first curve in each isogeny class
    query['conductor_norm'] = {'$gte': int(min_norm)}
    if max_norm:
        query['conductor_norm']['$lte'] = int(max_norm)
    else:
        max_norm = 'infinity'
    cursor = nfcurves.find(query)
    nfound = 0
    nnotfound = 0
    nok = 0
    bad_curves = []
    K = HilbertNumberField(field_label)
    primes = [P['ideal'] for P in K.primes_iter(30)]
    curve_ap = {}  # curve_ap[conductor_label] will be a dict iso -> ap
    form_ap = {}  # form_ap[conductor_label]  will be a dict iso -> ap

    # Step 1: look at all curves (one per isogeny class), check that
    # there is a Hilbert newform of the same label, and if so compare
    # ap-lists.  The dicts curve_ap and form_ap store these when
    # there is disagreement:
    # e.g. curve_ap[conductor_label][iso_label] = aplist.

    for ec in cursor:
        hmf_label = "-".join([ec['field_label'], ec['conductor_label'], ec['iso_label']])
        f = forms.find_one({'field_label': field_label, 'label': hmf_label})
        if f:
            if verbose:
                print("hmf with label %s found" % hmf_label)
            nfound += 1
            ainvsK = [K.K()([QQ(str(c)) for c in ai]) for ai in ec['ainvs']]
            E = EllipticCurve(ainvsK)
            good_flags = [E.has_good_reduction(P) for P in primes]
            good_primes = [P for (P, flag) in zip(primes, good_flags) if flag]
            aplist = [E.reduction(P).trace_of_frobenius() for P in good_primes[:10]]
            f_aplist = [int(a) for a in f['hecke_eigenvalues'][:30]]
            f_aplist = [ap for ap, flag in zip(f_aplist, good_flags) if flag][:10]
            if aplist == f_aplist:
                nok += 1
                if verbose:
                    print("Curve %s and newform agree!" % ec['short_label'])
            else:
                bad_curves.append(ec['short_label'])
                print("Curve %s does NOT agree with newform" % ec['short_label'])
                if verbose:
                    print("ap from curve: %s" % aplist)
                    print("ap from  form: %s" % f_aplist)
                if not ec['conductor_label'] in curve_ap:
                    curve_ap[ec['conductor_label']] = {}
                    form_ap[ec['conductor_label']] = {}
                curve_ap[ec['conductor_label']][ec['iso_label']] = aplist
                form_ap[ec['conductor_label']][f['label_suffix']] = f_aplist
        else:
            if verbose:
                print("No hmf with label %s found!" % hmf_label)
            nnotfound += 1

    # Report progress:

    n = nfound + nnotfound
    if nnotfound:
        print("Out of %s forms, %s were found and %s were not found" % (n, nfound, nnotfound))
    else:
        print("Out of %s classes of curve, all %s had newforms with the same label" % (n, nfound))
    if nfound == nok:
        print("All curves agree with matching newforms")
    else:
        print("%s curves agree with matching newforms, %s do not" % (nok, nfound - nok))
        # print("Bad curves: %s" % bad_curves)

    # Step 2: for each conductor_label for which there was a
    # discrepancy, create a dict giving the permutation curve -->
    # newform, so remap[conductor_label][iso_label] = form_label

    remap = {}
    for level in curve_ap.keys():
        remap[level] = {}
        c_dat = curve_ap[level]
        f_dat = form_ap[level]
        for a in c_dat.keys():
            aplist = c_dat[a]
            for b in f_dat.keys():
                if aplist == f_dat[b]:
                    remap[level][a] = b
                    break
    if verbose:
        print("remap: %s" % remap)

    # Step 3, for through all curves with these bad conductors and
    # create new labels for them, update the database with these (if
    # fix==True)

    for level in remap.keys():
        perm = remap[level]
        print("Fixing iso labels for conductor %s using map %s" % (level, perm))
        query = {}
        query['field_label'] = field_label
        query['conductor_label'] = level
        cursor = nfcurves.find(query)
        for ec in cursor:
            iso = ec['iso_label']
            if iso in perm:
                new_iso = perm[iso]
                if verbose:
                    print("--mapping class %s to class %s" % (iso, new_iso))
                num = str(ec['number'])
                newlabeldata = {}
                newlabeldata['iso_label'] = new_iso
                newlabeldata['short_class_label'] = '-'.join([level, new_iso])
                newlabeldata['class_label'] = '-'.join([field_label,
                                                        newlabeldata['short_class_label']])
                newlabeldata['short_label'] = ''.join([newlabeldata['short_class_label'], num])
                newlabeldata['label'] = '-'.join([field_label,
                                                  newlabeldata['short_label']])
                if verbose:
                    print("new data fields: %s" % newlabeldata)
                if fix:
                    nfcurves.update({'_id': ec['_id']}, {"$set": newlabeldata}, upsert=True)

#
#
# Code to go through HMF database to find newforms which should have
# associated curves, look to see if a suitable curve exists, and if
# not to create a Magma script to search for one.
#
#


def output_magma_field(field_label, K, Plist, outfilename=None, verbose=False):
    r"""
    Writes Magma code to a file to define a number field and list of primes.

    INPUT:

    - ``field_label`` (str) -- a number field label

    - ``K`` -- a number field.

    - ``Plist`` -- a list of prime ideals of `K`.

    - ``outfilename`` (string, default ``None``) -- name of file for output.

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.  If
      True, all output written to stdout.

    NOTE:

    Does not assumes the primes are principal.

    OUTPUT:

    (To file and/or screen, nothing is returned): Magma commands to
    define the field `K` and the list `Plist` of primes.
    """
    if outfilename:
        outfile = file(outfilename, mode="w")
    disc = K.discriminant()
    name = K.gen()
    pol = K.defining_polynomial()

    def output(L):
        if outfilename:
            outfile.write(L)
        if verbose:
            sys.stdout.write(L)
    output('print "Field %s";\n' % field_label)
    output("Qx<x> := PolynomialRing(RationalField());\n")
    output("K<%s> := NumberField(%s);\n" % (name, pol))
    output("OK := Integers(K);\n")
    output("Plist := [];\n")
    for P in Plist:
        Pgens = P.gens_reduced()
        Pmagma = "(%s)*OK" % Pgens[0]
        if len(Pgens) > 1:
            Pmagma += "+(%s)*OK" % Pgens[1]
        output("Append(~Plist,%s);\n" % Pmagma)
        # output("Append(~Plist,(%s)*OK);\n" % P.gens_reduced()[0])
    output('effort := 400;\n')
    # output definition of search function:
    output('ECSearch := procedure(class_label, N, aplist);\n')
    output('print "Isogeny class ", class_label;\n')
    output('goodP := [P: P in Plist | Valuation(N,P) eq 0];\n')
    output('goodP := [goodP[i]: i in [1..#(aplist)]];\n')
    output('curves := EllipticCurveSearch(N,effort : Primes:=goodP, Traces:=aplist);\n')
    output('curves := [E: E in curves | &and[TraceOfFrobenius(E,goodP[i]) eq aplist[i] : i in [1..#(aplist)]]];\n')
    output('if #curves eq 0 then print "No curve found"; end if;\n')
    output('for E in curves do;\n ')
    output('a1,a2,a3,a4,a6:=Explode(aInvariants(E));\n ')
    output('printf "Curve [%o,%o,%o,%o,%o]\\n",a1,a2,a3,a4,a6;\n ')
    output('end for;\n')
    output('end procedure;\n')
    output('SetColumns(0);\n')
    if outfilename:
        output("\n")
        outfile.close()


def output_magma_curve_search(HMF, form, outfilename=None, verbose=False):
    r""" Outputs Magma script to search for an curve to match the newform
    with given label.

    INPUT:

    - ``HMF`` -- a HilbertModularField

    - ``form``  -- a rational Hilbert newform from the database

    - ``outfilename`` (string, default ``None``) -- name of output file

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.

    OUTPUT:

    (To file and/or screen, nothing is returned): Magma commands to
    search for curves given their conductors and Traces of Frobenius,
    as determined by the level and (rational) Hecke eigenvalues of a
    Hilbert Modular Newform.  The output will be appended to the file
    whoswe name is provided, so that the field definition can be
    output there first using the output_magma_field() function.
    """
    def output(L):
        if outfilename:
            outfile.write(L)
        if verbose:
            sys.stdout.write(L)
    if outfilename:
        outfile = file(outfilename, mode="a")

    N = HMF.ideal(form['level_label'])
    Plist = [P['ideal'] for P in HMF.primes_iter(30)]
    goodP = [(i, P) for i, P in enumerate(Plist) if not P.divides(N)]
    label = form['short_label']
    if verbose:
        print("Missing curve %s" % label)
    aplist = [int(form['hecke_eigenvalues'][i]) for i, P in goodP]
    Ngens = N.gens_reduced()
    Nmagma = "(%s)*OK" % Ngens[0]
    if len(Ngens) > 1:
        Nmagma += "+(%s)*OK" % Ngens[1]
    output("ECSearch(\"%s\",%s,%s);\n" % (label, Nmagma, aplist))
    # output("ECSearch(\"%s\",(%s)*OK,%s);\n" % (label,N.gens_reduced()[0],aplist))

    if outfilename:
        outfile.close()


def find_curve_labels(field_label='2.2.5.1', min_norm=0, max_norm=None, outfilename=None, verbose=False):
    r""" Go through all Hilbert Modular Forms with the given field label,
    assumed totally real, for level norms in the given range, test
    whether an elliptic curve exists with the same label.
    """
    hmfs = conn.hmfs
    forms = hmfs.forms
    fields = hmfs.fields
    query = {}
    query['field_label'] = field_label
    if fields.count({'label': field_label}) == 0:
        if verbose:
            print("No HMF data for field %s" % field_label)
        return None

    query['dimension'] = 1  # only look at rational newforms
    query['level_norm'] = {'$gte': int(min_norm)}
    if max_norm:
        query['level_norm']['$lte'] = int(max_norm)
    else:
        max_norm = 'infinity'
    cursor = forms.find(query)
    nfound = 0
    nnotfound = 0
    nok = 0
    missing_curves = []
    K = HilbertNumberField(field_label)
    primes = [P['ideal'] for P in K.primes_iter(100)]
    curve_ap = {}  # curve_ap[conductor_label] will be a dict iso -> ap
    form_ap = {}  # form_ap[conductor_label]  will be a dict iso -> ap

    # Step 1: look at all newforms, check that there is an elliptic
    # curve of the same label, and if so compare ap-lists.  The
    # dicts curve_ap and form_ap store these when there is
    # disagreement: e.g. curve_ap[conductor_label][iso_label] =
    # aplist.

    for f in cursor:
        curve_label = f['label']
        ec = nfcurves.find_one({'field_label': field_label, 'class_label': curve_label, 'number': 1})
        if ec:
            if verbose:
                print("curve with label %s found" % curve_label)
            nfound += 1
            ainvsK = [K.K()([QQ(str(c)) for c in ai]) for ai in ec['ainvs']]
            E = EllipticCurve(ainvsK)
            good_flags = [E.has_good_reduction(P) for P in primes]
            good_primes = [P for (P, flag) in zip(primes, good_flags) if flag]
            aplist = [E.reduction(P).trace_of_frobenius() for P in good_primes[:30]]
            f_aplist = [int(a) for a in f['hecke_eigenvalues'][:40]]
            f_aplist = [ap for ap, flag in zip(f_aplist, good_flags) if flag][:30]
            if aplist == f_aplist:
                nok += 1
                if verbose:
                    print("Curve %s and newform agree!" % ec['short_label'])
            else:
                print("Curve %s does NOT agree with newform" % ec['short_label'])
                if verbose:
                    print("ap from curve: %s" % aplist)
                    print("ap from  form: %s" % f_aplist)
                if not ec['conductor_label'] in curve_ap:
                    curve_ap[ec['conductor_label']] = {}
                    form_ap[ec['conductor_label']] = {}
                curve_ap[ec['conductor_label']][ec['iso_label']] = aplist
                form_ap[ec['conductor_label']][f['label_suffix']] = f_aplist
        else:
            if verbose:
                print("No curve with label %s found!" % curve_label)
            missing_curves.append(f['short_label'])
            nnotfound += 1

    # Report progress:

    n = nfound + nnotfound
    if nnotfound:
        print("Out of %s newforms, %s curves were found and %s were not found" % (n, nfound, nnotfound))
    else:
        print("Out of %s newforms, all %s had curves with the same label and ap" % (n, nfound))
    if nfound == nok:
        print("All curves agree with matching newforms")
    else:
        print("%s curves agree with matching newforms, %s do not" % (nok, nfound - nok))
    if nnotfound:
        print("Missing curves: %s" % missing_curves)
    else:
        return

    # Step 2: for each newform for which there was no curve, create a
    # Magma file containing code to search for such a curve.

    # First output Magma code to define the field and primes:
    if outfilename:
        output_magma_field(field_label, K.K(), primes, outfilename)
        if verbose:
            print("...output definition of field and primes finished")
    if outfilename:
        outfile = file(outfilename, mode="a")

    for nf_label in missing_curves:
        if verbose:
            print("Curve %s is missing..." % nf_label)
        form = forms.find_one({'field_label': field_label, 'short_label': nf_label})
        if not form:
            print("... form %s not found!" % nf_label)
        else:
            if verbose:
                print("... found form, outputting Magma search code")
            output_magma_curve_search(K, form, outfilename, verbose=verbose)


def magma_output_iter(infilename):
    r"""
    Read Magma search output, as an iterator yielding the curves found.

    INPUT:

    - ``infilename`` (string) -- name of file containing Magma output
    """
    infile = file(infilename)

    while True:
        try:
            L = infile.next()
        except StopIteration:
            raise StopIteration

        if 'Field' in L:
            field_label = L.split()[1]
            K = HilbertNumberField(field_label)
            KK = K.K()
            w = KK.gen()

        if 'Isogeny class' in L:
            class_label = L.split()[2]
            cond_label, iso_label = class_label.split("-")
            num = 0

        if 'Curve' in L:
            ai = [KK(a.encode()) for a in L[7:-2].split(",")]
            num += 1
            yield field_label, cond_label, iso_label, num, ai

    infile.close()


def export_magma_output(infilename, outfilename=None, verbose=False):
    r"""
    Convert Magma search output to a curves file.

    INPUT:

    - ``infilename`` (string) -- name of file containing Magma output

    - ``outfilename`` (string, default ``None``) -- name of output file

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.
    """
    if outfilename:
        outfile = file(outfilename, mode="w")

    def output(L):
        if outfilename:
            outfile.write(L)
        if verbose:
            sys.stdout.write(L)

    K = None

    for field_label, cond_label, iso_label, num, ai in magma_output_iter(infilename):
        ec = {}
        ec['field_label'] = field_label
        if not K:
            K = HilbertNumberField(field_label)
        ec['conductor_label'] = cond_label
        ec['iso_label'] = iso_label
        ec['number'] = num
        N = K.ideal(cond_label)
        norm = N.norm()
        hnf = N.pari_hnf()
        ec['conductor_ideal'] = "[%i,%s,%s]" % (norm, hnf[1][0], hnf[1][1])
        ec['conductor_norm'] = norm
        ec['ainvs'] = [[str(c) for c in list(a)] for a in ai]
        ec['cm'] = '?'
        ec['base_change'] = []
        output(make_curves_line(ec) + "\n")


def is_fundamental_discriminant(d):
    if d in [0, 1]:
        return False
    if d.is_squarefree():
        return d % 4 == 1
    else:
        return d % 16 in [8, 12] and (d // 4).is_squarefree()


def rqf_iterator(d1, d2):
    for d in srange(d1, d2 + 1):
        if is_fundamental_discriminant(d):
            yield d, '2.2.%s.1' % d
