# -*- coding: utf-8 -*-
r""" Import data for GL2 Maass forms (from yaml file) and
data for GLn Maass form L-functions including plot and zeros
from L-calc files.

To run this go into the top-level lmfdb directory, run sage and give
the command
%runfile lmfdb/modular_forms/maass_forms/import_maass_and_maass_lfun.py

"""

import yaml
from lmfdb.website import DEFAULT_DB_PORT as dbport

from pymongo.mongo_client import MongoClient
print "getting connection"
C= MongoClient(port=dbport)
print "authenticating on the L-functions and Maass forms database"

##pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
##username = pw_dict['data']['username']
##password = pw_dict['data']['password']
##
##C['Lfunctions'].authenticate(username, password)
##C['MaassWaveForms'].authenticate(username, password)

##L_maass_gl2 = C.Lfunctions.maass_gl2
##L_maass_gl3 = C.Lfunctions.maass_gl3
##L_maass_gl4 = C.Lfunctions.maass_gl4
##maass_gl2 = C.MaassWaveForms.maass_gl2

def insertMaassGL2FromFiles(base_path, min_N, max_N):
    for N in xrange(min_N, max_N):
        fileName = base_path + str(N) + ".yaml"
        stream = open(fileName, "r")
        docs = yaml.load_all(stream)
        for doc in docs:
                for k,v in doc.items():
                    print k, "->", v
                print "\n"

insertMaassGL2FromFiles("/home/stefan/Documents/Test",1,1)
