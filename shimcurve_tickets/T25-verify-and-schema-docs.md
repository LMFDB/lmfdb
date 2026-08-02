---
id: T25
title: verify/ schema checks + table specification docs
status: review
owner: wave3-O-opus
priority: P2
tier: 4
repos: [lmfdb, ShimCurve, db-readonly]
depends_on: [T04]
questions: []
---

## Context

LMFDB tables ship with consistency checks under `~/claude/lmfdb/lmfdb/verify/` (e.g. `verify/modcurve/modcurve_modelmaps.py`). Nothing exists for the Shimura tables, and there is no committed schema spec beyond the partial notes in `~/claude/ShimCurve/code/utils/lmfdb-data-guide.txt` and `data/quaternion-orders/make-table.m`.

## Steps

1. Write `lmfdb/verify/shimcurve/` verification classes for `gps_shimura_test` (post-T27 name), `quaternion_orders`, `quaternion_orders_polarized`, `shimcurve_models`, `shimcurve_points`. Crib structure from `verify/modcurve/`. Checks worth encoding (each is a real invariant from the pipeline):
   - label ↔ (discO, deg_mu, level, index, genus, class, num) consistency; coarse_label consistency; mu_label = order_label.deg_mu; order_label exists in quaternion_orders; mu_label exists in quaternion_orders_polarized.
   - genus from Riemann–Hurwitz data: 2·index·(χ-ish via area) consistency — encode the Gauss–Bonnet identity used at `enumerate-H.m:280-283`: fuchsian_index, ν-counts, genus satisfy Area·index = 2g−2 + Σ ν_e(1−1/e).
   - Σ dims·mults = genus where dims present; simple/squarefree consistency with dims/mults; genus_minus_rank = genus − rank.
   - q_gonality within q_gonality_bounds; qbar ≤ q; bounds ordered.
   - parents: every parent label exists; parent index divides; parent genus ≤ genus.
   - pointless ⟹ num_known_degree1_points = 0; cm_discriminants are valid imaginary quadratic discriminants.
   - level_is_* flags match level; bad_primes = prime divisors of discO·level.
2. Table specs: write `~/claude/ShimCurve/code/utils/table-schemas.md` documenting every column of every table (name, type, definition, provenance ticket) — generated partly from T04's canonical constant; this becomes the reference the (future) preprint and knowls cite.
3. Run the verifiers against devmirror data; every failure is either a data bug (file a Log note + ticket reference) or a wrong check (fix). Expect hits: the columns entirely NULL are fine (verify skips), but e.g. the Gauss–Bonnet check will exercise the coarse rows' ν-columns immediately.
4. Keep the verify code on a local lmfdb branch `ticket/T25` for David to push.

## Acceptance criteria

