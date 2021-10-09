files = [
"lint",
"lmfdb/abvar/fq/test_av.py lmfdb/abvar/fq/test_browse_page.py lmfdb/number_fields/test_numberfield.py lmfdb/bianchi_modular_forms/test_bmf.py",
"lmfdb/galois_groups/test_galoisgroup.py lmfdb/siegel_modular_forms/test_siegel_modular_forms.py",
"lmfdb/tests/test_dynamic_knowls.py lmfdb/tests/test_root.py lmfdb/hecke_algebras/test_hecke_algebras.py lmfdb/tests/test_homepage.py lmfdb/elliptic_curves/test_ell_curves.py lmfdb/elliptic_curves/test_browse_page.py",
"lmfdb/sato_tate_groups/test_st.py lmfdb/hilbert_modular_forms/test_hmf.py lmfdb/tests/test_spelling.py lmfdb/tests/test_template_namespace.py lmfdb/tests/test_acknowlegments.py lmfdb/tests/test_tensor_products.py",
"lmfdb/cluster_pictures/test_clusterpicture.py lmfdb/local_fields/test_localfields.py lmfdb/ecnf/test_ecnf.py lmfdb/ecnf/test_isog_class.py lmfdb/api/test_api.py lmfdb/characters/test_characters.py",
"lmfdb/users/test_users.py lmfdb/lattice/test_lattice.py lmfdb/maass_forms/test_maass.py lmfdb/higher_genus_w_automorphisms/test_hgcwa.py lmfdb/belyi/test_belyi.py lmfdb/tests/test_utils.py",
"lmfdb/artin_representations/test_artin_representation.py lmfdb/genus2_curves/test_genus2_curves.py",
"lmfdb/classical_modular_forms/test_cmf.py lmfdb/classical_modular_forms/test_cmf2.py",
    "lmfdb/lfunctions/test_lfunctions.py",
    "lmfdb/groups/abstract/test_browse_page.py lmfdb/groups/abstract/test_abstract_groups.py",
]

server = ["proddb", "devmirror"]

import os
workflows_dir = os.path.dirname(os.path.abspath(__file__))
assert workflows_dir.endswith('workflows')
r = []
strip = lambda elt: elt if not elt.startswith('lmfdb') else '/'.join(elt.split('/')[1:-1])
from itertools import product
for f, s in product(files, server):
    r.append({'files': f,
              'server': s,
              'folders': ' '.join(sorted(set(map(strip, f.split())))),
              })
import json
with open(os.path.join(workflows_dir, 'matrix_includes.json'), 'w') as W:
    W.write(json.dumps(r, indent=4) + '\n')


