from lmfdb import db
from lmfdb.sato_tate_groups.main import sg_pretty
import re

hgcwa_group = re.compile(r'\[(\d+),(\d+)\]')

def create_ug_file():
    f = open('scripts/higher_genus_w_automorphisms/unique-groups.txt', 'x')
    col_names = 'group|genus|g0_is_gt0|iso_class|gen_vectors|topologicals|braids\n'
    col_types = 'integer[]|smallint|boolean|text|integer|integer|integer\n'
    f.write(col_names)
    f.write(col_types)
    f.write('\n')
    data = compute_ug_data()
    for datum in data:
        line = '|'.join([str(val) for val in datum])
        f.write(line + '\n')
    f.close()

def compute_ug_data():
    data = []
    hgcwa = db.hgcwa_passports
    genus_list = hgcwa.distinct('genus')
    for genus in genus_list:
        # currently does not compute correct topological, braid numbers for g0 > 0 or genus > 7

        # rows for g0 = 0 table on unique groups page
        group_stats_0 = hgcwa.count({'genus':genus, 'g0': 0}, ['group'])
        for group, gen_vectors in group_stats_0.items():
            group = group[0]
            iso_class = sg_pretty(re.sub(hgcwa_group, r'\1.\2', group))
            labels = hgcwa.distinct('label', {'genus':genus, 'g0': 0, 'group': group})
            topologicals = braids = 0
            for label in labels:
                topologicals += len(hgcwa.distinct('topological', {'label': label}))
                braids += len(hgcwa.distinct('braid', {'label': label}))
            data.append([group, genus, False, iso_class, gen_vectors, topologicals, braids])

        # rows for g0 > 0 table on unique groups page
        group_stats_gt0 = hgcwa.count({'genus':genus, 'g0':{'$gt':0}}, ['group'])
        for group, gen_vectors in group_stats_gt0.items():
            group = group[0]
            iso_class = sg_pretty(re.sub(hgcwa_group, r'\1.\2', group))
            labels = hgcwa.distinct('label', {'genus':genus, 'g0':{'$gt':0}, 'group': group})
            topologicals = braids = 0
            for label in labels:
                topologicals += len(hgcwa.distinct('topological', {'label': label}))
                braids += len(hgcwa.distinct('braid', {'label': label}))
            data.append([group, genus, True, iso_class, gen_vectors, topologicals, braids])
    return data

