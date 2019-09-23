# -*- coding: utf-8 -*-
r""" Functions to add ranks and generators to elliptic curves in the
database by outputting a Magma script and parsing its output """

# 2019-02-27: converted to work with the postgres database (JEC)

from lmfdb import db

print "setting nfcurves and qcurves"
nfcurves = db.ec_nfcurves
qcurves = db.ec_curves

from sage.all import EllipticCurve
from scripts.ecnf.import_ecnf_data import nf_lookup
from lmfdb.ecnf.WebEllipticCurve import parse_ainvs

def MWShaInfo(E, HeightBound=None, test_saturation=False, verbose=False):
    r"""
    Interface to Magma's MordellWeilShaInformation function

    INPUT:

    - E : an elliptic curve defined over a number field (including Q)

    OUTPUT:

    a triple [rank_low_up, gens, sha_bound_dict] where

    - rank_bounds is a list of 2 integers [r1,r2] such r1 <= rank(E) <= r2

    - gens is a list of r1 independent points on E

    - sha_bound_dict is a dict with keys positive integers n, values rank bounds for Sha[n].

    EXAMPLE::

        sage: E = EllipticCurve('5077a1')
        sage: MWShaInfo(E)
        [[3, 3], [(2 : -1 : 1), (9/4 : -15/8 : 1), (-1 : 3 : 1)], {2: [0, 0]}]

    """
    K = E.base_field()

    def convert_point(P):
        return E([K(c.sage()) for c in P.Eltseq()])
    if verbose:
        print("calling magma...")
    from sage.all import magma
    if HeightBound is None:
        MWSI = magma(E).MordellWeilShaInformation(nvals=3)
    else:
        MWSI = magma(E).MordellWeilShaInformation(nvals=3, HeightBound=HeightBound)
    if verbose:
        print("...done.")
    rank_bounds = MWSI[0].sage()
    gens = [convert_point(P) for P in MWSI[1]]
    sha_bound_dict = dict(MWSI[2].sage())
    if gens and test_saturation:
        if verbose:
            print("testing that Magma's generators are saturated...")
        newgens, index, newreg = E.saturation(gens, verbose)
        if index > 1:
            # Must print this even if not verbose!
            print("Magma's generators for curve %s were not saturated!  index = %s" % (E.ainvs(), index))
            gens = newgens
        else:
            if verbose:
                print("... and they are!")
    return [rank_bounds, gens, sha_bound_dict]


def map_points(maps, source, Plist, verbose=False):
    r""" Given a matrix of isogenies and a list of points on one curve (with
    index 'source'), returns a list of their images on each other curve.
    Since the isogenies only exist for some i,j pairs, we need to know
    an index 'source' such that following the maps from that curve will
    cover the class, and the initial points must be on that curve.

    We assume that the original points are saturated; after mapping
    under a p-isogeny theimages may not be p-saturated so additional
    p-saturation is done.  This requires Sage version 6.9 (pending) or
    the working branch at http://trac.sagemath.org/ticket/8829.
    """
    ncurves = len(maps)
    if ncurves == 1:
        return [Plist]
    Qlists = [[]] * ncurves
    Qlists[source] = Plist
    if len(Plist) == 0:
        return Qlists
    nfill = 1
    # print("Qlists = %s" % Qlists)
    # while True: // OK if input satisfies the conditions, but otherwise would loop for ever
    for nstep in range(ncurves):  # upper bound for number if iterations needed
        for i in range(ncurves):
            for j in range(ncurves):
                if Qlists[i] != [] and (maps[i][j] != 0) and Qlists[j] == []:
                    # print("Mapping from %s to %s at step %s" % (i,j,nstep))
                    phi = maps[i][j]
                    p = phi.degree()  # a prime
                    Qlists[j] = [maps[i][j](P) for P in Qlists[i]]
                    # now do p-saturation (if possible)
                    try:
                        E = Qlists[j][0].curve()
                        pts, index, reg = E.saturation(Qlists[j], one_prime=p)
                        if index > 1:
                            Qlists[j] = E.lll_reduce(pts)[0]
                            if True:  # verbose:
                                print("%s-saturation needed on curve %s, gaining index %s" % (p, list(E.ainvs()), index))
                        else:
                            if verbose:
                                print("image points on curve %s already %s-saturated" % (j, p))
                    except AttributeError:
                        print("Unable to %s-saturate, use a newer Sage version!" % p)
                    # print("...now Qlists = %s" % Qlists)
                    nfill += 1
                    if nfill == ncurves:
                        return Qlists
    if nfill < ncurves:
        raise RuntimeError("In map_points, failed to cover the class!")


def MWInfo_class(Cl, HeightBound=None, test_saturation=False, verbose=False):
    r"""
    Get MW info for all curves in the class

    INPUT:

    - Cl: an isogeny class

    OUTPUT:

    A list of pairs [rank_bounds, gens], one for each curve in the class.
    """
    # source = find_source(Cl.isogenies())
    # adiscs = [E.discriminant().norm().abs() for E in Cl.curves]
    # print("Abs disc list: %s" % adiscs)
    ss = [len(str(E.ainvs())) for E in Cl.curves]
    source = ss.index(min(ss))
    if verbose:
        print("Using curve %s to find points" % list(Cl.curves[source].ainvs()))
    MWI = MWShaInfo(Cl.curves[source], HeightBound=HeightBound, test_saturation=test_saturation, verbose=verbose)[:2]  # ignore Sha part
    return [[MWI[0], pts] for pts in map_points(Cl.isogenies(), source, MWI[1], verbose)]


