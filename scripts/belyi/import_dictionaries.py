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

passports.find().count()
galmaps.find().count()
