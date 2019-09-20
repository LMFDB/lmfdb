# On data updates:

## mf_newforms

### populate analytic ranks
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_analytic_ranks_in_mf_newforms.py 40 ::: {0..39}
```
### Generate statistics
```
from db_backend import db, SQL
db.mf_newforms.stats.refresh_stats()
db.mf_newspaces.stats.refresh_stats()
```

## mf_hecke_cc

### populate embeddings in complex data
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_embeddings_mf_hecke_cc.py 40 ::: {0..39}
```

## lfunc_lfunctions
### populate trace hashes in Lfunctions
This runs in parallel and takes about 15min
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_trace_hash_Lfunctions.py 40 ::: {0..39}
```


# Run consistency checks

## check that the data is there and is consistent
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/verify_data.py 40 ::: {0..39}
```
takes around 15 min
## check that all the pages load, display the appropriate things, and that parts of the data are consistent
This runs in parallel and takes about 1h
```
./test.sh lmfdb/classical_modular_forms/cmf_test_pages.py
```


# Indexes

## To make tests run smoothly:
```
for cols in [['is_self_twist'], ['level'], ['weight'], ['self_twist_type'],['analytic_conductor'],['label'],['space_label']]:
    try:
        db.mf_newforms.create_index(cols)
    except ValueError, err:
        print cols, err
        pass
for cols in [['embedding_m', 'hecke_orbit_code']]:
    try:
        db.mf_hecke_cc.create_index(cols)
    except ValueError, err:
        print cols, err
        pass
for cols in [['n', 'hecke_orbit_code'],['hecke_orbit_code']]:
    try:
        db.mf_hecke_nf.create_index(cols)
    except ValueError, err:
        print cols, err
        pass
for cols in [['label'], ['weight'], ['level'],['char_order', 'weight','level']]:
    try:
        db.mf_newspaces.create_index(cols)
    except ValueError, err:
        print cols, err
        pass
```
