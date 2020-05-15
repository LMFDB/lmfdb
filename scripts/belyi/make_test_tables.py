from lmfdb import db
# drop old tables
#db.drop_table('belyi_galmaps_test')
#db.drop_table('belyi_passports_test')
# make new test tables
db.create_table_like('belyi_galmaps_test', db.belyi_galmaps) # create empty table with same format as db.belyi_galmaps
db.create_table_like('belyi_passports_test', db.belyi_passports) # create empty table with same format as db.belyi_passports
# insert data
from psycopg2.sql import SQL # to import SQL functions
db._execute(SQL('INSERT INTO belyi_galmaps_test SELECT * FROM belyi_galmaps')) # insert data from belyi_galmaps into test table
db._execute(SQL('INSERT INTO belyi_passports_test SELECT * FROM belyi_passports')) # insert data from belyi_passports into test table
# create new columns
db.belyi_galmaps_test.add_column('old_label', 'text')
db.belyi_galmaps_test.add_column('old_plabel', 'text')
db.belyi_passports_test.add_column('old_plabel', 'text')
# update labels
#load("/scratch/home/sschiavo/github/lmfdb/scripts/belyi/new_labels.py") # load label-changing functions
from scripts.belyi import update_label_galmap, update_label_passport
db.belyi_galmaps_test.rewrite(update_label_galmap)
db.belyi_passports_test.rewrite(update_label_passport)
