---
id: T12
title: Populate subgroup-lattice columns (parents, parents_conj, lattice_labels, lattice_x)
status: open
owner: none
priority: P1
tier: 2
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: []
questions: []
---

## Context

The frontend has a complete lattice-diagram feature waiting on data: `lat_diagram` route (`~/claude/lmfdb/lmfdb/shimura_curves/main.py:152-205`), `nearby_lattice` (`web_curve.py:974-1025`, reads `lattice_labels`, `lattice_x`, parses labels as level.index.genus via `get_lig`), "modular covers / covered by" sections (read `parents`; `covered_by` search at `main.py:628-642`). Today: `parents` = hardcoded `{}` (`enumerate-H.m:593`, so it *displays* as empty rather than missing), `parents_conj`/`lattice_labels`/`lattice_x` = `\N`.

Semantics should mirror modular curves (`gps_gl2zhat_fine`): `parents` = labels of curves minimally covered by this one (H maximal-among-proper-overgroups, up to conjugacy in G — note covers go H ⊂ H′ ⟹ X_H → X_{H′}), `parents_conj` = conjugating data aligning generators, `lattice_labels`/`lattice_x` = the precomputed local picture (nearby lattice nodes and x-coordinates) used to draw the diagram. Check modcurve's meaning of each on a sample: `select label,parents,lattice_labels,lattice_x from gps_gl2zhat_fine where label='8.12.1.a.1';` and read `~/claude/lmfdb/lmfdb/modular_curves/web_curve.py` around its `nearby_lattice` for exact expectations.

**Prior art**: David's open PR assaferan/ShimCurve#3 ("Refactoring and attempts to use subgroup lattices", +3219/−868, adds a `FiniteGroups` submodule) is an earlier run at exactly this. Inspect before writing anything: `gh pr view 3 -R assaferan/ShimCurve`, `gh pr diff 3 -R assaferan/ShimCurve`. It has drifted from main (main has since gained the gerbiest enumeration and Eichler work) — treat it as a quarry for design/code, not something to merge blindly.

## Steps

1. Study PR #3's approach (which pieces of the modular-curves subgroup-lattice machinery it ports; what "attempts" failed) and modcurve's data semantics. Write a short design note in the Log: compute the full poset per (O, μ, N) at enumeration time (all H are already in memory in `GenerateDataForGerbiestSurjectiveH` — the subgroup list comes from `Subgroups(G, KG)`) vs. postprocess.
2. Recommended shape: at the end of `GenerateDataForGerbiestSurjectiveH`, compute inclusion-up-to-conjugacy among the enumerated H (Magma: for each pair with index dividing, `IsConjugateSubgroup`/transversal search — the sets are small, ≤ 475 per (D,deg,N)); derive minimal overgroups → `parents` (labels), and the conjugator → `parents_conj` (in the modcurve encoding — check what the frontend actually consumes; `parents_conj` is unread by the shimura frontend today, so match modcurve's format).
3. `lattice_labels`/`lattice_x`: port modcurve's layout computation (in lmfdb repo, `lmfdb/modular_curves/` — find where lattice_x is produced; if it's produced offline in the modular-curves data repo, reimplement the simple version: nodes = H's neighborhood in the poset restricted as modcurve does, x = ordering within rank rows).
4. Wire into `createRecord`/`WriteSubgroupsDataToFile` (remove the hardcoded `{}` and `\N`s), regenerate the D=6 corpus, stage `update_from_file` files.
5. Verify end-to-end: load into a local/dev table David provides (or hand him load commands), then check `/ShimuraCurve/Q/6.1.6.24.1.a.1/` (any mid-lattice curve) renders the diagram and the covers list; screenshot in the Log. Until a load happens, unit-verify by asserting poset consistency: every parent's index properly divides, genus weakly decreases under covering, X(D;1)-analogue is the unique maximal element per component.
6. Reconcile with PR #3: note in the Log what was reused vs. superseded so David can close/rework the PR.

## Acceptance criteria

- Regenerated D=6 files have non-trivial `parents` for every non-top H and lattice columns populated; poset sanity assertions pass over the whole corpus.
- Frontend diagram renders (or, pre-load, the JSON the diagram route builds from a synthetic row is well-formed).
- Design note + PR #3 reconciliation in the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (orchestrator): claimed by an agent that was stopped (credit limit) during the reading/design phase before producing any code. Branch `ticket/T12-subgroup-lattice` exists but its tip == the T11 tip `3d30898` (zero T12 commits); worktree was clean. **Reset to open — start fresh.** The correct base is still the tier1core chain tip (currently T11 @ 3d30898; will be the T17 tip once T17 lands, or T06 once the capstone starts — take the latest tier1core-chain branch that includes T11). Nothing to salvage.

- 2026-08-01 (opus session): **new consumer — [D26](DECISIONS.md).** David added the
  `factorization text[]` column to the canonical schema (fiber-product decomposition, semantics
  copied from `gps_gl2zhat_fine.factorization`). Both writers currently emit `\N` because
  deciding which curves are fiber products **needs the subgroup lattice this ticket builds**.
  So T12 now has a second deliverable beyond `parents`/`parents_conj`/`lattice_labels`/
  `lattice_x`: compute `factorization`, and hand T27 the values to populate.
  The frontend already consumes it (jump-box fiber products in `main.py`, `fiber_product_of`
  in `web_curve.py`) and will light up as soon as the column is populated.
