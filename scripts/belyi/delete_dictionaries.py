import db
Cw = db.getDBconnection_write();

belyidb = Cw['belyi']
passports = belyidb['passports']
galmaps = belyidb['galmaps']

passports.delete_many({})
galmaps.delete_many({})
