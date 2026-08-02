---
id: T27
title: Rename gps_shimura_test; release checklist
status: open
owner: none
priority: P2
tier: 4
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T02, T03, T07, T11, T14, T24, T25]
questions: [Q12]
---

## Context

The main table's `_test` name (and its 10 accumulated `_old*` snapshots on the server) signal pre-release state. Final gate: rename per Q12.3, reload clean data, flip the sidebar out of beta when ready.

## Steps

1. Inventory every reference to `gps_shimura_test`: lmfdb repo (`grep -rn gps_shimura_test ~/claude/lmfdb/lmfdb/` — main.py×8, web_curve.py, stats) and ShimCurve (guide docs, make-table). Same for any table renames from Q12.3.
2. Prepare the rename as a coordinated change: one lmfdb commit switching the table name behind a single module-level constant (introduce `SHIMCURVE_TABLE = "..."` if not already factored), one DB-side script for David (`ALTER TABLE ... RENAME` or fresh `create_table` + reload from the regenerated corpus — prefer fresh create: the accumulated `_old*` tables and stale `_counts`/`_stats` argue for a clean start; include `db.<table>.stats.refresh_stats()` and search-column/sort configuration in the script).
3. Final reload: assemble the definitive upload fileset from all landed tickets (T04-format corpus + T12/T14/T15/T17/T18 update files), load order documented; verifiers from T25 run green post-load.
4. Release checklist (execute + check off in the Log): pytest suite; T24 manual page checklist; stats page shows correct totals; downloads round-trip; jump box resolves names and fiber products; sidebar entry text/status reviewed (`~/claude/lmfdb/lmfdb/homepage/sidebar.yaml:98-101`); rcs knowls uploaded (T26); CONTRIBUTORS.yaml current.
5. Coordinate: this ticket is mostly David-executed (DB writes, knowl uploads, PR to assaferan/lmfdb or upstream LMFDB); the agent's deliverable is the scripts, the fileset, and the checklist with everything pre-verified that can be.

## Acceptance criteria

- Rename lands in one reviewable commit + one DB script; verifier suite green on the renamed, reloaded table; checklist fully executed.

## Log

- 2026-07-16: ticket created from survey.

- 2026-08-01 (opus session): **the reload strategy is now SIGNED OFF and the schema deltas are
  pinned.** See [DECISIONS.md](DECISIONS.md). Everything below is decided, not proposed.

  ### [D5] The reload is a full atomic `copy_from` — approved
  The shipped labels are unreproducible (73% of rows change curve under the canonical sort,
  `psl2label` on 98%), so **label-keyed `update_from_file` against the current table is
  permanently unsafe**. T27 reloads the whole table with canonical labels under the new name,
  and the **304 `shimcurve_pictures` rows re-key** (they are keyed by `psl2label`, which [D4]
  changes on 2158/2198 rows). Every `PROVISIONAL — pending T27 reload` artifact in
  `artifacts/` unparks here, each re-keyed via its own invariant-key file.

  ### Schema deltas to apply before loading (both columns are new to the live table)
  ```python
  db.gps_shimura_test.add_column("base_gerbiness", "integer")   # T07 / D7
  db.gps_shimura_test.add_column("factorization", "text[]")     # D26
  ```
  Canonical schema is **72 columns** (`GpsShimuraSchema()`); `label` is not column 1.
  `factorization` loads as `\N` until **T12** computes fiber-product decompositions — populate
  it in the same pass if T12 has landed, otherwise leave null and populate later.

  ### [D31] The Pollack label cascade lands here — UNIMPLEMENTED WORK, schedule it
  `mu_label` becomes four components **`discB.discO.deg.i`** (maximal orders write
  discO = discB) and `quaternion_orders_polarized` becomes **one row per negation pair**
  {[μ], [−μ]}. This cascades into the curve label and widens `LABEL_RE`
  (`lmfdb/shimura_curves/main.py:57-60`). Nothing implements this yet — it needs a real
  implementation pass across `enumerate-O.m`, `enumerate-H.m` and the frontend regexes before
  the reload can produce final labels. T08's audit already maps each shipped row to its true
  class index, so migration is not blind. **Interaction:** even deg-1 needs the index (D=15
  has two principal-polarization pairs), so Q11's naming votes ([D54]–[D56], still open) must
  land before `name` generation (T18).

  ### [D46] Level convention
  Level-family columns come from the **congruence level**. The unified writers already do
  this, so the 71 + 86 + 303 rows T25's verify flagged self-heal on reload — no migration
  script, just don't reintroduce the Eichler-level computation.

  ### [D48] Prerequisite: fix the discB/discO swap FIRST
  `quaternion_orders.discB`/`discO` are swapped on all 640 Eichler rows. **T06 owns the fix
  and it must land before this reload**, otherwise the corrected labels get built on inverted
  order data.

  ### Also carried in from the review round
  - **T25's checklist**: rename `verify/shimcurve/gps_shimura_test.py` (+ class) to match the
    new table name, retarget the `shimcurve_models`/`_points` FK checks, add `UNIQUE(label)`
    (confirm on the primary — devmirror's `list_constraints()` returns `{}`), and reconcile
    the duplicated `columns.gps_shimura*` knowl sets.
  - **T24 is done and pushed** (D25), so its dependency is satisfied.
  - Still-open decisions that gate parts of this ticket: **Q12** (release scope, table name,
    completeness claims — this ticket's own `questions:` entry), [D26]'s population source
    (T12), [D43] (enhanced Jacobian rows), and the Q11 votes.
