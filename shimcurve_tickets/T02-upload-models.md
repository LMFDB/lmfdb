---
id: T02
title: Relabel + stage the models upload; create shimcurve_modelmaps / shimcurve_teximages tables
status: review
owner: wave2-G-opus
priority: P0
tier: 0
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T01]
questions: [Q1]
---

## Context

The frontend renders models and maps between models, reading three tables:

- `db.shimcurve_models` — exists on devmirror with **1 row**. Columns (from frontend usage, `~/claude/lmfdb/lmfdb/shimura_curves/web_curve.py:411,420,544-547`, `main.py:424-426,469-471`): `shimcurve` (curve label FK), `equation`, `number_variables`, `model_type`, `smooth`, `dont_display` (+ comment mentions `gonality_bounds`).
- `db.shimcurve_modelmaps` — **does not exist**. Frontend expects `domain_label, domain_model_type, codomain_label, codomain_model_type, coordinates, leading_coefficients, factored, degree, dont_display` (`web_curve.py:430-435,567`, `main.py:464-467`).
- `db.shimcurve_teximages` — **does not exist**. Frontend expects `label, image` (`web_curve.py:1011`); for modular curves this holds pre-rendered TeX images of level-structure names used in lattice diagrams.

Local data: `~/claude/ShimCurve/data/models/lmfdb_shim_models.txt` (462 records, old labels, no header). Record shape appears to be `f|{equation}|[opt int]|int|int|old_label|t` — the field roles must be pinned down against the modular-curve analogue and the 1 existing devmirror row.

`model_type` codes in the frontend (`web_curve.py:441-470`): 0 = canonical, 2 = plane, 5 = Weierstrass?, 7 = geometric hyperelliptic, 8 = embedded (check the code — the mapping is explicit there).

## Task

Produce postgres-ready upload files for `shimcurve_models` under the **new** labels, plus `create_table` statements for `shimcurve_modelmaps` and `shimcurve_teximages`, and exact load commands. Do **not** run anything against a writable database.

## Steps

