from lmfdb import db
import math

# sage -python
# from lmfdb import db
# from scripts.higher_genus_w_automorphisms.hgcwa_complete_table import create_file
# create_file()

def create_file():
    f = open('scripts/higher_genus_w_automorphisms/hgcwa_complete.txt', 'x')
    col_names = 'genus|g0_gt0_compute|top_braid_compute|top_braid_g0_gt0|num_families|num_refined_pp|num_gen_vectors|num_unique_groups\n'
    col_types = 'smallint|boolean|boolean|boolean|integer[]|integer[]|integer[]|integer\n'
    f.write(col_names)
    f.write(col_types)
    f.write('\n')
    data = compute_values()
    for datum in data:
        line = '|'.join([str(val) for val in datum])
        f.write(line + '\n')
    f.close()

def compute_values():

    data = []
    hgcwa = db.hgcwa_passports
    
    for genus in range(2, hgcwa.max('genus')+1):

        # hgcwa_complete has exactly one row for each genus
        table_entry = db.hgcwa_complete.lookup(genus)

        row = [genus]

        if table_entry is not None: 
            # retrieve some of the previous values
            row.extend([table_entry['g0_gt0_compute'], table_entry['top_braid_compute'], table_entry['top_braid_g0_gt0']])
        else: # a new genus is being added
            # can be manually updated
            row.extend([False, False, False])

        # Compute data for the columns num_families, num_refined_pp, num_gen_vectors, num_unique_groups
        # first entry is total number of distinct families, passports, or gen_vectors for genus
        num_families = [len(hgcwa.distinct('label', {'genus':genus}))]
        num_refined_pp = [len(hgcwa.distinct('passport_label', {'genus':genus}))]
        num_gen_vectors = [hgcwa.count({'genus':genus})]

        num_unique_groups = len(hgcwa.distinct('group', {'genus':genus}))

        # second entry is number of distinct families, passports, or gen_vectors for quotient genus 0
        num_families.append(len(hgcwa.distinct('label', {'genus': genus, 'g0': 0})))
        num_refined_pp.append(len(hgcwa.distinct('passport_label', {'genus': genus, 'g0': 0})))
        num_gen_vectors.append(hgcwa.count({'genus': genus, 'g0': 0}))

        if table_entry['g0_gt0_compute']:
            for g0 in range(1, hgcwa.max('g0')+1):
                if g0 <= int(math.ceil(genus / 2)):
                    # append counts for increasing quotient genus
                    num_families.append(len(hgcwa.distinct('label', {'genus': genus, 'g0': g0})))
                    num_refined_pp.append(len(hgcwa.distinct('passport_label', {'genus': genus, 'g0': g0})))
                    num_gen_vectors.append(hgcwa.count({'genus': genus, 'g0': g0}))

        row.extend([num_families, num_refined_pp, num_gen_vectors, num_unique_groups])
        data.append(row)
    
    return data
