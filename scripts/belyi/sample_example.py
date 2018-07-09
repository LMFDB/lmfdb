import db
Cw = db.getDBconnection_write();

belyidb = Cw['belyi']
passports = belyidb['passports']
galmaps = belyidb['galmaps']

# sample passport
sample_pass = {
    'plabel':'6T15-[5,5,5]-51-51-51-g1',
    'deg' : 6,
    'group' : '6T15',
    'geomtype' : 'H',
    'abc' : [5,5,5],
    'lambdas' : [[5,1], [5,1], [5,1]],
    'g' : 1,
    'maxdegbf' : 2,
    'pass_size' : 8,
    'num_orbits' : 3
};

# sample galmap
sample_galmap = {
    'label':'6T15-[5,5,5]-51-51-51-g1-a',
    'plabel' : '6T15-[5,5,5]-51-51-51-g1',
    'triples' : [[[ 2, 3, 4, 5, 1, 6 ],[ 3, 1, 4, 6, 5, 2 ],[ 5, 2, 6, 1, 3, 4 ]],[[ 2, 3, 4, 5, 1, 6 ],[ 1, 3, 5, 6, 4, 2 ],[ 3, 1, 6, 2, 5, 4 ]]],
    'aut_group' : [[ 3, 6, 5, 2, 1, 4 ],[ 5, 4, 1, 6, 2, 3 ]],
    'base_field' : [4,-1,1],
    'embeddings' : [[0.500000, 1.93649], [0.500000, -1.93649]],
    'curve' : "y^2 = x^3 + 1/160000*(657*nu - 5076)*x + 1/6400000*(-20013*nu - 34044)",
    'map' :"(1/200000*(11745*nu - 17172)*x^2 + 1/625000*(19197*nu - 41796)*x + 1/32000000000*(12725667*nu - 373299516))/(x^6 + 1/200*(21*nu + 12)*x^5 + 1/32000*(1935*nu + 8532)*x^4 + 1/3200000*(-106701*nu + 262020)*x^3 + 1/5120000000*(-28837917*nu - 9389628)*x^2 + 1/5120000000000*(70827885*nu - 3813131268)*x + 1/4096000000000000*(36228501693*nu - 41819362884))*y + (1/200000*(-11745*nu + 17172)*x^3 + 1/80000000*(-26973*nu + 1192644)*x^2 + 1/160000000000*(668868435*nu + 309542148)*x + 1/64000000000000*(35387022501*nu - 38387253348))/(x^6 + 1/200*(21*nu + 12)*x^5 + 1/32000*(1935*nu + 8532)*x^4 + 1/3200000*(-106701*nu + 262020)*x^3 + 1/5120000000*(-28837917*nu - 9389628)*x^2 + 1/5120000000000*(70827885*nu - 3813131268)*x + 1/4096000000000000*(36228501693*nu - 41819362884))",
    'orbit_size' : 2,
    'deg' : 6,
    'group' : '6T15',
    'geomtype' : 'H',
    'abc' : [5,5,5],
    'abc_sorted' : [5,5,5],
    'lambdas' : [[5,1], [5,1], [5,1]],
    'g' : 1
};

#insert the sample passport
passports.insert_one(sample_pass);

#insert the sample galmap
galmaps.insert_one(sample_galmap);

#loops over all passports
for elt in passports.find():
    for key, val in  elt.iteritems():
        print("%s : %s") % (key, val.__repr__())

for elt in galmaps.find():
    for key, val in  elt.iteritems():
        print("%s : %s") % (key, val.__repr__())

    print("############")
    print("############")

# passports.delete_one({'plabel':'6T15-[5,5,5]-51-51-51-g1'})
passports.find().count()
