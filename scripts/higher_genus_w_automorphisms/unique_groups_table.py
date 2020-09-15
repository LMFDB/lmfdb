from lmfdb import db
import re

hgcwa_group = re.compile(r'\[(\d+),(\d+)\]')


def print_list(L):
    strg = '{'
    for l in range(1,len(L)):
       strg = strg + str(L[l-1]) + ','
    strg = strg + str(L[len(L)-1])
    strg = strg + '}'
    return strg


def create_ug_file():
    f = open('scripts/higher_genus_w_automorphisms/unique-groups.txt', 'x')
    col_names = 'group|genus|g0_is_gt0|g0_gt0_list|gen_vectors|topological|braid\n'
    col_types = 'integer[]|smallint|boolean|integer[]|integer|integer|integer\n'
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
    compdb = db.hgcwa_complete
    genus_list = hgcwa.distinct('genus')
    for genus in genus_list:
        # currently does not compute correct topological, braid numbers for g0 > 0 or genus > 7
        # rows for g0 = 0 table on unique groups page
        comp_info = compdb.lucky({'genus': genus},sort=[])
        group_stats_0 = hgcwa.count({'genus':genus, 'g0': 0}, ['group'])
        for group, gen_vectors in group_stats_0.items():        
            grp = group[0]
            grp_print = grp.replace('[','{').replace(']','}')
            labels = hgcwa.distinct('label', {'genus':genus, 'g0': 0, 'group': grp})
            if comp_info['top_braid_compute']:
                topological = braid = 0
                for label in labels:
                    topological += len(hgcwa.distinct('topological', {'label': label}))
                    braid += len(hgcwa.distinct('braid', {'label': label}))
                data.append([grp_print, genus, "f", "\\N", gen_vectors, topological, braid])
            else:    
                data.append([grp_print, genus,  "f", "\\N", gen_vectors, "\\N", "\\N"])
                
        # rows for g0 > 0 table on unique groups page
        if comp_info['g0_gt0_compute']:
            group_stats_gt0 = hgcwa.count({'genus':genus, 'g0':{'$gt':0}}, ['group'])
            for group, gen_vectors in group_stats_gt0.items():
                grp = group[0]
                grp_print = grp.replace('[','{').replace(']','}')
                labels = hgcwa.distinct('label', {'genus':genus, 'g0':{'$gt':0}, 'group': grp})
                g0_list = print_list(hgcwa.distinct('g0', {'genus':genus, 'g0':{'$gt':0}, 'group': grp}))
                if comp_info['top_braid_g0_gt0']:
                    topological = braids = 0
                    for label in labels:
                        topological += len(hgcwa.distinct('topological', {'label': label}))
                        braid += len(hgcwa.distinct('braid', {'label': label}))
                    data.append([grp_print, genus, "t", g0_list  , gen_vectors, topological, braid])
                else:
                    data.append([grp_print, genus, "t", g0_list  , gen_vectors,"\\N","\\N"])
    return data

