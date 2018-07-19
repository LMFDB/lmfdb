import db
import os, sys, inspect

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
print passports.find().count(), len(passports_upload)
print galmaps.find().count(), len(galmaps_upload)


filename = inspect.getframeinfo(inspect.currentframe())[0];
folder = os.path.dirname(os.path.abspath(filename));
sys.path.append(os.path.join(folder, "../../"));
# from data_mgt.utilities.rewrite import create_random_object_index, rewrite_collection
from data_mgt.utilities.rewrite import create_random_object_index
if "galmaps" in belyidb.collection_names():
    belyidb["galmaps"].rename("galmaps_old")
galmaps.rename("galmaps");
if "passports" in belyidb.collection_names():
    belyidb["passports"].rename("passports_old")
passports.rename("passports");
create_random_object_index(belyidb, "galmaps");
belyidb.drop_collection('passports_old');
belyidb.drop_collection('galmaps_old');