1. Inspect the existing devmirror row and the modular-curve templates:
   `select * from shimcurve_models;` and `\d modcurve_models`, `\d modcurve_modelmaps`, `\d modcurve_teximages` — use the modcurve schemas as the blueprint (drop columns Shimura can't fill yet rather than inventing new ones).
2. Parse `lmfdb_shim_models.txt` handling multi-line equations (a new record starts on a line whose first field is `t`/`f` — verify). Establish each positional field's meaning by cross-checking: the `number_variables` int must equal the number of distinct variables in the equation; `model_type` must be consistent with equation shape (conic/quartic in 3 vars ⇒ plane=2; y² = sextic ⇒ geometric hyperelliptic).
3. Apply T01's label map (`artifacts/T01-label-map.csv`). Rows mapping to UNMAPPED go to a parked file `artifacts/T02-models-parked.txt` with the same format (they wait on Q1.2 / T19-T21 coverage).
4. Emit `artifacts/T02-shimcurve_models.txt` in standard copy format (3 header lines: names, types, blank), matching the devmirror table's columns exactly; set `dont_display = f` except where the source marked otherwise.
5. Write the `create_table` calls for `shimcurve_modelmaps` and `shimcurve_teximages` (mirroring modcurve types), and — if any model maps are derivable from the source data (they may not be) — an upload file for them too.
6. Also stage the update of `gps_shimura_test.models` (smallint: number of displayed models per curve) for affected labels: emit `artifacts/T02-gps-models-count-update.txt` with columns `label|models` suitable for `db.gps_shimura_test.update_from_file`.
7. Append to this ticket's Log the exact commands for David to run, e.g.:
   ```python
   # sage -python, editor credentials, from ~/claude/lmfdb
   from lmfdb import db
   db.shimcurve_models.copy_from('.../T02-shimcurve_models.txt', sep='|')
   db.create_table(...)  # modelmaps, teximages — spelled out fully in the Log
   ```
8. Verification: reload a local LMFDB dev server pointed at a database where David has loaded the file (or, before that, unit-test the parse by round-tripping 5 sample records) and confirm the Models section renders on one affected curve page.

## Acceptance criteria

- Upload file passes a lint script (correct column count on every record, all labels match `LABEL_RE` from `main.py:60`, equations non-empty, types line matches the table).
- Parked file + upload file together account for all 462 source records.
- `create_table` statements are complete (search columns, label column, sort order specified) and copied into the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-G-opus): **DONE → review.** Staged the models upload, wrote the
  two `create_table` calls, and staged the gps models-count update. All artifacts under
  `shimcurve_tickets/artifacts/`; scripts committed in worktree `ticket/T02-upload-models`
  (`code/scripts/t02_*.py`). No DB writes; devmirror used read-only.

  **Field-role pinning (models file `data/models/lmfdb_shim_models.txt`, 462 records).**
  Robust record shape, indexed from the END so the optional empty middle field and the
  multi-line equations (embedded newlines inside `{…}`) don't shift columns:
  `lead | {equation} | [opt empty] | model_type | number_variables | label | smooth`.
  Verified over all 462: `lead` always `f` (= `dont_display`), `smooth` always `t`,
  `number_variables` == actual #distinct variables on every record, 4 records carry an
  extra empty middle field (the `[opt]` slot), 458 distinct labels + 4 duplicate labels.
  The **source `model_type` code is NOT the LMFDB code** (source ∈ {3,5,7}; LMFDB/modcurve
  ∈ {0,2,5,7,8}, no 3; source `5` even spans genus-0 conics, genus-1 cubics, genus-1
  quadric-intersections and genus≥2 hyperelliptics). So model_type is **derived from
  (equation shape)**, cross-checked against `modcurve_models` on devmirror and against
  `formatted_model()` in `web_curve.py`:
  - single deg-2 conic (3 vars) → **2** (plane); matches the 1 existing devmirror row
    `6.1.1.4.0.a.1` = conic → type 2.  [152 recs]
  - single 3-var equation with a `y^2` term, deg ≥ 3 (genus-1 cubics + genus≥2 weighted
    `y^2=f`) → **5** (Weierstrass); confirmed modcurve stores genus-2..9 `y^2=sextic/…`
    in 3 vars as type 5 (e.g. `10.30.2.a.1`), reserving type 7 for the 4-variable
    `{conic, w^2=f}` form.  [241 recs]
  - 4-var 2-quadric intersections, 3-var double covers `{y^2=f, z^2=g}`, and 2-var
    `y^2=quartic` → **8** (embedded).  [69 recs]  Rationale: `formatted_model` strict-parses
    ONLY types 5 & 7 (5 needs 3 vars + `y^2`; 7 needs 4 vars + `w^2`); every other type
    renders via the generic `teXify_pol` else-branch, which is crash-proof for any shape.
    The source's genus-1/3 "geometric hyperelliptic" reps are in a 2-/3-variable
    auxiliary-square form the frontend's 4-var type-7 cannot consume, so they are parked
    as type 8 for safe generic display rather than risk a math re-expression (flagged below).
  Equation normalization is **lossless + syntactic only**: strip TeX braces `x^{10}→x^10`;
  move `A = B` to `A - (B)` (=0 form); insert `*` between adjacent variable letters
  (`xyz→x*y*z`) and after coeff/paren where Sage needs it; collapse embedded whitespace.
  No homogenization, no coefficient changes. Implicit multiplication like `2x^6`, `x^4z^2`
  is left as-is (Sage parses it). The existing shimura equation convention is
  implicit-multiplication (no `*`), unlike modcurve's explicit `*`.

  **Split (accounting — acceptance criterion met).** 53 staged + 409 parked = **462** source
  records. Staged = the 53 `MAPPED_PROVISIONAL` `[1]` bases (33 type-5, 20 type-8), keyed by
  their currently-shipped coarse label. Parked = 409 UNMAPPED (404 pending-generation incl.
  the 15.4 quotients, 4 grammar-violation, 1 no-coarse-row) — no target curve row exists yet.

  **Duplicate-label resolution (4 pairs).** `39.1-[1,13]`, `55.1-[1,5]`, `62.1-[1,2]`,
  `69.1-[1,3]` each have TWO reps: a clean 4-var P³ embedded model AND a 2-var `y^2=quartic`
  plane model — i.e. **two legitimate distinct models of one genus-1 curve, not an error**;
  both kept (a curve may carry several models). All four are UNMAPPED_PENDING (parked), so
  no staging choice arises. Flagged: `39.1-[1,13]`'s quartic rep is **corrupted** (a doubled
  `-34x^3` term) — David should regenerate/verify the four `y^2=quartic` reps.

  **Artifacts (all carry a PROVISIONAL banner; label-keyed ⇒ re-key after T27):**
  - `T02-shimcurve_models.txt` — staged copy file: `#`-banner + 3 psycodict header lines
    (`dont_display|equation|model_type|number_variables|shimcurve|smooth` ;
    `boolean|text[]|smallint|smallint|text|boolean`) + 53 rows. `shimcurve` FK =
    `mu_label.coarse_label` (= full coarse label; the form `web_curve.py:410-411` searches).
    NOT directly loadable — the `#` banner must be stripped (deliberate safety).
  - `T02-shimcurve_models-keys.csv` — durable join key per staged row for the T27 re-key.
  - `T02-models-parked.txt` — 409 parked records with join key + `park_reason` + equation +
    per-record notes (dup/corruption flags).
  - `T02-gps-models-count-update.txt` — `label|models` (all `models=1`) for the 53 bases.

  **create_table statements (complete; no map DATA is derivable — the models file has no
  inter-model coordinate maps and the points file holds point coords, T03, not maps, so
  both tables are created EMPTY). Validated structurally against the devmirror blueprints
  (`modcurve_modelmaps` minus `upload_id`; `modcurve_teximages` verbatim) by
  `code/scripts/t02_create_tables.py`:**
  ```python
  # sage -python, editor credentials, from ~/claude/lmfdb ; from lmfdb import db
  db.create_table(
      name='shimcurve_modelmaps',
      search_columns={'integer': ['degree'], 'text': ['domain_label', 'codomain_label'],
          'smallint': ['domain_model_type', 'codomain_model_type'],
          'text[]': ['coordinates', 'leading_coefficients'],
          'boolean': ['factored', 'dont_display']},
      label_col=None,
      sort=['domain_label', 'domain_model_type', 'codomain_label', 'codomain_model_type', 'degree'],
      id_ordered=False,
      table_description='Maps between models of Shimura curves (mirrors modcurve_modelmaps minus upload_id).',
      col_description={'degree': 'Degree of the map',
          'domain_label': 'Label of the domain Shimura curve (coarse label)',
          'domain_model_type': 'Model type of the domain model (0 canonical, 2 plane, 5 Weierstrass, 7 geometric hyperelliptic, 8 embedded)',
          'codomain_label': 'Label of the codomain Shimura curve (or j-line 1.1.0.a.1)',
          'codomain_model_type': 'Model type of the codomain model',
          'coordinates': 'Coordinates of the map, as a list of polynomials/rational functions',
          'leading_coefficients': 'Leading coefficient factored out of each coordinate',
          'factored': 'Whether the coordinates are displayed in factored form',
          'dont_display': 'Whether to suppress this map on the website'})
  db.create_table(
      name='shimcurve_teximages',
      search_columns={'text': ['label', 'image']},
      label_col='label', sort=['label'],
      table_description='Pre-rendered TeX images of level-structure names used in Shimura-curve lattice diagrams (mirrors modcurve_teximages).',
      col_description={'label': 'Identifier of the level-structure name whose TeX image is stored',
          'image': 'Pre-rendered TeX image (as stored for modular curves) of the level-structure name'})
  ```

  **Load commands (DAVID; ONLY AFTER the T27 reload + re-key — labels here predate T29):**
  ```python
  # sage -python, editor credentials, from ~/claude/lmfdb ; from lmfdb import db
  # 0) create the two aux tables (idempotent; safe to run now):
  #    python3 .../code/scripts/t02_create_tables.py --execute      # under sage -python
  # 1) re-key T02-shimcurve_models.txt: map each provisional 'shimcurve' label to the
  #    NEW coarse label via T02-shimcurve_models-keys.csv + T01-report.md §4, then:
  grep -v '^#' shimcurve_tickets/artifacts/T02-shimcurve_models.txt > /tmp/models_load.txt  # strip banner
  #    (edit /tmp/models_load.txt so column 5 holds the reassigned labels)
  db.shimcurve_models.copy_from('/tmp/models_load.txt', sep='|')     # appends (id auto)
  # 2) re-key + load the models-count update:
  grep -v '^#' shimcurve_tickets/artifacts/T02-gps-models-count-update.txt > /tmp/models_cnt.txt
  db.gps_shimura.update_from_file('/tmp/models_cnt.txt', label_col='label', sep='|')
  # 3) parked models load once their target curve rows exist (T19→T20→T09→T08 chain), via join key.
  ```

  **Verification (no writable DB on this machine, per instructions — parse round-trip +
  lint instead):** (a) `code/scripts/t02_lint.py` → **PASS** (col counts, `LABEL_RE`
  fullmatch on every FK, renderable model_type, non-empty equation arrays, header types
  line, accounting 53+409=462, gps rows == staged bases). (b) `t02_verify_type5.py` under
  Sage → **241/241** type-5 equations satisfy the exact `formatted_model(5)` assertions
  (3 vars, single eq, `y^2` coeff ±1). (c) parse round-trip on the FINAL staged file: 8
  type-5 rows re-read + Sage-parsed, 0 errors; all 53 equation arrays parse as `text[]`.
  (d) postgres `::text[]` cast of sampled equation arrays (incl. multi-poly + fraction) →
  valid, correct element counts. Did **not** touch the port-37778 dev server.

  **Flags for David:** (1) `39.1-[1,13]` `y^2=quartic` model rep is corrupted (doubled
  `-34x^3`); check all four dup-label quartic reps. (2) The 69 type-8 records include
  genus-1/3 "geometric hyperelliptic" curves whose source models are 2-/3-variable
  auxiliary-square forms; they render via the generic branch but do **not** get a proper
  type-5/7 (Weierstrass/geometric-hyperelliptic) display until re-expressed to the frontend's
  3-var `y^2=f` (type 5) or 4-var `{conic,w^2=f}` (type 7) form — a model re-computation,
  out of T02 scope. (3) Existing shimura equations use implicit multiplication (no `*`);
  types 5/7 are Sage-strict-parsed, so any future models must be stored `*`-free-but-parseable
  as here (or the frontend will 500). (4) 28 source records used an affine `y^2 = quartic`
  (`=`) form (2 vars) — normalized to `=0` and parked as type 8; homogenizing to weighted
  P(1,2,1) would promote them to type 5 (deferred, needs sign/weight care).
