---
id: T26
title: Draft the shimcurve.* knowls
status: review
owner: wave2-L-opus
priority: P3
tier: 4
repos: [lmfdb]
depends_on: []
questions: []
---

## Context

The templates/code reference ~50 knowls that must exist in the knowl database before release. Full list referenced by the module:

`shimcurve.{pqm, standard, level, index, genus, rank, genus_minus_rank, discb, disco, nrdmu, gonality, elliptic_points, decomposition, simple, is_coarse, models, known_points, local_obstruction, level_structure, modular_cover, relative_index, quadratic_refinements, quaternion_algebra, order, polarized_order, endomorphism_galois_group, torsion_subgroup, plane_model, embedded_model, model, invariants, cm_discriminants, isolated_point, point_degree, point_residue_field, j_invariant_map, elliptic_curve_of_point, fiber_product, rational_points, nonrational_point, label, search_input}` plus `portrait.shimcurve` and `rcs.{source,ack,cite,cande,rigor}.shimcurve`.

Knowls live in the knowl DB (edited via the website when logged in as an editor), not the repo — so this ticket produces **drafts as markdown files**, David uploads.

## Steps

1. Create `~/claude/lmfdb/shimcurve_tickets/artifacts/knowls/<knowl-id>.md`, one per knowl: title + body in knowl markdown (KaTeX math, `{{KNOWL(...)}}` cross-references). Model tone/length on the modular-curves analogues — fetch a few for calibration: `https://beta.lmfdb.org/knowledge/show/modcurve.level` etc. (if unreachable from this network, note it and work from the modcurve template usage instead).
2. Definitions must follow the enhanced-representation framework (LSSV arXiv:2308.15193 §3.5) and the QUESTIONS.md answers where they exist (gerbiness, coarse/fine, labels — leave `{{TODO}}` markers where a Q is unanswered rather than guessing).
3. The rcs.* knowls (source, reliability, completeness) should state exactly what the data is and how it was computed — pull the honest statements from BOARD.md's data-state section + Q12.4's answer.
4. `shimcurve.label` is the big one: full grammar of coarse/fine/order/mu/psl2 labels; write it as the normative spec (coordinate with T11).
5. Index file `artifacts/knowls/INDEX.md` mapping id → one-line summary → status (draft/needs-Q/final).

## Acceptance criteria

- Every referenced knowl id has a draft file; unanswered-question gaps are explicit TODO markers, not invented math; INDEX.md complete.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-L-opus): **DRAFTED all knowls → status: review.** Deliverable in
  `artifacts/knowls/` — 51 draft files (48 referenced ids + 3 supporting: `shimcurve.maximal`,
  `enhanced_group`, `aut_pm_mu_o`) + `INDEX.md`. Each file: `title/status/db/waits_on/note`
  metadata, then `---`, then the pasteable knowl body (KaTeX, `{{KNOWL}}` cross-refs). All 74
  distinct cross-referenced ids verified to resolve (DB or own drafts) — 0 dead links.
  - **Status counts: 32 final-candidate, 15 draft, 4 needs-Q.**
  - **needs-Q (id → open Q):** `shimcurve.quadratic_refinements` → **Q5** (fine-suffix labelling);
    `shimcurve.search_input` → **Q11** (name-grammar votes); `rcs.cande.shimcurve` → **Q12.4**
    (final completeness claim DEFERRED — interim honest coverage is stated, TODO for the final);
    `shimcurve.elliptic_curve_of_point` → **David** (a Shimura-curve point is an abelian *surface*;
    the "Elliptic curve" link on fine curves has no modcurve-style meaning — flagged, not invented).
  - **BIG FINDING — ~24 of the 48 ids already exist in the knowl DB** (authored by `yhuang`/David,
    Jan 2026; pulled verbatim from devmirror `kwl_knowls`, since beta WebFetch returns empty/JS).
    The definitional core is live and consistent with QUESTIONS_ANSWERS; those are reproduced as
    final-candidate. **Two live knowls need their body replaced:** `shimcurve.is_coarse` (DB text
    uses the stronger "H ⊇ proj(ker f)"; Q5.1 DECIDED `is_coarse ⟺ (1,−1) ∈ H`, matches frontend
    `contains_negative_one`), and `shimcurve.label` (DB grammar is right but omits the T29 tiebreak
    = AL-content then canonical generators, the maximal-vs-Eichler `order_label`, and the
    psl2/scalar side-labels; + Q3/Q11 TODOs). `rcs.cande`/`rcs.rigor` refreshed to the honest state.
  - **Label grammar pinned from live rows** (for the normative `shimcurve.label` spec): full label =
    `order_label.deg_mu.level.index.genus.class.num`; `order_label` = `discB` (maximal, 7 comps, e.g.
    `6.2.3.2.0.a.1`) or `discB.discO` (Eichler, 8 comps, e.g. `15.30.1.1.4.3.a.1`); `mu_label` =
    `order_label.deg_mu`; `coarse_label` (column) = `level.index.genus.class.num`; `psl2label` = the
    same-shaped label from the norm-1 image (drives pictures); `scalar_label` = `level.scalar_idx.1`
    (placeholder tail; Q6/T11).
  - **Calibration:** copied modcurve style straight from `kwl_knowls` — bold term first, heavy
    `{{KNOWL}}` cross-linking, `\cite{arxiv:...}`, the existing shimcurve macros (`\colonequals`,
    `\modstar{O}{NO}`); most knowls 2–6 sentences, `label`/`level_structure`/`decomposition`/
    `modular_cover`/rcs.* longer. `modular_cover`, `relative_index`, `models`/`model`/`plane_model`/
    `embedded_model`, `point_degree`/`point_residue_field`, `known_points`, `cm_discriminants`,
    `local_obstruction`, and rcs.* are direct adaptations of the modcurve analogues.

  **Cross-ticket findings (also flagged in INDEX.md):**
  - **T11:** `shimcurve.label.md` is written as the normative spec of the CURRENT (T29) grammar with
    TODO markers for Q3 (Pollack class index — will add a label component) and Q11 (names). `is_coarse`
    encodes Q5.1. `scalar_label` middle component is still a placeholder (Q6/T11) — I did not invent
    a format; observed live value e.g. `3.4.1` at N=3 does not obviously equal `[H:H∩G1] ≤ φ(3)=2`, so
    the exact semantics need T11's pull-from-modcurve-generation step before this can be finalized.
  - **Frontend/knowls (T24?):** `shimcurve.maximal` is referenced by the LIVE name knowls
    `shimcurve.xd1`/`xd1_star`/`xdn`/`xdn_star` but does **not exist** → dead links today. Fix: add
    the drafted `shimcurve.maximal.md` or repoint those links to `shimcurve.order` (defines "maximal").
  - **T25/T27:** the auto-generated column knowls exist under BOTH `columns.gps_shimura_test.*` (old)
    and `columns.gps_shimura.*` (target) — the T27 rename must reconcile which set is live (the
    `.gps_shimura.*` set is missing several columns the `.gps_shimura_test.*` set has, e.g.
    `is_coarse`, `label`, `psl2label`, `scalar_label`, `gerbiness`).
  - **David to confirm** the display meaning of `shimcurve.j_invariant_map` (target = X(D;1)?),
    `shimcurve.torsion_subgroup`, `shimcurve.endomorphism_galois_group` (drafted from LSSV §3.5), and
    to finalize the `rcs.source`/`rcs.ack`/`rcs.cite` contributor/acknowledgement/citation text (TODOs).
