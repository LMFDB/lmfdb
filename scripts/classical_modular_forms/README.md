# On data updates:

## mf_newforms

### populate analytic ranks
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_analytic_ranks_in_mf_newforms.py 40 ::: {0..39}
```
### Generate statistics
```
from db_backend import db, SQL
db._execute(SQL("DELETE FROM mf_newforms_stats"))
db._execute(SQL("DELETE FROM mf_newforms_counts"))
db.mf_newforms.stats.add_stats(['has_inner_twist'])
db.mf_newforms.stats.add_stats(['analytic_rank'])
db.mf_newspaces.stats.add_stats(['num_forms'])
db.mf_newforms.stats.add_stats(['cm_disc'])
db.mf_newforms.stats.add_bucketed_counts([],{'dim':[1,1,2,3,4,5,10,20,100,1000,10000]})
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
