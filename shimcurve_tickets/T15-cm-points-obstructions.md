---
id: T15
title: CM points, obstructions, and point counts for coarse rows
status: review
owner: wave2-I-fable
priority: P1
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q9]
---

## Context

Null columns with existing, polished machinery in `code/X0DN/X0DN_code.m` (Arango-Pineros–Padurariu–Saia; Ogg/González–Rotger-based):

- `cm_discriminants` (frontend: `web_curve.py:401-402,913`) — from `CMPointsX0DN` / `QuadraticCMPointsX0DN`.
- `obstructions`, `has_obstruction`, `pointless` — real place: Shimura's theorem (X₀(D;N)(ℝ) = ∅ for D > 1) applies to every curve admitting a map to the coarse X₀(D;N) — per Q9.3, decide the exact H-criterion for when that argument applies to X_H (Aut-projection trivial ⟹ X_H covers X₀(D;N)-mod-nothing); p-adic: Ogg/Jordan–Livné criteria at p | D per Q9.2.
- `num_known_degree1_points`, `num_known_degree1_noncm_points` — rational CM points on AL quotients from `RationalCMPointsX0DN` / `RationalCMQuotientsX0DN` give known-point lower bounds; `pointless=true` rows get 0s.
- `all_degree1_points_known` — currently hardcoded `F` for all; genuinely-true cases (pointless curves! and genus-0 curves with a point) should flip to `T` per Q9.

Scope note: start with the 389 coarse X₀(D;N)-type rows plus the D=6 level-1 quotient rows where the AL-quotient interpretation is exact; the general-X_H story (level > 1) needs the Q9.3 criterion and possibly more theory — split it out if it balloons.

## Steps

