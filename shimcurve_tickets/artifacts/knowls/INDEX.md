# T26 — shimcurve.* knowl drafts (INDEX)

Owner: wave2-L-opus. One draft file per referenced knowl id; each file is
`title:` / `status:` / `db:` / `waits_on:` / `note:` metadata, then `---`, then the
**pasteable knowl body** (KaTeX math, `{{KNOWL(...)}}` cross-references).

## How to use these

- Everything after the `---` in each file is the exact content to paste into the knowl DB
  (`kwl_knowls.content`); the `title:` line is the knowl title.
- `db:` records whether the id already exists in the knowl database and whether it is
  consistent: `yes (in DB, consistent)` = live and unchanged, reproduced here for reference;
  `yes (NEEDS UPDATE)` = live but the body below should replace it; `no (new)` = not yet in DB.
- `waits_on:` names the open question a `{{TODO}}` marker in the body is waiting on.

## Key finding — much of this is already seeded

**~24 of the 48 referenced ids already exist in the knowl DB** (authored by `yhuang`/David,
Jan 2026). The definitional core (algebra/order/polarization/level/index/genus/rank/…) is
already live and consistent with the QUESTIONS_ANSWERS decisions; those files reproduce the
current text verbatim as `final-candidate`. Only two live knowls need their body replaced:

- **shimcurve.is_coarse** — current DB text uses the stronger "H ⊇ proj(ker f)" condition;
  Q5.1 DECIDED the criterion `is_coarse ⟺ (1,−1) ∈ H` (matches the frontend
  `contains_negative_one`). Equivalent on all released data, not in general. Replace.
- **shimcurve.label** — current DB text (yhuang) has the right 7–8 component grammar but omits
  the T29 tiebreak (Atkin–Lehner content, then canonical generators), the explicit maximal-vs-
  Eichler `order_label`, and the psl2/scalar side-labels; and needs the Q3/Q11 TODO markers.

Plus **rcs.cande.shimcurve** / **rcs.rigor.shimcurve** refreshed to the honest current data state.

## Things to fix outside this ticket (flagged for David)

- **shimcurve.maximal is referenced but MISSING** — the live name knowls `shimcurve.xd1`,
  `xd1_star`, `xdn`, `xdn_star` link `{{KNOWL('shimcurve.maximal',…)}}`, which does not exist,
  so those links are dead. Either add `shimcurve.maximal.md` (drafted here) or repoint the links
  to `shimcurve.order` (which already defines "maximal").
- **shimcurve.elliptic_curve_of_point** — a point of a Shimura curve is an abelian *surface*;
  the "Elliptic curve" link (main.py:909, fine curves) has no modular-curve-style meaning.
  Needs David's decision before shipping (see file).
- **shimcurve.j_invariant_map**, **torsion_subgroup**, **endomorphism_galois_group** — drafted
  from the enhanced-representation framework, but the exact intended display meaning should be
  confirmed with David (notes in each file).

## Calibration (what was copied from the modcurve style)

Pulled the live modcurve + existing shimcurve knowl bodies straight from the devmirror
`kwl_knowls` table (beta.lmfdb WebFetch returned empty — JS-rendered). Conventions adopted:
bold defined term first; heavy `{{KNOWL(...)}}` cross-linking; `\cite{arxiv:...}` references;
custom macros already in use by the shimcurve knowls (`\colonequals`, `\modstar{O}{NO}` = (O/NO)^×,
`\Aut`, `\widehat`); most knowls 2–6 sentences, with `label` / `level_structure` / `decomposition`
/ `modular_cover` / rcs.* running longer. `modular_cover`, `relative_index`, `models`, `model`,
`plane_model`, `embedded_model`, `point_degree`, `point_residue_field`, `known_points`,
`cm_discriminants`, `local_obstruction`, `rcs.*` are direct adaptations of their modcurve analogues.

## Status counts

- **final-candidate: 30** — ready to ship (21 already-live reproductions + 9 new standard adaptations).
- **draft: 17** — written and encodes the decided definitions, but carries a TODO/flag or is new
  conceptual content wanting David's review (incl. the 2 live-knowl updates + 2 rcs refreshes).
- **needs-Q: 4** — core content blocked on an open decision.

## Index

Legend for status: **F** = final-candidate, **D** = draft, **Q** = needs-Q.

### needs-Q (blocked on an open decision)

| id | status | waits on | summary |
|----|--------|----------|---------|
| shimcurve.quadratic_refinements | Q | Q5 | Fine (index-2, no (1,−1)) refinements of a coarse curve; fine-suffix labelling undecided. |
| shimcurve.search_input | Q | Q11 | Jump-box grammar: labels, names X(D;N)/X(D,M;N)/X^*, fiber products; names broaden with Q11. |
| shimcurve.elliptic_curve_of_point | Q | David | The EC linked from a (fine-curve) point; correspondence for PQM surfaces not settled. |
| rcs.cande.shimcurve | Q | Q12.4 | Honest current coverage (2198 D=6 enhanced + 389 coarse); final completeness claim deferred. |

### draft (encodes decided defs; TODO/flag or wants review)

