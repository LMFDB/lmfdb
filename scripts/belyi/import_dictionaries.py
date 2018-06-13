import db
Cw = db.getDBconnection_write();

belyidb = Cw['belyi']
passports = belyidb['passports']
galmaps = belyidb['galmaps']

# import the raw data
# import ola
from raw_data import ola
# insert passports one at a time
for i in range(0,len(ola)):
    passports.insert_one(ola[i][0])

# insert galmaps one at a time
for i in range(0,len(ola)):
    for j in range(0,len(ola[i][1])):
        galmaps.insert_one(ola[i][1][j])

print passports.find().count()
print galmaps.find().count()

import os, sys, inspect
filename = inspect.getframeinfo(inspect.currentframe())[0];
folder = os.path.dirname(os.path.abspath(filename));
sys.path.append(os.path.join(folder, "../../"));
from data_mgt.utilities.rewrite import create_random_object_index
create_random_object_index(belyidb, "galmaps");
