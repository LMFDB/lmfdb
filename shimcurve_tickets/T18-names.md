---
id: T18
title: Populate the `name` column systematically
status: open
owner: none
priority: P3
tier: 2
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: []
questions: [Q11]
---

## Context

391/2,587 rows have a `name`. Names drive the jump box (`shimcurve_lmfdb_label` resolves via `db.gps_shimura_test.lucky({"name": ...})`, `main.py:231-241`), `NAME_RE = X\*?\(\d+(,\d+)?(;|,)\d+\)` (`main.py:62`), `canonicalize_name` (`web_curve.py:98-112`, normalizes `X*`→`X^*` and comma/semicolon forms), and display. Recent lmfdb commits mention `X(D,M;1)` forms for Eichler orders.

Blocked on Q11 (the full grammar). Once answered:

## Steps

1. Encode the grammar as a Magma function `CurveName(record) -> MonStgElt or ""` next to `updateLabels` in `enumerate-H.m`, assigning names to exactly the families Q11 specifies (top curves, X₀-type, X-full-level-type, AL-star quotients, Eichler `X(D,M;N)`, fiber-product names excluded presumably).
2. Cross-check the 391 existing names: recompute them; any mismatch is either a bug in the new function or an inconsistency in the shipped data — list mismatches in the Log, don't silently overwrite.
3. Check `NAME_RE` and `canonicalize_name` accept every generated name (run the actual Python regex over the full generated list); extend the regex in a small lmfdb-side commit if the grammar outgrew it (e.g. `X*` with two arguments, `X_0`?).
4. Stage `artifacts/T18-names-update.txt` + load commands; verify the jump box resolves 3 sample names locally.

## Acceptance criteria

- Deterministic name generation; existing-name cross-check documented; regex round-trip passes for all names.

## Log

- 2026-07-16: ticket created from survey.
