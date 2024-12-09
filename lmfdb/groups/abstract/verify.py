#!/usr/bin/env python3
#from lmfdb.groups.abstract import verify
#TO DO:  subgroups, larger order + 1024


from lmfdb import db
from sage.all import libgap

def test_small_gps(sample_gp):
    print(sample_gp['label'])

    if sample_gp['order'] != 1024:  #1024 doesn't have standard labels, need to construct another way
        #create corresponding GAP group
        id_nums = sample_gp['label'].split(".")
        G = libgap.SmallGroup(int(id_nums[0]),int(id_nums[1]))
        #Confirm group order matches
        print("Group orders match: " + str(sample_gp['order'] == libgap.Order(G)))
        #Confirm IsAbelian returns same value
        print("Groups abelian-ness match: " + str((sample_gp['abelian']) == bool(libgap.IsAbelian(G))))
        #Confirm IsSimple returns same value
        print("Groups simple-ness match: " + str((sample_gp['simple']) == bool(libgap.IsSimple(G))))
        #Confirm IsPerfect returns same value
        print("Groups perfect-ness match: " + str((sample_gp['perfect']) == bool(libgap.IsPerfect(G))))
        #Confirm IsMonomial returns same value
        print("Groups monomial-ness match: " + str((sample_gp['monomial']) == bool(libgap.IsMonomial(G))))

        #Confirm number of non-conjugate subgroups (if known in database)
        if sample_gp['number_subgroup_classes']:
            SubLat = libgap.LatticeSubgroups(G)
            Cons = libgap.ConjugacyClassesSubgroups(SubLat)
            print("Number of subgroup classes match: " + str(libgap.Size(Cons) == sample_gp['number_subgroup_classes']))
        if sample_gp['number_normal_subgroups']:
            NormLat = libgap.NormalSubgroups(G)
            print("Number of normal subgroups match: " + str(libgap.Size(NormLat) == sample_gp['number_normal_subgroups']))

        # check if minimal permutation  degrees match
        if sample_gp['permutation_degree']:
            minpermdeg_gap = libgap.MinimalFaithfulPermutationDegree(G)
            print("Minimal permutation degrees match: " + str(minpermdeg_gap == sample_gp['permutation_degree']))

        # check order stats
        stupid_str = 'Set(ConjugacyClasses(SmallGroup(' + id_nums[0] + ',' + id_nums[1] + ")), z->Order(Representative(z))) "
        ords = libgap.eval(stupid_str)

        ordsLMFDB = []
        ords_list = sample_gp['order_stats']
        for i in range(len(ords_list)):
            ordsLMFDB.append(ords_list[i][0])
        print("Order set matches: " + str(ords == ordsLMFDB))
        # print(ords,ordsLMFDB)

        # check degrees
        irr_stats = sample_gp['irrep_stats']
        degLMFDB = []
        for i in range(len(irr_stats)):
            for j in range(irr_stats[i][1]):
                degLMFDB.append(irr_stats[i][0])
        stupid_str_2 = 'List(Irr(SmallGroup(' + id_nums[0] + ',' + id_nums[1] + ')), z -> z[1])'
        degs = libgap.eval(stupid_str_2)

        print("Degrees of characters match: " + str(degs == degLMFDB))
        # print(degs,degLMFDB)


# pick random group of order <= 2000 from DB

for i in range(10):
    x = db.gps_groups_test.random({'order': {"$lte" :2000}})
    sample_gp = db.gps_groups_test.lucky({'label': x})
    test_small_gps(sample_gp)
