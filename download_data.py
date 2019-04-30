from lmfdb.db_backend import db
from bson.json_util import dumps

def count_twos(label):
    return label.split('.')[-1].split('-').count('2')

hg = db.hgcwa_passports
sizes = [0 for i in range(10)]
file = open('families.json'.format(0), 'w')
#large_files = [open('largefamilies{0}.json'.format(i), 'w') for i in range(10)]



#Not include quotient genus greater than zero
#Pass in genus as the argument
gendata = list(hg.search({'genus': 2}))
families = set()
for i in range(len(gendata)):
    families.add(gendata[i]['label'])


for family in families:
    vectors = hg.search({'label': family},projection=[
        'label',
        'cc',
        'passport_label',
        'total_label',
        'gen_vectors',
        'group',
        'signature',
        'genus',
        'id'])
    file.write(dumps(vectors) + '\n')

file.close()