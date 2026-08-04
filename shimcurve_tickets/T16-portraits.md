---
id: T16
title: Portraits (fundamental-domain pictures) beyond level 1
status: open
owner: none
priority: P2
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: []
---

## Context

`shimcurve_pictures` (devmirror) has 304 rows — exactly the level-1 curves for D ≤ 1000 — keyed by `psl2label` with a base64 PNG in `image` (`web_curve.py:315` does `db.shimcurve_pictures.lookup(self.psl2label, "image")`). The 2,198 D=6 level-structure rows have `psl2label`s pointing at PSL₂-quotient curves that mostly have **no picture**.

Toolchain (all present):
1. `~/claude/ShimCurve/code/../pictures/picture-to-gp.m` — Magma `PrepPictureDataH(O, H)` emits `algdat.dat` (vertices etc.) for a subgroup H.
2. `pictures/makedata.gp` — PARI/GP processing of `algdat.dat`.
3. `pictures/make-fdom-pictures.sage` — Sage renders the PNG (adapted from David Lowry-Duda's LMFDB picture code).
4. Output format: `data/level1_pictures.fdom` — `?`-separated, header `psl2label ? image`, rows `label?data:image/png;base64,...`.

## Steps

1. Reconstruct the exact run recipe for the level-1 batch (read the three scripts; the .sage one documents its expected inputs) and write it down as `pictures/README.md` — this is currently tribal knowledge.
2. Determine the distinct `psl2label`s needed: `select distinct psl2label from gps_shimura_test where psl2label not in (select psl2label from shimcurve_pictures);` (devmirror) — expect ≲ a few hundred distinct PSL₂ curves for D=6.
3. Drive `PrepPictureDataH` per missing psl2label: the H here is the PSL₂-scalar version (the `psl2label` rows are themselves curves in the table — their `generators` column reconstructs H; use the T05 reader). Batch through gp + sage; render at the same size/style as the level-1 batch for visual consistency.
4. Spot-check 5 images visually (open the PNGs) — fundamental domains should tile plausibly and differ between curves.
5. Emit `artifacts/T16-pictures.fdom` in the same format; load commands (copy_from into `shimcurve_pictures`) in the Log.
6. Frontend verify (post-load): a level-structure curve page shows its portrait (the `portrait` block on `shimcurve.html`).

## Acceptance criteria

- `pictures/README.md` makes the pipeline reproducible end-to-end.
- Every distinct missing psl2label either has an image in the staged file or is listed with a failure reason (timeouts at large index are acceptable, logged).

## Log

- 2026-07-16: ticket created from survey.
