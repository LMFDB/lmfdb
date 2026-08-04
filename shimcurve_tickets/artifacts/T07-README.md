# T07 gerbiness column update — PROVISIONAL, pending T27 reload

**Status: PROVISIONAL — DO NOT LOAD against the current `gps_shimura_test`.**

`T07-gerbiness-update.txt` is keyed by labels from the **canonical (T29) sort**.
The labels shipped in `gps_shimura_test` predate T29 and are not reproducible
(73% of rows change curve under the canonical sort — see T29 Log), so a
label-keyed `update_from_file` against the current table would attach values to
the wrong curves. This artifact is staged for the **T27 full reload**, where the
whole table is relabeled under the canonical order; alternatively it becomes
redundant if T27 reloads from the regenerated 69-column genera files directly
(which already carry both columns).

## Contents

`label ? gerbiness ? base_gerbiness` for 2,373 enhanced D=6 rows: the 2,198
corpus rows (deg μ ∈ {1,2,6}, N ∈ {1,2,3,4,6}) plus the 175 new N=5 deg-1
rows (T10 evidence file), regenerated on ShimCurve branch
`ticket/T07-fix-gerbiness`:

- `gerbiness` = #ker(f: Aut_{±μ}(O) → Aut(coarse)) — the moduli-stack gerbe
  (Q2, DECIDED), a level-independent invariant of (O, μ). Values:
  deg 1 → 1, deg 2 → 3, deg 6 → 2.
- `base_gerbiness` = #KG_level — the root-of-unity band reduced to the working
  level; this is exactly the value the `gerbiness` column stored before T07.
  Values: deg 1 → 2, deg 2 → 6, deg 6 → 4 at levels ≥ 3; at levels 1–2 the
  band partially collapses mod N: deg 1 → 1, deg 2 → 3, deg 6 → 2.
  Verified row-by-row equal to the old stored gerbiness on all 2,198 rows.
- `aut_gerbiness` is unchanged by T07 (not in this file).
- Value profile: (g,bg) = (1,1)×33, (1,2)×794, (3,3)×33, (3,6)×688,
  (2,2)×33, (2,4)×792.

Note the deg-2/deg-6 values reflect the μ representative chosen by the current
`HasPolarizedElementOfDegree` (deg-2 band ζ₆ → 6/3); the shipped DB rows for
deg 2 show a ζ₄-band μ (4/2) — a different polarization class (see Q3 /
T08). Gerbiness is a per-polarization-class invariant, one more reason this
update must ride the T27 reload rather than patch the current rows.

## Load commands (T27 time, after relabeling)

```python
from lmfdb import db
# base_gerbiness is a new column:
db.gps_shimura_test.add_column("base_gerbiness", "integer")   # or on the renamed gps_shimura
db.gps_shimura_test.update_from_file("T07-gerbiness-update.txt", label_col="label", sep="?")
```
