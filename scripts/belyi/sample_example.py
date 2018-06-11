import db
Cw = db.getDBconnection_write();

belyidb = Cw['belyi']
passports = belyidb['passports']
galmaps = belyidb['galmaps']


sample_pass = {
    'label':'sample-6T15-[5,5,5]-51-51-51-g1',
    'deg' : 6,
    'group' : '6T15',
    'aut_group' : [[ 3, 6, 5, 2, 1, 4 ],[ 5, 4, 1, 6, 2, 3 ]],
    'geomtype' : 'hyperbolic',
    'abc' : [5,5,5],
    'lambdas' : [[5,1], [5,1], [5,1]],
    'g' : 1,
    'maxdegbf' : 2,
    'pass_size' : 8,
    'num_orbits' : 3
              };

#insert the sample passport
passports.insert_one(sample_pass);

#loops over all passports
for elt in passports.find():
    for key, val in  elt.iteritems():
        print "%s : %s" % (key, val.__repr__())

    print "############"
    print "############"

passports.delete_one({'label':'sample-6T15-[5,5,5]-51-51-51-g1'})
passports.find().count()
