# -*- coding: utf-8 -*-
r""" Checking that knowls only cross-reference existing knowls

Initial version (Bristol March 2016)

"""
from lmfdb.knowledge.knowl import knowldb
from commands import getoutput

cats = knowldb.get_categories()
print("There are %s categories of knowl in the database" % len(cats))

def check_knowls(cat='ec', verbose=False):
    cat_knowls = knowldb.search(category=cat)
    if verbose:
        print("%s knowls in category %s" % (len(cat_knowls),cat))
    for k in cat_knowls:
        if verbose:
            print("Checking knowl %s" % k['id'])
        k = knowldb.get_knowl(k['id'])
        cont = k['content']
        all_content = cont
        cont = cont.replace("KNOWL ","KNOWL")
        i = 0
        while (i>=0):
            i = cont.find("KNOWL_INC")
            if i>=0:
                offset = 10
            else:
                i = cont.find("KNOWL")
                if i>=0:
                    offset=6
            if (i>=0):
                cont = cont[i+offset:]
                qu = cont[0]
                j = cont.find(qu,1)
                ref = cont[1:j]
                if verbose:
                    print("..cites %s" % ref)
                cont = cont[j+1:]
                the_ref = knowldb.get_knowl(ref)
                if the_ref is None:
                    print("Non-existing reference to %s in knowl %s" % (ref,k['id']))
                    print("content of {} = ".format(k['id']))
                    print(all_content)
                    return False
                elif verbose:
                    print("--- found")
    return True

def find_knowl_crossrefs(id, all=True, verbose=False):
    """Finds knowl(s) which cite the given knowl.

    if verbose, list the citing knowls (or just the first if
    all=False), otherwise just return True/False according to whether
    any other knowls cite the given one.

    EXAMPLE:

    sage: find_knowl_crossrefs("ec.q.torsion_order", verbose=True)
    knowl ec.q.torsion_order is cited by ec.q.bsd_invariants
    knowl ec.q.torsion_order is cited by ec.q.mordell-weil
    True

    """
    found = False
    for k in knowldb.search():
        content = knowldb.get_knowl(k['id'])['content']
        if id in content:
            found = True
            if verbose:
                print("knowl {} is cited by {}".format(id,k['id']))
            if not all or not verbose:
                return True
    return found    

def find_knowl_links(id, base=None, all=True, verbose=False):
    """Use grep to find the given knowl id in the source tree, assuming
    that to be based in the directory lmfdb in the current directory
    unless otherwise specified.

    EXAMPLE:

    sage: find_knowl_links("ec.q.torsion_order")
    /scratch/home/jcremona/lmfdb/lmfdb/elliptic_curves/templates/ec-isoclass.html:<th>{{ KNOWL('ec.q.torsion_order', title='Torsion order') }}</th>
    /scratch/home/jcremona/lmfdb/lmfdb/elliptic_curves/templates/ec-index.html:By {{ KNOWL('ec.q.torsion_order', torsion=t,title="torsion order") }}:
    /scratch/home/jcremona/lmfdb/lmfdb/elliptic_curves/templates/ec-index.html:          {{ KNOWL('ec.q.torsion_order',title="torsion order") }}
    /scratch/home/jcremona/lmfdb/lmfdb/elliptic_curves/templates/ec-search-results.html:<td align=left>{{ KNOWL('ec.q.torsion_order', title='Torsion order') }}</td>
    /scratch/home/jcremona/lmfdb/lmfdb/elliptic_curves/templates/ec-search-results.html:  <th class="center">{{ KNOWL('ec.q.torsion_order', title='Torsion order') }}</th>

    """
    if base==None:
        base = "~/lmfdb"
    found = False
    for L in getoutput('grep -r "{}" {}'.format(id, base)).splitlines():
        found = True
        if verbose:
            print L
        if not all or not verbose:
            return True
    return found

def uncited_knowls(ignore_top_and_bottom=True):
    """Lists all knowls not cited by other knowls.

    Knowls whose id ends in "top" or "bottom" are ignored by default.

    NB This lists a lot of knowls which are linked from code or
    templates so is not so useful by itself.

    """
    for k in knowldb.search():
        kid = k['id']
        if kid.endswith(".top") or kid.endswith(".bottom"):
            continue
        crossrefs = find_knowl_crossrefs(kid)
        links = find_knowl_links(kid)
        if crossrefs:
            print("{} is cited by other knowl(s)".format(kid))
        else:
            print("No other knowl cites {}".format(kid))
        if links:
            print("{} IS mentioned in the source code".format(kid))
        else:
            print("{} is NOT mentioned in the source code".format(kid))

"""
Result of running

sage: for cat in cats:
    check_knowls(cat, verbose=False)

on 30 March 2016:

Non-existing reference to ag.base_change in knowl ag.geom_simple
Non-existing reference to ag.dual_variety in knowl ag.ppav
Non-existing reference to doc.LMFDB.database in knowl doc.lmfdb.contextualize
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to ag.good_reduction in knowl g2c.lfunction
Non-existing reference to hgm.tame in knowl hgm.conductor
Non-existing reference to lfunction.normalization in knowl lfunction.central_value
Non-existing reference to mf.elliptic.hecke_operator in knowl mf.elliptic.coefficient_field
Non-existing reference to test.nonexisting in knowl test.text

Run on 2018-05-10:


Non-existing reference to doc.LMFDB.database in knowl doc.lmfdb.contextualize
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to lfunction.rh.proof in knowl doc.knowl.guidelines
Non-existing reference to mf.modular symbols in knowl hecke-algebra.defintion
Non-existing reference to mf.modular symbols in knowl hecke_algebra.definition
Non-existing reference to lattice.automorphism_group in knowl lattice.group_order
Non-existing reference to mf.siegel.weight in knowl mf.siegel.family.sp8z
Non-existing reference to mf.siegel.ikeda in knowl mf.siegel.family.sp8z
Non-existing reference to mf.siegel.miyawaki in knowl mf.siegel.family.sp8z
Non-existing reference to mf.siegel.weight in knowl mf.siegel.family.kp
Non-existing reference to mf.siegel.nonlift in knowl mf.siegel.family.kp
Non-existing reference to mf.siegel.pluriharmonic in knowl mf.siegel.family.gamma0_3
Non-existing reference to mf.siegel.pluriharmonic in knowl mf.siegel.family.gamma0_3_psi_3
Non-existing reference to test.nonexisting in knowl test.text
"""
