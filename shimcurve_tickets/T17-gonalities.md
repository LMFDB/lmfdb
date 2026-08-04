---
id: T17
title: Exact gonalities where determinable
status: open
owner: none
priority: P3
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q10]
---

## Context

All rows have `q_gonality_bounds`/`qbar_gonality_bounds` (heuristic, from `enumerate-H.m:529-540` — genus-aware but with the comment "These could be better — maybe (g+3)/2? Ask Oana and Freddy"); exact `q_gonality` is set on only ~121 rows, `qbar_gonality` on ~101.

Free wins independent of Q10:
- genus 0: gonality 1 over ℚ̄; over ℚ it is 1 if a rational point exists else 2 (conic) — needs T15's pointless data.
- genus 1: qbar_gonality 2; q_gonality 2 (elliptic after point) — check the convention modcurve used for genus 1 with/without a point.
- genus 2: gonality 2 (hyperelliptic).
- Trivial bounds tightening: qbar ≤ ⌈(g+3)/2⌉ for g ≥ 2 (Q10 confirms applicability), q_gonality ≤ 2·qbar? no — q ≤ some function; also gonality ≥ known lower bounds via Abramovich-style Fuchsian index bounds (λ₁ ≥ 3/16 ⇒ gon_ℚ̄ ≥ (21/200)·(index)/? — the Shimura-curve version; only add with a citation per Q10).

Q10 asks whether Padurariu–Saia gonality tables can be imported wholesale for X₀(D;N) and AL quotients.

## Steps

1. Apply the genus ≤ 2 rules corpus-wide (join with T15's point data for the ℚ-side of genus 0/1). Produce `artifacts/T17-gonality-update.txt` (labels + exact values + tightened bounds; never widen an existing bound, assert new ⊆ old interval).
2. Per Q10: import external tables if provided (map by (D, N, W) → label using T01's grammar knowledge).
3. Update the bound formulas in `enumerate-H.m:529-540` per Q10.2 so future generation emits the tighter bounds; regenerate bounds columns for shipped rows in the same update file.
4. Consistency: `q_gonality ≥ qbar_gonality`, both within their bounds arrays, `gonality=2 ⟺ hyperelliptic-or-genus≤1-cases` spot-checks.

## Acceptance criteria

- Every genus ≤ 2 row has exact gonalities; no bound widened; consistency checks pass corpus-wide.

## Log

- 2026-07-16: ticket created from survey.