def find_source(maps):
    r""" maps is an nxn array representing a directed graph on n vertices,
    with some entries 0 and some non-zero.  There will be at least one
    index i such that starting from vertex i you can reach every
    vertex, and we return such an i.  For example if
    maps=[[0,0],[1,0]] then vertex 1 is good but vertex 0 is not!
    """
    from sage.all import union
    n = len(maps)
    mat = [[int((maps[i][j] != 0) or (i == j)) for j in range(n)] for i in range(n)]
    # print("mat = %s" % mat)
    children = [[j for j in range(n) if mat[i][j]] for i in range(n)]
    for nstep in range(n):  # upper bound for number if iterations needed
        for i in range(n):
            for j in children[i]:
                children[i] = union(children[i], children[j])
                if len(children[i]) == n:
                    # print("source = %s" % i)
                    return i
    raise ValueError("find_source problem with mat=%s: at end, children = %s but no source found!" % (mat, children))


def MWInfo_curves(curves, HeightBound=None, test_saturation=False, verbose=False):
    r""" Get MW info for all curves in the list; this is a list of all
    curves in a class in some order, where we do not have the maps
    between them, so we recompute the class with maps and take into
    account the order of the curves.

    INPUT:

    - Cl: an isogeny class

    OUTPUT:

    A list of pairs [rank_bounds, gens], one for each class.
    """
    Cl = curves[0].isogeny_class()
    MWI = MWInfo_class(Cl, HeightBound=HeightBound, test_saturation=test_saturation, verbose=verbose)
    # Now we must map the points to the correct curves!

    n = len(Cl.curves)
    fixed_MWI = range(n)  # just to set length
    for i in range(n):
        E = curves[i]
        j = Cl.index(E)  # checks for isomorphism, not just equality
        iso = Cl.curves[j].isomorphism_to(E)
        # print("(i,j)=(%s,%s)" % (i,j))
        fixed_MWI[i] = [MWI[j][0], [iso(P) for P in MWI[j][1]]]

    # Check we have it right:
    assert all([all([P in curves[i] for P in fixed_MWI[i][1]]) for i in range(n)])
    return fixed_MWI


def old_encode_point(P):
    r"""
    Converts a point [x,y,z] into a 3-list of d-lists of strings
    """
    return [[str(x) for x in list(c)] for c in list(P)]

def encode_point(P):
    r"""
    Converts a point into a string encoding a 3-list of d-lists of rationals
    """
    return str([list(c) for c in list(P)]).replace(" ","")

def encode_points(Plist):
    r"""
    Converts a list of points into a list of lists of 3 lists of d lists of strings
    """
    return [encode_point(P) for P in Plist]

def make_curve(dbCurve):
    nf = nf_lookup(dbCurve['field_label'])
    ainvs = parse_ainvs(nf,dbCurve['ainvs'])
    return EllipticCurve(ainvs)

def get_generators(field, iso_class, test_saturation=False, verbose=False, store=False):
    r""" Retrieves the curves in the isogeny class from the database, finds
    their ranks (or bounds) and generators, and optionally stores the
    result back in the database.  """
    res = nfcurves.search({'field_label': field, 'short_class_label': iso_class})
    if not res:
        raise ValueError("No curves in the database ovver field %s in class %s" % (field, iso_class))
    Es = [make_curve(e) for e in res]
    if verbose:
        print("Curves in class %s: %s" % (iso_class, [E.ainvs() for E in Es]))
    mwi = MWInfo_curves(Es, HeightBound=2, test_saturation=test_saturation, verbose=verbose)
    if verbose:
        print("MW info: %s" % mwi)

    # res.rewind()

    # We find the curves again, since the cursor times out after 10
    # miniutes and finding the generators can take longer than that.

    res = nfcurves.search({'field_label': field, 'short_class_label': iso_class})
    for e, E, mw in zip(res, Es, mwi):
        label = e['label']
        data = {}
        data['rank_bounds'] = [int(r) for r in mw[0]]
        if mw[0][0] == mw[0][1]:
            data['rank'] = int(mw[0][0])
        gens = mw[1]
        data['gens'] = encode_points(gens)
        data['heights'] = [str(P.height()) for P in gens]
        data['reg'] = E.regulator_of_points(gens)
        if verbose:
            print("About to update curve {} using data {}".format(label, data))
        if store:
            nfcurves.upsert({'label':label}, data)
        else:
            if verbose:
                print("(not done, dummy run)")


def get_all_generators(field, min_cond_norm=None, max_cond_norm=None, test_saturation=False, verbose=False, store=False):
    r""" Retrieves curves from the database defined over the given field,
    with conductor norm between given bounds (optional), finds their
    ranks (or bounds) and generators, and optionally stores the result
    back in the database.  """
    query = {'field_label': field, 'number': int(1)}
    if min_cond_norm or max_cond_norm:
        query['conductor_norm'] = {}
    if min_cond_norm:
        query['conductor_norm']['$gte'] = int(min_cond_norm)
    if max_cond_norm:
        query['conductor_norm']['$lte'] = int(max_cond_norm)

    res_info = {}
    res = nfcurves.search(query, info=res_info)
    print("{} curves over field {} found".format(res_info['number'], field))

    # extract the class labels all at the start, since otherwise the
    # cursor might timeout:
    classes = [r['short_class_label'] for r in res]
    for isoclass in classes:
        res = nfcurves.lucky({'field_label': field, 'short_class_label': isoclass, 'number':int(1)})
        if False:#'rank' in res or 'rank_bounds' in res:
            print("Isogeny class {} already has rank data".format(isoclass))
        else:
            print("Getting generators for isogeny class {}".format(isoclass))
            get_generators(field, isoclass, test_saturation=test_saturation, verbose=verbose, store=store)

