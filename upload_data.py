from lmfdb import db
import yaml
import sys


'''
Update the braid and topological field of each generating vectors
with the cc of the equivalence class representative
'''


if len(sys.argv) == 1:
    sys.exit('Please give one or more output file names as command-line arguments')

hgcwa = db.hgcwa_passports

for file_name in sys.argv[1:]:
    output_file = open(file_name, 'r')
    gen_vectors = yaml.load(output_file.read())
    for genvec_id in gen_vectors:
        genvec = gen_vectors[genvec_id]
        braid_id = genvec['braid']
        top_id = genvec['topological']

        # Get the cc of the representatives
        braid_cc = list(hgcwa.search({'id': braid_id}))[0]['cc']
        top_cc = list(hgcwa.search({'id': top_id}))[0]['cc']

        # Update the database one generating vector at a time
        hgcwa.upsert({'id': genvec_id}, {'braid': braid_cc, 'topological': top_cc})