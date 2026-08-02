---
id: T07
title: Fix gerbiness computations (upstream issue #6)
status: review
owner: wave1-A-fable
priority: P0
tier: 1
repos: [ShimCurve]
depends_on: []
questions: [Q2]
---

## Context

Upstream issue assaferan/ShimCurve#6: the gerbiness computation is wrong — "does not look at the projection onto the Aut_{±μ}(O) factor. The size of the gerbiness should be one when the degree of polarization is 1, but can be larger more generally."

Two code sites compute gerbiness-type data independently:

1. `code/level-structure/enumerate-H.m` (`createRecord`, ~`:246-248`): `gerbiness := #KG_level` where KG comes from `SemidirectToNormalizerKernel(O,mu)` (`code/level-structure/polarization-twisting.m:69`, wrapped by `GetKernelAsSubgroup` at `enumerate-H.m:49`); `aut_gerbiness :=` number of distinct Aut-components among KG's elements. Both columns are 100% populated in the DB (samples: deg 1 → gerbiness 2, aut_gerbiness 1; deg 2 → 4/2; deg 6 → 4/2 or 6/3) — so at least one of these disagrees with the issue's claim that deg 1 ⟹ gerbiness 1. That discrepancy is exactly what Q2 must resolve (definition mismatch vs computational bug).
2. `code/quaternion_orders/enumerate-O.m:258-260` (`LMFDBRowEntry(O,mu)`): hardcodes `Gerby_gen` = identity with the comment "gerbiness = 1 because f: Aut_{±mu}(O) → N_{Bˣ}(O)/Qˣ is injective — only correct when the degree of polarization is 1! TODO: handle this more generally." This is the site the issue links.

## Task

Once Q2 pins the definitions: implement them correctly in both sites, add asserted sanity checks, regenerate affected columns.

## Steps

1. Read Q2's answer. Write the definitions as docstrings on the relevant intrinsics (this is the lasting spec).
2. Implement `Gerby_gen` for deg μ > 1 in `LMFDBRowEntry(O,mu)`: compute the kernel of Aut_{±μ}(O) → N_{Bˣ}(O)/Qˣ from the `Aut` map object (`code/level-structure/aut_mu_O.m:9` returns the map; kernel elements are those whose Bˣ/Qˣ-image is trivial — but the map as constructed is claimed injective, so the correct kernel per Q2 may live elsewhere, e.g. in the semidirect product; follow the answer).
3. Fix/confirm `gerbiness`/`aut_gerbiness` in `createRecord`; if Q2 says the current numbers are right but the issue's expectation applies to a *different* column, document that in the issue-resolution note instead of changing code.
4. Add sanity assertions from Q2.4 (e.g. `deg_mu eq 1 implies <quantity> eq 1`) behind the existing test hooks; extend `tests/regression_enumerateH_small.m` with a gerbiness check for the D=6, deg 1, N=3 record against the (post-fix) known value.
5. Regenerate `data/quaternion-orders/*polarized*` (`EnumerateOmu(1000 : Write:=true)`, background — long) and, if `createRecord` changed, the `genera-D6-*` corpus (README driver loop; the D6/deg6/N6 case alone took ~33 min historically — run all 15 in background, ~1h total). Diff old vs new: only gerbiness-related columns change.
6. Stage a column update file for the DB (`label|gerbiness|aut_gerbiness` via `update_from_file`) in `artifacts/`, load commands in the Log.
7. Draft a comment for upstream issue #6 describing the resolution (do not post it — leave in Log for David).

## Acceptance criteria

- Definitions written as docstrings; both code sites derive from them.
- Sanity assertion holds over all regenerated data; tests green.
- Diff of regenerated vs old data shows changes only in the intended columns, summarized in the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave1-A-fable): **Implemented per Q2's DECIDED definitions.** Branch `ticket/T07-fix-gerbiness` (worktree tier1core, stacked on T10 → T29 → T28), commit `2aa137f` (+ verification commits below).

  **T09-first question (resolved: T07 proceeds, T09 can wait).** The D=6 corpus and the shipped `quaternion_orders_polarized` DO use the T09-suspect constructions — devmirror AutmuO_label counts: C2 379, C2² 353, **D4 119, D6 39** (no C4/C6 anywhere); D=6 itself: deg 1 → C2², deg 2 → **D6** (order 12), deg 6 → **D4** (order 8). But in Magma V2.29-7 `DihedralGroup(GrpPC, 4|6)` gives `Dn.2` full element order ([2,6,3]/[2,4,2] generator orders measured), the 12/8-element lists are distinct and correct, and `MapIsHomomorphism(… injective)` passes on all three D=6 cases — the FIXMEs do not bite on this corpus/version. T09 remains real hardening work (version-robustness + element-list conventions) but does not block T07.

  **The mathematical content pinned down (for Eran's review).** The map whose kernel is the moduli gerbe is f: Aut_{±μ}(O) → Aut(X(D;1)) — the action on the **coarse** curve. σ acts trivially ⟺ σ is **inner by a reduced-norm-1 unit of O** (necessarily a root of unity ζ_{2n}); ker(f) ≅ ⟨ζ_{2n}⟩/{±1}, cyclic of order n ∈ {1,2,3}. Relations, all verified empirically on D=6: `#KG = 2·gerbiness` (KG carries the (1,−1) absorbed into the "±"); `aut_gerbiness = gerbiness` numerically whenever the mod-N reduction of the band is faithful (always for working modulus ≥ 3, Minkowski / LSSV Lemma 3.5.7) — so **the new gerbiness column coincides with the existing aut_gerbiness on all D=6 data; Q2.1's "generally smaller than aut_gerbiness" does not materialize** (both count the same band; flagging since Q2 called it a genuinely third quantity — it is third relative to *stored* semantics, not in value). Values (with the μ this code picks): deg 1 → 1 (band ±1), deg 2 → 3 (band ζ₆), deg 6 → 2 (band ζ₄).
  - ⚠️ **μ/Pollack-class dependence (Q3 cross-ref):** the shipped DB's deg-2 rows carry 4/2 (a ζ₄-band μ) while the current `HasPolarizedElementOfDegree(O,2)` yields a ζ₆-band μ (6/3). Gerbiness is an invariant of the polarization **class**, not just (O, deg) — one more consumer for T08's canonical-and-complete μ enumeration.
  - ⚠️ **Sanity theorem, scoped:** "gerbiness = 1 ⟸ deg μ = 1" is a theorem **for maximal orders** (μ² = −disc, disc squarefree ≥ 6 kills the Q(μ)-side band) and is asserted inside `Gerbiness`. For **Eichler** orders it is *not* forced in general; however for the X(D,N;1) rows the Q(μ)-side is provably trivial (DN = 3k² or 4k² is impossible when D is a genuine quaternion discriminant with gcd(D,N) = 1 — every p | D would need even valuation), leaving only a χ-side ζ₄ as a possibility; spot checks (B₆, Eichler levels 2/5/11) all give 1. The ⟺ direction holds on the regenerated D=6 corpus (deg 2 → 3, deg 6 → 2, both > 1) and is enforced by the new regression checks, but is **not** asserted as a general theorem in code — Eran should confirm the intended scope.

  **Code changes** (`2aa137f`):
  1. `code/level-structure/aut_mu_O.m`: new intrinsics **`GerbeKernel(O,μ)`** (elements of ker(f) as ⟨σ, unit⟩ pairs + generating unit; docstring = the decided definition, incl. the KG relation and the LSSV §3.5 anchor) and **`Gerbiness(O,μ)`** (= #ker(f), with the maximal-order deg-1 assert).
  2. `enumerate-H.m` `createRecord`: `gerbiness` column now stores #ker(f) (computed once per (O,μ) in `GenerateDataForGerbiestSurjectiveH`, with `assert #KG eq 2*gerb`); **`base_gerbiness` := #KG_level** added (the old gerbiness value, renamed per Q2.2); `aut_gerbiness` kept unchanged (Gauss–Bonnet at the `area_term` consumes it). Docstring on `GetKernelAsSubgroup` spells out all three quantities.
  3. `enumerate-O.m` `LMFDBRowEntry`: `Gerby_gen` = genuine generator of ker(f) — primitive integral B-coordinate representative of the generating unit's class (**Eltseq(B!·) per the ⟐ recommendation**, primitivized to fit the `integer[]` column exactly as `AutmuO_generators` is; the norm-1 unit itself can have half-integral coordinates, recover as gen/√nrd). Polarized writers (.m and .txt): + `gerbiness` column, appended **last** so existing positional readers (tablesX0DN preload reads fields ≤ 6) are unaffected: 10 → 11 cols.
  4. `tablesX0DN.m` `X0DNdata`: hardcoded `gerbiness := 1; aut_gerbiness := 1` replaced: live `Gerbiness(O,μ)` when μ is computed in the fallback branch; theorem-backed default 1 when only the preloaded AutmuO size is available (no μ in hand; see scoped-theorem note above); `base_gerbiness := 2·gerbiness`, `aut_gerbiness := gerbiness`. TODO left for T06/T27: preload the new gerbiness column from the polarized files once regenerated.
  5. Writer schemas: **68 → 69 cols** (`?`-writer: `base_gerbiness` inserted alphabetically after `bad_primes`) and **70 → 71 cols** (`|`-writer: same position). Exact delta for T04/T25: one new column `base_gerbiness integer` in both; all other columns and their order unchanged.
  6. `tests/regression_enumerateH_small.m`: deg-1 records must have (gerbiness, base_gerbiness, aut_gerbiness) = (1,2,1); deg-2/6 `Gerbiness` = 3/2 with `#KG = 2·gerbiness` and a norm-1-unit generator.

  **Deviation from Q2.4 (flagged for Eran):** the unconditional injectivity assert at `aut_mu_O.m:66` was **kept, not dropped**. It checks `grp_map: A → Bˣ/Qˣ`, which is injective **by construction** (A is built to biject with its image; downstream `#Domain` counts rely on it), and it demonstrably does **not** fire on the gerby deg-2/6 cases (probe above; the full corpus regenerates fine — T29 already ran it twice). The non-injective map of issue #6 is the moduli f, which is now computed directly by `GerbeKernel`. A comment at the assert documents the distinction. If Eran still wants it relaxed, it is a one-line change.

  **LSSV §3.5 cross-check (the ⟐ 2-liner):** LSSV Lemma 3.5.3 identifies automorphism pairs (γ, x) ∈ Aut(O) ⋉ (O/I)ˣ with Aut°(A[I]); the ±μ-polarized specialization restricts γ to Aut_{±μ}(O), and the generic object's automorphisms are exactly the pairs (σ_u, u⁻¹) with u a norm-1 root of unity of O — i.e. KG, whose image in the Aut factor is ker(f) after the ±1 (present for every object) is absorbed. Faithfulness of the mod-N view for N ≥ 3 is Minkowski (LSSV Lemma 3.5.7). So ker(f) is precisely the residual gerbe band. ✔

  **Deferrals (per plan):** full `EnumerateOmu(1000 : Write:=true)` polarized-file regeneration **deferred to post-T07+T08 merge (T06 wave)** — agent B is rewriting the μ computation concurrently and a polarized regen now would produce files conflicting with theirs. `LMFDBRowEntry`/`Gerby_gen` verified on samples instead: D=6 deg 1/2/6 rows print 11 well-formed fields with Gerby_gen = {1,0,0,0} / {1,1,3,1}-class (ζ₆) / {0,0,−1,0} (ζ₄) and gerbiness 1/3/2; Eichler deg-1 samples (levels 2/5/11) give gerbiness 1.

- 2026-07-22 (wave1-A-fable): **VERIFIED + CLOSED → review.** Commits: `2aa137f` (code), `9defaf1` (regenerated corpus). Branch `ticket/T07-fix-gerbiness`.
  - **Full-corpus regeneration + diff (ticket step 5): ALL CLEAN.** Baseline pass at T10-state code, then T07 pass; field-mapped comparison of all 15 files (2,198 rows): row counts and label sequences identical; **new `base_gerbiness` == old `gerbiness` on every row** (including the mod-level band collapse at levels 1–2: deg-1 N∈{1,2} rows have base 1 not 2, etc.); **new `gerbiness` = 1/3/2 for deg 1/2/6 uniformly** (level-independent, as the definition demands); every other column identical except the two presentation-dependent encodings (`generators`, `ram_data_elts`) whose per-process churn is the documented T29 leftover. Corpus totals per file: deg1 5/28/36/262/321, deg2 5/28/36/331/321, deg6 5/28/55/262/475 = 2,198 ✓ (matches the shipped enhanced-row count). The N=5 deg-1 evidence file (175 rows) regenerated under the 69-col schema too.
  - **Sanity theorem on the corpus:** gerbiness = 1 ⟺ deg μ = 1 holds on every regenerated row (⟸ asserted in code for maximal orders; ⟾ verified by the deg-2/6 values 3/2 > 1).
  - **`tests/run_quick.m` green** (0 failures, 0 skips) including the new gerbiness-family regression checks.
  - **Artifact staged (step 6):** `shimcurve_tickets/artifacts/T07-gerbiness-update.txt` — 2,373 rows (2,198 corpus + 175 N=5) of `label?gerbiness?base_gerbiness`, **PROVISIONAL — pending T27 reload** (canonical-sort labels; a label-keyed update against the current DB is unsafe, and the deg-2 shipped rows even carry a different Pollack-class μ). Value profile: (1,1)×33, (1,2)×794, (3,3)×33, (3,6)×688, (2,2)×33, (2,4)×792. Load commands (T27 time): `db.gps_shimura_test.add_column("base_gerbiness","integer")` then `update_from_file(".../T07-gerbiness-update.txt", label_col="label", sep="?")` — see artifacts/T07-README.md.
  - **Schema delta for T04/T25:** `?`-writer 68 → 69 cols, `|`-writer 70 → 71 cols; single new column `base_gerbiness integer`, inserted after `bad_primes` in both; polarized writers 10 → 11 cols (`gerbiness integer` appended last). No other column or ordering changes.
  - Scratch: `.t07-baseline/` in the worktree (untracked) holds the T10-state baseline pass + single-file drivers used for the diff; safe to delete after review.
  - **Draft closing comment for upstream issue #6 (do NOT post — for David):**
    > Fixed on `ticket/T07-fix-gerbiness` (commits 2aa137f, 9defaf1), following the definitions settled in QUESTIONS Q2. The confusion was three distinct quantities sharing one name:
    > 1. `gerbiness` now stores #ker(f), where f: Aut_{±μ}(O) → Aut(X(D;1)) is the action on the coarse curve: an automorphism acts trivially exactly when it is inner by a reduced-norm-1 (finite-order) unit of O, so ker(f) ≅ ⟨ζ_{2n}⟩/{±1} is cyclic of order n ∈ {1,2,3}. This is the size of the gerbe of the moduli stack — the issue's notion: 1 whenever deg μ = 1 (theorem for maximal orders, asserted in code), and larger in general (D=6: deg 2 → 3, deg 6 → 2). Computed by the new `GerbeKernel`/`Gerbiness` intrinsics (`code/level-structure/aut_mu_O.m`), used by `createRecord`, `LMFDBRowEntry`, and `X0DNdata`.
    > 2. The value the column *used* to store — #KG_level, the full root-of-unity band of ker(Aut_{±μ}(O) ⋉ Oˣ → N_{Bˣ}(O)/Qˣ) reduced mod N, which equals 2·#ker(f) rationally since the (1,−1) it contains is absorbed into the ± of Aut_{±μ}(O) — is kept under the new name `base_gerbiness`.
    > 3. `aut_gerbiness` (Aut-components of KG, used by the Gauss–Bonnet genus normalization) is unchanged; it agrees numerically with the new gerbiness whenever reduction mod N is faithful (N ≥ 3, Minkowski).
    > `Gerby_gen` is now a genuine generator of ker(f) (primitive integral representative of the generating unit's Bˣ/Qˣ-class, matching the `AutmuO_generators` normalization) instead of the hardcoded identity. The D=6 corpus was regenerated and diffed against a pre-change baseline: only the gerbiness-family columns changed.

- 2026-08-01 (opus session): **[D7] APPROVED AS-IS** — see [DECISIONS.md](DECISIONS.md).
  `gerbiness` := #ker(f), `base_gerbiness` added, and the writer schema delta are all
  blessed. **Q2.2's optional rename `aut_gerbiness` → `aut_band` is DECLINED**: the column
  keeps its name, so nothing further to do on that front. The "coincides numerically with
  `aut_gerbiness` on all D=6 data" finding is acknowledged and recorded in QUESTIONS.md §Q2
  so nobody re-reports it as a bug.
  **Ticket stays `review`**: [D8] (keeping the `aut_mu_O.m:66` injectivity assert) and [D10]
  (maximal-only scope of the deg-1 theorem) both route to **Eran** and are unanswered; [D9]
  (Gerby_gen coordinates) and [D11] (post the issue-#6 comment) are also still open.
