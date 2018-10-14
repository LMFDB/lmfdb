On data updates:

# mf_newforms

## populate analytic ranks
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_analytic_ranks_in_mf_newforms.py 40 ::: {0..39}
```


# mf_hecke_cc

## populate embeddings in complex data
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_embeddings_mf_hecke_cc.py 40 ::: {0..39}
```

# lfunc_lfunctions
## populate trace hashes in Lfunctions
```
parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_trace_hash_Lfunctions.py 40 ::: {0..39}
```


