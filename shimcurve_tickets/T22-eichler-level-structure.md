---
id: T22
title: Eichler orders with level structure
status: open
owner: none
priority: P2
tier: 3
repos: [ShimCurve]
depends_on: [T08, T21]
questions: [Q12]
---

## Context

Today Eichler (non-maximal) orders appear only as coarse level-1 rows (the X₀(D;N) signature-table arm, where the Eichler level plays the role of the classical N). Running the **enhanced** pipeline on an Eichler order O of level M would give curves X(D,M;N) with genuine level-N structure — the `X(D,M;1)` display work already landed in the frontend anticipates this.

What already half-works: `createRecord` knows Eichler order labels (`enumerate-H.m:261-267`; errors only for non-Eichler), `quo(O,N)` and the GL₄ machinery are order-agnostic, `EnumerateOmu` produced 86 deg-1 polarized Eichler rows. What blocks it: `HasPolarizedElementOfDegree` flakiness on Eichler orders (T08), the normalizer/twisting TODO (`polarization-twisting.m:196` — resolved in T08 step 4), normalizer-plus generators for Eichler orders (T19's generalization must accept level > 1 — its AL part already ranges over m ∥ disc(O)·level; verify), and elliptic-point counting for Eichler bottoms (T20 — `SignatureX0DN` handles (D, M) so the oracle exists).

## Steps

1. Preflight on the smallest case O = Eichler order of level 5 in D=6 (label `6.30`): `HasPolarizedElementOfDegree(O,1)` (post-T08), `Aut(O,mu)`, `EnhancedImageGL4(AutFull,O,N)` for N=3 — chase errors; each distinct failure gets a Log entry with the fix applied.
2. Check the N-coprimality question: the enhanced level N presumably must be coprime to disc(O) = D·M (the current maximal-order code asserts gcd conditions — find them and confirm what the right condition is for Eichler; note `jacobian_decomp/level_dividing_D.m` exists precisely for non-coprime classical cases, so document what's out of scope).
3. Run a pilot batch per Q12 scope (suggest: D=6, M ∈ {5,7,11,13}, deg 1, N ∈ {1,2,3,4}); sanity via `SignatureX0DN(6, M·N)`-style cross-checks where the coarse curves coincide, and via the existing 86 polarized-Eichler rows.
4. Label audit: Eichler rows produce 8-component labels (`main.py:58` optional group); confirm frontend pages render (the `X(D,M;1)` display fixes from recent lmfdb commits were for exactly these).
5. Stage files + commands; record timings.

## Acceptance criteria

- Pilot batch generates clean, cross-checked files; every earlier error has a root-caused fix (no try/catch swallowing).
- Frontend renders an Eichler level-structure curve page locally.

## Log

- 2026-07-16: ticket created from survey.
