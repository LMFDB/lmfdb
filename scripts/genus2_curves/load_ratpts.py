# -*- coding: utf-8 -*-

import lmfdb
import ast
import pymongo

# expected input file format is
# label:eqn:rank:ratpts:ratpts-verified:mwgroup:mwgens:mwgroup-verified:rank-verified
# ratpts contains a list of triples of ints representing projective points
# mwgroup is a list of invariants for finitely generated abelian group (0 means Z/0 = Z)
# mwgens is a list of degree 0 divisors on the Jacobian in Magma's Mumford representation

def load_ratpts_data(filename):
    db = lmfdb.base.getDBConnection().genus2_curves
    with open(filename,'r') as input_file:
        data = input_file.read()
    outrecs = []
    for inrec in data.split('\n'):
        if not inrec:
            break
        items = inrec.split(':')
        assert len(items) == 9
        label = items[0]
        Lrank = int(items[2])
        ratpts = ast.literal_eval(items[3])
        ratpts_v = True if int(items[4]) == 1 else False
        mwgroup = ast.literal_eval(items[5])
        mwrank = len([n for n in mwgroup if n == 0])
        mwgens = ast.literal_eval(items[6])
        mwgroup_v = True if int(items[7]) == 1 else False
        mwrank_v = True if int(items[8]) == 1 else False
        if mwrank < Lrank and not mwrank_v:
            print "Skipping record for %s with unverified mwrank %d < Lrank %d"%(label,mwrank,Lrank)
            continue
        if mwrank != Lrank:
            "Hooray you have found a counterexample to BSD! Or your data is wrong/incomplete :("
            print inrec
            #return
        rec = { 'label': label,
                'num_rat_pts': int(len(ratpts)),
                'rat_pts': [[str(c) for c in p] for p in ratpts],
                'rat_pts_v': bool(ratpts_v),
                'mw_group' : [int(a) for a in mwgroup],
                'mw_rank' : int(mwrank),
                'mw_gens' : mwgens, # divisor coefficients should already be encoded as strings
                'mw_group_v': bool(mwgroup_v),
                'mw_rank_v': bool(mwrank_v) }
        outrecs.append(rec)
    print "Loading %d records to ratpts collection...\n"%len(outrecs)
    #db.ratpts.insert_many(outrecs)
    print "...done!"
    if db.ratpts.new.count() > 0:
        print "overwriting existing ratpts.new"
        db.ratpts.new.drop()
    db.ratpts.new.insert_many(outrecs)
    assert db.ratpts.new.count() == len(outrecs)
    if db.ratpts.old.count() > 0:
        db.ratpts.old.drop()
    db.ratpts.rename('ratpts.old')
    db.ratpts.new.rename('ratpts.new')

