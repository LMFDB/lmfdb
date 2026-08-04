# T11 is_coarse / scalar_label update — PROVISIONAL, pending T27 reload

**Status: PROVISIONAL — DO NOT LOAD against the current `gps_shimura_test`.**

Both files are keyed by labels from the **canonical (T29) sort**. The labels
shipped in `gps_shimura_test` predate T29 and are not reproducible (73% of
rows change curve under the canonical sort — see T29 Log), so a label-keyed
`update_from_file` against the current table would key values to the wrong
rows. Staged for the **T27 full reload**; the update becomes redundant if T27
reloads from corpus files regenerated after T11 merges (the regenerated files
carry both columns natively).

**Special property of this particular update:** the payload is constant on
every row (`is_coarse = T`, `scalar_label = 1.1.1`), so the update is
label-permutation-invariant — it would be value-correct under *any* bijective
relabeling. It is staged PROVISIONAL anyway per board protocol.

## Contents

`T11-labels-update.txt` — `label | is_coarse | scalar_label` (3-line
postgres-copy header, `|`-separated, T04 canonical separator) for all 2,373
enhanced D=6 rows: the 2,198 shipped-corpus rows (deg μ ∈ {1,2,6},
N ∈ {1,2,3,4,6}) plus the 175 N=5 deg-1 rows (T10 evidence file). Freshly
computed on ShimCurve branch `ticket/T11-fine-coarse-labels` (no `data/`
files were regenerated).

`T11-labels-invariants.txt` — the same rows with invariant join keys for
post-relabel reconciliation:
`label | deg_mu | level | index | genus | coarse_class | coarse_num | autmuO_norms | is_coarse | scalar_label`.
Load the 3-column file with `update_from_file`; use this one only to re-join
rows across a relabeling.

- `is_coarse` = T on all 2,373 rows, now **computed** (`ContainsMinusOne`:
  (1,−1) ∈ H per Q5.1) instead of hardcoded. Empirically confirms Q5.2:
  every gerbiest H contains (1,−1) ((1,−1) ∈ KG held at every (deg,N)), so
  no shipped value changes.
- `scalar_label` = `1.1.1` on all 2,373 rows: the RSZB GL1-subgroup label
  `N.i.n` (arXiv:2106.11141 §2.2; `GL1Label` in `groups/gl2.m` of
  github.com/AndrewVSutherland/ell-adic-galois-images) of the reduced-norm
  image nrd(H) ≤ (ℤ/N)ˣ, per the Q6 decision (follow the modular-curve
  generation convention exactly). Every enumerated H has surjective reduced
  norm, so nrd(H) is the full group, whose GL1 label is `1.1.1`. This
  CHANGES every enhanced row (shipped values `3.4.1`, `6.12.1`, … were
  `{level}.{[H : H ∩ P]}.1` for an unstable pre-T29 subgroup pick P —
  non-canonical; see T11 Log). The 389 coarse X₀(D;N) rows keep
  `scalar_label = NULL` and are not in this file.
- `fine_label`/`fine_num` are NOT in this update: they are unchanged
  (`fine_label = coarse_label`, `fine_num = NULL` on every current row).

## Load commands (T27 time, after the canonical-label reload)

```python
from lmfdb import db
db.gps_shimura.update_from_file("T11-labels-update.txt", label_col="label", sep="|")
```

(`sep="|"` matches psycodict's default; the header carries column names and
types.)