| id | status | db | summary |
|----|--------|----|---------|
| shimcurve.label | D | UPDATE | Normative label spec: order_label.deg_mu.level.index.genus.class.num; T29 tiebreak; Q3/Q11 TODOs. |
| shimcurve.is_coarse | D | UPDATE | Q5 criterion is_coarse ⟺ (1,−1) ∈ H; analogue of −I ∈ H; replaces stronger DB text. |
| shimcurve.pqm | D | new | Potential quaternionic multiplication; the moduli objects (LSSV). |
| shimcurve.level_structure | D | new | Enhanced level structure + enhanced Galois representation (LSSV §3.5); the long knowl. |
| shimcurve.cm_discriminants | D | new | CM points = surfaces whose QM order admits an imaginary quadratic order; CM discriminant. |
| shimcurve.j_invariant_map | D | new | Forgetful map to the level-1 base; analogue of the j-line map. (Confirm target.) |
| shimcurve.nonrational_point | D | new | Low-degree closed points = PQM surfaces over the residue field. |
| shimcurve.endomorphism_galois_group | D | new | Gal of the endomorphism field = image of ρ_A in Aut_{±μ}(O). (Confirm.) |
| shimcurve.torsion_subgroup | D | new | Rational torsion forced by H; LSSV 12-torsion, order ≤ 18. (Confirm.) |
| shimcurve.modular_cover | D | new | X_H → X_G from H ≤ G; degree = ratio of Fuchsian indices; minimal; kernel. (Most-referenced knowl.) |
| shimcurve.relative_index | D | new | Relative index [G:H]; degree = half when (1,−1) ∈ G∖H. |
| shimcurve.maximal | D | new | Maximal order stub (referenced-but-missing dependency of the name knowls). |
| portrait.shimcurve | D | new | Picture via the Fuchsian group of O on its fundamental domain; keyed by psl2label. |
| rcs.source.shimcurve | D | new | Provenance: ShimCurve Magma pkg + LSSV; algorithms. Contributor list = TODO. |
| rcs.ack.shimcurve | D | new | Acknowledgements placeholder (TODO: David). |
| rcs.cite.shimcurve | D | new | Citation placeholder pointing at LSSV (TODO: David). |
| rcs.rigor.shimcurve | D | UPDATE | Reliability: proven vs computed; partial columns; alpha label caveat. |

### final-candidate — already live (reproduced verbatim)

| id | status | summary |
|----|--------|---------|
| shimcurve.standard | F | Names the standard families X(D;1), X(D;N), X^*(D;1), X^*(D;N), X(D,M;1). |
| shimcurve.quaternion_algebra | F | Central simple algebra of dim 4; split/nonsplit; indefinite/definite. |
| shimcurve.order | F | Z-lattice subring of B; maximal orders; finitely many conjugacy classes. |
| shimcurve.polarized_order | F | (O,μ) with μ²∈Z_{<0} and trd(μx)∈Z for x∈O. |
| shimcurve.discb | F | disc(B) = product of ramified primes. |
| shimcurve.disco | F | disc(O) via Gram of reduced-trace form; reduced discriminant. |
| shimcurve.nrdmu | F | Polarization degree = squarefree part of nrd(μ)/discrd(O). |
| shimcurve.level | F | Least N with ker(Ô^× → (O/NO)^×) ⊆ H. |
| shimcurve.index | F | Index of H in the enhanced group. |
| shimcurve.genus | F | Genus of a geometric component of X_H. |
| shimcurve.rank | F | Analytic rank = Σ analytic ranks of the Jacobian's newform factors. |
| shimcurve.genus_minus_rank | F | genus − analytic rank; governs feasibility of rational-point methods. |
| shimcurve.gonality | F | K-gonality of a geometric component. |
| shimcurve.elliptic_points | F | Points with nontrivial stabilizer of order 2, 3, 4, or 6 (Q7 theorem). |
| shimcurve.decomposition | F | Isogeny decomposition of Jac(X_H) into modular abelian varieties (dims + newforms). |
| shimcurve.simple | F | X_H simple ⟺ Jac(X_H) is a simple abelian variety. |
| shimcurve.invariants | F | Order, level, index, genus, gonality. |
| shimcurve.local_obstruction | F | No real or no Q_p points; genus-0 converse. |
| shimcurve.rational_points | F | Genus-0/positive-rank genus-1 infinite; otherwise finite. |
| shimcurve.enhanced_group | F | (support) Aut_{±μ}(O) ⋉ Ô^× (LSSV §3.5). |
| shimcurve.aut_pm_mu_o | F | (support) {γ ∈ N_{B^×}(O)/Q^× : γ⁻¹μγ = ±μ}. |

### final-candidate — new (standard adaptations of modcurve analogues)

| id | status | summary |
|----|--------|---------|
| shimcurve.models | F | Count of stored models. |
| shimcurve.model | F | Model types: canonical / plane / embedded / Weierstrass; no cusps ⇒ from quaternionic forms. |
| shimcurve.plane_model | F | Possibly singular plane model in P². |
| shimcurve.embedded_model | F | Even-weight embedding for hyperelliptic / low-genus curves. |
| shimcurve.known_points | F | CM and non-CM stored points; counts are lower bounds; no cusps. |
| shimcurve.isolated_point | F | Isolated closed point (→ ag.isolated_point). |
| shimcurve.point_degree | F | [Q(x):Q]. |
| shimcurve.point_residue_field | F | K(x). |
| shimcurve.fiber_product | F | X_H = fiber product over X(D;1) when H = ∩ H_i; jump-box via *. |
