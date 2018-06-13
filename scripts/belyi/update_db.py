import db
import os, sys, inspect
import subprocess

Cw = db.getDBconnection_write();

belyidb = Cw['belyi']
belyidb.drop_collection('passports_new');
belyidb.drop_collection('galmaps_new');
passports = belyidb['passports_new']
galmaps = belyidb['galmaps_new']

# import the raw data
# import ola
from raw_data import ola
# insert passports one at a time
passports_upload = [ elt[0] for elt in ola];
galmaps_upload = [];
for elt in ola:
    galmaps_upload += elt[1];

passports.insert_many(passports_upload);
galmaps.insert_many(galmaps_upload);
print passports.find().count()
print galmaps.find().count()


filename = inspect.getframeinfo(inspect.currentframe())[0];
folder = os.path.dirname(os.path.abspath(filename));
sys.path.append(os.path.join(folder, "../../"));
from data_mgt.utilities.rewrite import create_random_object_index, rewrite_collection
rewrite_collection(belyidb,"galmaps","galmaps_new",lambda x: x)
rewrite_collection(belyidb,"passports","passports_new",lambda x: x)
create_random_object_index(belyidb, "galmaps");