- Verifier suite runs end-to-end against devmirror; results table (pass/fail per check) in the Log; every failure triaged.
- `table-schemas.md` covers all columns of all 5+ tables.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave3-O-opus): **DONE → review.** Both deliverables built and run against devmirror.
  - **lmfdb branch `ticket/T25-verify`** (worktree `/Users/roed/claude/lmfdb-wt/T25`), commit `4d949e5c0`:
    `lmfdb/verify/shimcurve/` = `_shimcurve_common.py` (mixin: raw-SQL helper, FK-existence helper,
    Gauss–Bonnet ν-weights) + one class file per table: `gps_shimura_test.py` (30 checks),
    `quaternion_orders.py`, `quaternion_orders_polarized.py`, `shimcurve_models.py`,
    `shimcurve_points.py`. Cribbed from `verify/modcurve` + `verify/gps`. Pyflakes-clean.
    **T27 rename note in-file**: at the `gps_shimura` rename, rename `gps_shimura_test.py` + its class
    (auto-discovery keys both to `db.tablenames`); `shimcurve_models`/`_points` FK checks retarget too.
  - **ShimCurve branch `ticket/T25-schema-docs`** (worktree `tier1core`, stacked on `ticket/T05-stale-readers`),
    commit `b819a30`: `code/utils/table-schemas.md` (all 119 columns of all 5 tables: name, pg type,
    definition, provenance, per-column knowl status) + `code/utils/gen_table_schemas.py` (the gps
    column backbone is parsed live from `schema.m` `GpsShimuraSchema()`; regen is DB-free).

  ### Environment path (per the ticket's fallback caveat)
  The verify **framework runs** against devmirror (search/count/`db._execute` all work) — BUT
  `from lmfdb.verify import db` triggers the package `__init__` auto-discovery walk, which imports
  every verify module and **crashes on the pre-existing `verify/mf/mf_newspaces.py`** (`ImportError:
  dimension_new_cusp_forms` — a Sage-version incompatibility, unrelated to T25). Harness bypasses the
  broken walk by injecting a bare `lmfdb.verify` package module, then imports the shimcurve classes
  directly and runs every `@overall` check. **Both paths were run and agree**: the framework harness
  (`scratchpad/run_verify.py`) and independent hand-SQL against devmirror give identical hit counts.
  The verify code is correct for a healthy environment (where the real `from lmfdb.verify import db`
  works once mf_newspaces is fixed — flag for whoever owns the mf verify modules / Sage bump).

  ### RESULTS TABLE — 56 checks, 46 clean / 10 with-hits / 0 error (devmirror 2026-07-22)
  | table | check | result | hits | triage → owner |
  |---|---|---|---:|---|
  | gps | check_label / mu_label / coarse_label / coarse_class_letter / coarse_index | PASS | 0 | label grammar 2587/2587 |
  | gps | check_order_label_exists / mu_label_exists (FK) | PASS | 0 | 2587/2587 |
  | gps | **check_gauss_bonnet_enhanced** (#Aut form) | PASS | 0/2198 | — |
  | gps | **check_gauss_bonnet_coarse** (classical form) | PASS | 0/389 | — |
  | gps | genus=Σdims·mults / simple / squarefree / genus_minus_rank | PASS | 0 | Jacobian (339 rows) |
  | gps | traces_length(168) / trace_hash_present | SKIP | 0 | traces NULL until T14 loads |
  | gps | qbar_le_q / gonality_bounds_ordered / q_gonality_in_bounds / qbar_bounds_le_q_bounds | PASS | 0 | — |
  | gps | **check_qbar_gonality_in_bounds** | **HITS** | **11** | Q10 `gon_Qbar:=gon_Q_low` bug → T17/T27 |
  | gps | check_parents | PASS | 0 | all `parents` empty `{}` (nothing to exercise) |
  | gps | **check_pointless_implications** | **HITS** | **1** | pre-T15 (nk NULL, adk=f on the 1 shipped pointless row) → T15 |
  | gps | check_has_obstruction_iff_pointless | PASS | 0 | 1 row |
  | gps | check_cm_discriminants_valid | SKIP | 0 | 0 populated until T15 loads |
  | gps | **check_level_flags** | **HITS** | **71** | coarse level-vs-M: level_is_prime/_power=t on level-1 → T06/T27 |
  | gps | **check_level_radical** | **HITS** | **86** | coarse level_radical reflects Eichler M → T06/T27 |
  | gps | **check_num_bad_primes** | **HITS** | **303** | coarse rows: bad_primes NULL but num_bad_primes∈{2,4} → T06/T27 |
  | gps | check_bad_primes_divide | PASS | 0 | every bad prime divides discO·level; sorted/distinct |
  | gps | check_fine_label_when_coarse | PASS | 0 | fine_label=coarse_label (all coarse) |
  | gps | check_base_gerbiness | SKIP | 0 | column absent on devmirror (guarded) → arrives T27 |
  | quaternion_orders | **check_discB_divides_discO** / **check_label_matches_discs** | **HITS** | **640 / 640** | **discB/discO swapped** → T06 |
  | quaternion_orders | check_area_positive / gens_lengths | PASS | 0 | — |
  | quaternion_orders_polarized | check_label / order_label_exists(FK) / nrd_mu / mu_length / generator_lengths / autmuO_is_cyclic | PASS | 0 | nrd_mu·deg_mu=discO 890/890 |
  | shimcurve_models | model_type_valid / number_variables / equation_nonempty / shimcurve_exists(FK) | PASS | 0 | 1 row |
  | shimcurve_points | degree / curve_label_exists(FK) / cm_valid / curve_columns_agree | PASS | 0 | 0 rows (vacuous) |
  | gps, quat, pol | check_uniqueness_constraints (inherited) | **HITS** | **3** | no formal `UNIQUE(label)` on the pre-release tables (`list_constraints()={}`; data IS unique 2587/2587) → T27 |

  ### Triaged data bugs (all DATA bugs, not check bugs — every check re-verified as a correct invariant)
  1. **`quaternion_orders.discB`/`discO` are SWAPPED (640 rows, owner T06).** The column named `discB`
     holds the reduced order discriminant and `discO` holds the algebra discriminant — contradicting
     BOTH the label grammar (`discB.discO`) AND `gps_shimura_test`'s own discB/discO. Invisible on the
     304 maximal rows (discB=discO); wrong on all 640 Eichler rows. Cross-checked definitively:
     joining on `order_label`, quaternion_orders columns are swapped vs gps_shimura_test on all 86
     Eichler references (agree on the maximal ones). `area_*` is unaffected (computed from true discB),
     so Gauss–Bonnet was not disturbed. This is also the root of the `nrd_mu` "reciprocal" appearance.
  2. **`qbar_gonality` = `q_gonality` on 11 bielliptic coarse rows (owner T17/T27).** Exact ℚ̄-gonality
     is stored equal to the ℚ-gonality (e.g. 4), which is **twice** the correct value and **exceeds its
     own correctly-computed `qbar_gonality_bounds` {2,2}**. Rows: 10.1.1.4.0.a.1, 22.1.1.4.0.a.1,
     10.130.1.1.4.3.a.1, 14.42.1.1.4.3.a.1, 21.42.1.1.4.3.a.1, 57.1.1.2.3.a.1, 6.102.1.1.4.3.a.1,
     82.1.1.2.3.a.1, 10.190.1.1.4.5.a.1, 26.78.1.1.4.5.a.1, 93.1.1.2.5.a.1. This is exactly the Q10
     flag `X0DN_code.m:1394 gon_Qbar := gon_Q_low` (should be `gon_Qbar_low`) biting real shipped data.
  3. **Coarse level-family columns computed from the Eichler level M, not the congruence level 1
     (owner T06/T27; = T15 flag #2).** `level_is_prime`/`level_is_prime_power`=t on 71 level-1 rows
     (where M is prime), `level_radical` = rad(M) ≠ 1 on 86 level-1 rows. Also `level_is_prime` /
     `level_is_prime_power` are **NULL on all 2183 level>1 rows** (only ever set by the old coarse
     writer). Self-heals at T27 (both unified writers now emit F at level 1 from the congruence level).
  4. **`bad_primes` NULL while `num_bad_primes`∈{2,4} on 303 coarse rows (owner T06/T27).** The coarse
     writer set the count but left the array `\N`. (All 2198 enhanced + 86 coarse rows have bad_primes.)
  5. **`nrd_mu`·`deg_mu` = `discO` on all 890 polarized rows — the RECIPROCAL of the gps convention
     `Norm(μ)=deg_mu·discO` (owner T06/T08).** Either `nrd_mu` stores nrd of a deg_mu-scaled μ, or the
     column is misnamed. Flagged for Eran; the verify check encodes the relation the data satisfies.
  6. **1 shipped `pointless` row** (`6.1.1.4.0.a.1`) has `num_known_degree1_points` NULL (not 0) and
     `all_degree1_points_known`=f — pre-T15 partial population; T15's staged artifact fixes both.
  7. **No formal `UNIQUE(label)` constraint** on gps/quaternion_orders/_polarized (T27 should add it;
     labels are unique in the data, 2587/2587 etc.). (`list_constraints()` returns `{}` on devmirror —
     possibly a mirror/metadata-format-0 limitation; confirm on the primary before adding.)

  ### s3=e3 (T19) evidence — NOT corroborated in current data (verdict deferred to T20 per ticket)
  The Gauss–Bonnet check exercises every coarse ν-column and **passes 389/389** under the classical
  form, so the shipped coarse ν-columns are all self-consistent with genus. The suspected s3=e3 bug
  (X0DN_code.m:185, nu3 too large for AL quotients with m≡1,2 mod 4) **cannot manifest here**: all 389
  coarse rows are BASE curves X₀(D;M) (trivial W, m=1), where s3=e3 is correct. It will only surface
  once T19/T20 generate AL-quotient (nontrivial-W) coarse rows — at which point `check_gauss_bonnet_coarse`
  will catch a systematic nu3 defect. Logged as evidence for the T20 agent; no verdict rendered here.

  ### Deviations / decisions
  - **Gauss–Bonnet is BRANCHED, not unified** (the key design correction). Enhanced rows (autmuO_norms
    populated, from enumerate-H.m) obey the #Aut-normalised identity `genus = 1 + aut_gerbiness·
    fuchsian_index·Area/AutmuO_size − ½Σν_e(1−1/e)` (enumerate-H.m:323-326) — pass 2198/2198. Coarse
    rows (from tablesX0DN.m) obey the **classical** Shimura form `genus = 1 + Area − ½Σν_e(1−1/e)`
    (no #Aut factor) — pass 389/389. A single unified check applying the #Aut form to coarse rows
    wrongly flags 51 rows; that was a CHECK bug (fixed by the split), NOT a data bug. Both forms need
    the `Area` join to quaternion_orders (area unaffected by the discB/discO swap).
  - **`nrd_mu` check** uses the empirically-true `nrd_mu·deg_mu=discO` (discO parsed from order_label,
    so swap-independent), documented as a discrepancy vs the gps convention rather than asserting the
    gps form (which would false-fail 500 rows).
  - table-schemas.md covers 119 columns (71+9+10+6+19 + `id` rows); gps backbone generated from schema.m.
  - Scratch harness: `/private/tmp/.../scratchpad/run_verify.py` (safe to delete).

  ### Flags for David
  1. **discB/discO column swap in `quaternion_orders`** is the single most impactful finding — fix under
     T06 before the T27 reload (it silently mislabels every Eichler order).
  2. `nrd_mu` reciprocal-vs-`Norm(μ)` semantics (finding 5) needs an Eran ruling (misnamed column vs
     scaled μ) — affects the schema-doc definition and the quaternion_orders_polarized knowl.
  3. The **mf verify modules don't import under this Sage** (`mf_newspaces.py` → `dimension_new_cusp_forms`),
     which blocks the real `from lmfdb.verify import db` entry point for ALL tables, not just shimcurve
     — worth fixing alongside the Sage/psycodict environment work.
  4. T27 checklist adds: rename `gps_shimura_test.py`→`gps_shimura.py` (+class), add `base_gerbiness`
     + reconcile the duplicated/misaligned `columns.gps_shimura*` knowl sets (§6 of table-schemas.md),
     add `UNIQUE(label)`, and the checks above go green once the T06/T14/T15/T17 fixes land.

- 2026-08-01 (opus session): **[D48] CONFIRMED — the discB/discO swap is real; T06 owns the
  fix, before the T27 reload.** See [DECISIONS.md](DECISIONS.md). Recorded in T06's Log as an
  assigned work item. Also relevant to this ticket's results table:
  - **[D46] congruence level** settles `check_level_flags` (71 hits) and `check_level_radical`
    (86 hits) as **data bugs that self-heal at T27**, not check bugs — the checks stay as
    written.
  - **[D26]** adds `factorization text[]` to the canonical schema (72 columns now), so
    `table-schemas.md` needs the new row and the T27 checklist in this ticket's close-out
    grows a second `add_column`. The generator parses `schema.m` live, so a regen picks it up.
  **Ticket stays `review`**: [D47] (approve the suite + doc) and [D49] (`nrd_mu` semantics —
  routes to Eran) are unanswered.
