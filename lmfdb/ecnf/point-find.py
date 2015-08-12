# -*- coding: utf-8 -*-
r""" Functions to add ranks and generators to elliptic curves in the
database by outputting a Magma script and parsing its output """

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
from lmfdb.ecnf.hmf_check_find import (is_fundamental_discriminant, rqf_iterator)

print "calling base._init()"
dbport=37010
init(dbport, '')
print "getting connection"
conn = getDBConnection()
print "setting nfcurves, qcurves and fields"
nfcurves = conn.elliptic_curves.nfcurves
qcurves = conn.elliptic_curves.curves
fields = conn.numberfields.fields

############################################################
#
# Code to go through nfcurves database (for one field) to find curves
# (grouped into isogeny classes) and output Magma code to process
# these.
#
############################################################

def output_magma_field(field_label, outfilename=None, verbose=False):
    r"""
    Writes Magma code to a file to define a number field.

    INPUT:

    - ``field_label`` (str) -- a number field label

    - ``outfilename`` (string, default ``None``) -- name of file for output.

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.  If
      True, all output written to stdout.

    OUTPUT:

    Output goes to file and/or screen, nothing is returned.  Outputs
    Magma commands to define the field `K` with given label.
    """
    def output(L):
        if outfilename:
            outfile.write(L)
        if verbose:
            sys.stdout.write(L)

    if outfilename:
        outfile=file(outfilename, mode="w")

    F = fields.find_one({'label':field_label})
    if not F:
        raise ValueError("%s is not a field in the database!" % field_label)

    output("COEFFS := [%s];\n" % F['coeffs'])
    output("K<a> := NumberField(PolynomialRing(Rationals())!COEFFS);\n")

    if outfilename:
        output("\n")
        outfile.close()


def output_magma_point_search(curves, outfilename=None, verbose=False):
    r""" Outputs Magma script to search for an curve to match the newform
    with given label.

    INPUT:

    - ``curves`` -- a list or iterator of database elliptic curve
      objects (one complete isogeny class: the label will be taken
      from the furst one)

    - ``outfilename`` (string, default ``None``) -- name of output file

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.

    OUTPUT:

    Output goes to file and/or screen, nothing is returned. Outputs
    Magma commands to compute the rank and generators of the curves in
    the class.  The output will be appended to the file whose name is
    provided, so that the field definition can be output there first
    using the output_magma_field() function.
    """
    def output(L):
        if outfilename:
            outfile.write(L)
        if verbose:
            sys.stdout.write(L)
    if outfilename:
        outfile=file(outfilename, mode="a")

    try:
        curve1 = curves.next()
        curves.rewind()
    except AttributeError:  # it was a list, not an iterator
        curve1 = curves[0]

    all_ai = [[[int(c) for c in ai] for ai in e['ainvs']] for e in curves]
    all_ai_str = str(all_ai).replace(" ","")
    R = PolynomialRing(QQ,'a')
    all_ai_pols = [[R(ai) for ai in c] for c in all_ai]

    output('LABEL := ["%s","%s","%s"];\n' %
           (curve1['field_label'],
            curve1['conductor_label'],
            curve1['iso_label']))
    output("CURVES := %s;\n" % all_ai_str)
    output("CURVES := %s;\n" % all_ai_pols)
    output("PointSearch(LABEL,CURVES);\n")

    if outfilename:
        outfile.close()

##########################################
#
# Functions below here not ready for use!
#
##########################################

def magma_output_iter(infilename):
    r"""
    Read Magma search output

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
    Convert Magma search output to a curve_data file.

    INPUT:

    - ``infilename`` (string) -- name of file containing Magma output

    - ``outfilename`` (string, default ``None``) -- name of output file

    - ``verbose`` (boolean, default ``False``) -- verbosity flag.
    """
    if outfilename:
        outfile=file(outfilename, mode="w")

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
        output(make_curves_line(ec)+"\n")