1. Read Q9. Confirm conventions against modular curves (`obstructions`: 0 = real place; `has_obstruction` smallint semantics — check modcurve: 1 = yes, 0 = none known, −1 = ?; copy exactly: `select distinct has_obstruction from gps_gl2zhat_fine;` + grep its frontend for display logic).
2. Implement `intrinsic X0DNPointsData(D, N, W) -> rec` wrapping the X0DN_code intrinsics: CM points by discriminant, rational points/quotient results, real-point status (for the quotient X₀(D;N)/W, real points can exist — use the criteria from the literature per Q9.2; Ogg's real-points criterion for AL quotients is classical), local obstructions at p | D·N.
3. Map results onto rows: coarse rows (trivial W) and the 5 D=6 level-1 rows (W from `autmuO_norms`). Emit `artifacts/T15-points-update.txt` (label-keyed update file: `cm_discriminants|obstructions|has_obstruction|pointless|num_known_degree1_points|num_known_degree1_noncm_points|all_degree1_points_known`).
4. Consistency guards: `pointless=T ⟹ num_known_degree1_points=0 and has_obstruction=1`; genus 0 + known point ⟹ infinitely many (follow modcurve's encoding for that, cf. T03); a curve with a rational CM point must have `pointless=F` and the CM disc in `cm_discriminants`.
5. Cross-validate against T03's data where they overlap (a curve with uploaded rational points must not be marked pointless — run the join and log it).
6. Stage load commands in the Log.

## Acceptance criteria

- Update file covers all targeted rows; guards pass; overlap check vs T03 clean.
- Convention table (ours vs modcurve) documented in the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-I-fable): **DONE → review (v1 scope per Q9 DECIDED: real place + CM lower bounds; NO p-adic).** Branch `ticket/T15-cm-obstructions` (stacked on T04), commit `975b2df`. Artifact: `artifacts/T15-points-update.txt` — **394 rows** (389 coarse + 5 D=6 deg-1 level-1), PROVISIONAL, invariant join keys alongside labels. `run_quick` green (0/0).

  **Convention table (ours vs modcurve `gps_gl2zhat_fine`, pinned from value sets + frontend + T03; devmirror `meta_tables.col_description` is empty except `label`, so no official prose exists — noted gap):**
  | column | modcurve observed | T15 v1 |
  |---|---|---|
  | `obstructions` int[] | `\N` = not computed; `{}` = none found/exist; sorted asc, `0` = real place, `p` = X(ℚ_p)=∅ (e.g. `{0}`, `{0,3,19}`) | `{0}` on Shimura/Ogg-pointless rows; `{}` where a rational point exists (provably no obstruction); `\N` where real points exist but no rational point is known (p-adics unexamined in v1 — never claim `{}` there) |
  | `has_obstruction` smallint | `1` ⟺ `pointless=t` (exact on 17.1M rows); `0` = provably none (pointless `f` **or** `\N`); `-1` = undetermined (`f` or `\N`) | same: 1 / 0 / −1 |
  | `pointless` bool | `t` ⟺ has_obstruction=1; `f` = point exists; `\N` unknown | `t` / `f` / `\N` (same) |
  | `num_known_degree1_points`, `_noncm_` | count of known points; **`\N` on genus-0-with-point** (infinitely many, not enumerated — T03-verified); `0` + pointless `\N` = searched-found-nothing | `0`/`0` on pointless rows; `\N`/`\N` on the genus-0 quotients with points |
  | `cm_discriminants` int[] | fundamental discs of rational CM points; `{}` = none **known** (universal default) | `{}` on pointless; GR06 discs sorted ascending on quotients |
  | `all_degree1_points_known` bool | **never `t`** (0 of 17.1M rows) | `t` on pointless rows (trivially all known) per the ticket/Q9 direction — **deliberate divergence from observed modcurve practice, flag for Eran**; `f` otherwise |

  **Row outcomes:** 390 rows pointless (`{0}`,1,t,cm `{}`,0/0,allk t): all 389 coarse X₀(D;N) (Shimura, D>1; the map is the identity — coarse rows have trivial Aut-projection per Q9.3) + the enhanced `X(6;1)` row `6.1.1.4.0.a.1` (autmuO_norms all 1 ⟹ trivial Aut-projection). 4 rows with rational points (`{}`,0,f, counts `\N` genus-0-infinite, allk f) — **the AL-exception cases, none real-obstructed**: `6.1.1.2.0.a.1` = X₀(6)/w₃ cm `{-24,-4}` (≥3 pts), `.b.1` = /w₆ cm `{-163,-67,-43,-24,-19,-4,-3}` (≥21), `.c.1` = /w₂ cm `{-24,-3}` (≥3), `6.1.1.1.0.a.1` = X\*(6;1) cm = the 7-disc union (≥7, conservative one-per-disc under the further quotient). 0 rows left `\N` (the real-but-no-known-point case did not arise in this scope).

  **Implementation** (`code/X0DN/points_obstructions.m`, in spec; tests `tests/regression_points_obstructions.m` in run_quick):
  - `OggQuotientHasRealPoints(D,N,m)`: Ogg's ν(m)>0 criterion [Ogg83 Prop 1 + Thm 3; local embedding numbers Thm 2], following the Padurariu–Saia summary (arXiv:2401.08829 Thm 2.6/3.1). Since h(R) ≥ 1, positivity needs no class numbers: ν(m)>0 ⟺ some R ∈ {ℤ[√m] (disc 4m), and ℤ[(1+√m)/2] (disc m) if m≡1 (4)} has ν_p ≠ 0 ∀ p | DN/m, with ν_p = 1−(R/p) at p|D, 1+(R/p) at p‖N (Eichler symbol; squarefree-N scope enforced by `require`). m=1 → false (Shimura). Hand-verified: D=6 quotients w₂/w₃/w₆ all real; **X₀(14)/w₂ is genuinely real-obstructed (ν(2)=0 via ν₇=1−(8/7)=0)** — regression-tested as the machinery-bites case.
  - `X0DNPointsData(D,N,W)` for any AL subgroup W (norm-set, auto-closed by `HallClosure`): real points of X/W ⟺ ν(m)>0 for some 1≠m ∈ W (a real point of X/W is a w∘σ-fixed point for some w ∈ W, and maps to/from real points of X/⟨w⟩ — so the cyclic criterion covers X\* too). CM via `RationalCMPointsX0DN` (GR06 Cor 5.14; lower bounds, "may not be exhaustive" per its docstring).
  - **Finding (canary-tested): the raw GR06 `m=1` entry is NONEMPTY for D=6** (`[[-24,1]]`) — a field-of-moduli artifact: CM points on X₀(D;N) itself have residue field a ring class field or index-2 subfield, totally complex for D>1 [Shi67], so none is rational (Shimura). `X0DNPointsData` ignores all m=1 entries; the regression test asserts both the raw nonemptiness and that nothing leaks. **Anyone consuming `RationalCMPointsX0DN` raw must do the same.**
  - `SignatureX0DNmodAtkinLehnerElement` (suspected `s3 = e3` bug, per coordinator): **not used anywhere in T15** — the real-points path is Ogg Thm 2/3 directly and CM is GR06; no cross-check needed here, suspicion stays open for whoever consumes that intrinsic.

  **Consistency guards (ticket step 4) — all pass** (`code/scripts/t15_stage_points_update.py`, exits nonzero on failure): pointless ⟹ counts 0 ∧ has_obstruction=1 ∧ cm `{}` ∧ 0 ∈ obstructions ∧ allk t; CM point ⟹ pointless=f ∧ discs negative, sorted, ⊆ cm_discriminants; genus-0-with-point ⟹ counts `\N` (infinite convention); no duplicate labels.

  **T03 cross-validation (ticket step 5) — clean:** staged file joined by label: **42/42 matched, count agreement 42/42, 0 conflicts** (their coarse bases all `num=0, pointless=\N` — T15 upgrades `\N`→`t` with the Shimura proof, exactly the split T03's Log deferred to Q9/T15). Parked file joined on invariant key (discB, discO, deg_mu, congruence level, W-set): **0 overlaps** — T03's source has no D=6-maximal level-1 rows (its D=6 rows are Eichler discO=102/114/…), so no point-bearing T03 curve meets my scope; nothing could be contradicted. T03's point-bearing quotients are all PENDING_GENERATION (T19→T20 chain) — when those rows exist, `X0DNPointsData(D, N, W)` applies to them as-is at level 1.

  **Flags for David/Eran:**
  1. **`all_degree1_points_known = t` on pointless rows** diverges from modcurve-as-shipped (never `t` there). Ticket-directed; Eran should confirm before T27.
  2. **`level`-column discrepancy (T06/T27):** all 389 shipped coarse rows carry `level=1` (congruence level; Eichler level M in discO — labels e.g. `6.138.1.1.4.5.a.1` = X(6,23;1)), but current `tablesX0DN.m` writes `level := N` (and level_radical/_is_prime/… from N). A regeneration under current code would flip these 389 rows' level-family columns. My artifact carries both (`join_level_congruence=1`, `join_eichler_level=M`); decide the convention before the T27 reload.
  3. **Label reshuffle on the 5 enhanced rows:** shipped DB has a/b class letters swapped vs the canonical (T29) sort (`…2.0.a.1` is w₆ in the DB but w₃ canonically). Artifact uses canonical labels; **re-key by `join_W` (the Hall-divisor set), not by shipped label**.
  4. `cm_discriminants` sorted ascending (−163 … −3); modcurve samples don't pin an order (frontend only uses the length). Trivial to flip if a convention exists.
  5. The GR06 m=1 artifact (finding above) — worth an upstream comment on `RationalCMPointsX0DN`.
  6. Q9's remaining ⟐: none decided unilaterally here; v1 exclusions (Ogg85/Jordan–Livné p-adic criteria at p | D — Thm 3.2 of PS24 is the recipe) are the natural v2 and would populate the 4 quotient rows' `obstructions` beyond `{0}`… actually would refine coarse rows' arrays from `{0}` to `{0,p,…}`.
  7. Scope did NOT balloon: general X_H (level > 1) untouched per the ticket. The reusable pieces for that future ticket: Q9.3's Aut-projection test = "distinct autmuO_norms ⊆ {1}" and `X0DNPointsData(D, N, HallClosure(norms))` — valid verbatim for any level-1 X_H the T19/T20 chain generates; level>1 needs the H-level real-structure analysis (new theory).

  **Load commands (DAVID; post-T27 re-key, AFTER T03's count file — T15 supersedes its `pointless=\N` on the coarse bases):**
  ```python
  # sage -python, editor credentials; from lmfdb import db
  # strip comment lines and the join_* columns (keep header line 1 = cols 1-8):
  #   grep -v '^#' shimcurve_tickets/artifacts/T15-points-update.txt | cut -d'|' -f1-8 > /tmp/t15_load.txt
  db.gps_shimura_test.update_from_file('/tmp/t15_load.txt', label_col='label', sep='|')
  ```
