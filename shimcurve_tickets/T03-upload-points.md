---
id: T03
title: Relabel + stage the rational-points upload (shimcurve_points)
status: review
owner: wave2-G-opus
priority: P0
tier: 0
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T01]
questions: [Q1]
---

## Context

`db.shimcurve_points` exists on devmirror with **0 rows**. The frontend's point search and curve-page point tables read: `curve_label, curve_name, curve_genus, curve_level, curve_index, degree, isolated, cm, residue_field, j_field, jinv, jorig, j_height, coordinates, cusp, conductor_norm` and an elliptic-curve label column (`~/claude/lmfdb/lmfdb/shimura_curves/main.py:900-914`, `web_curve.py:765-781`). Note a known frontend inconsistency: search code uses `Elabel`, curve pages use `Clabel` (T24 fixes this — coordinate on which name the table will use; check the actual devmirror schema with `\d shimcurve_points` and treat it as authoritative).

Local data: `~/claude/ShimCurve/data/rational points/lmfdb_shim_rational_pt_updated.txt` — ~424 records, 20 pipe-delimited columns, no header. Populated: col 3 = number of rational points (`0`…`10`, `infinite`), col 6 = coordinate list `{[4,-9,1],...}` or `[]`, col 7 = 0/1, col 11 = `1`, col 12 = old curve label. Everything else `\N`.

Important: this file mixes two kinds of information — (a) individual point records (coordinates) that belong in `shimcurve_points`, and (b) per-curve counts (`num_known_degree1_points`, `pointless`, and "infinite" ⇒ genus 0 with a rational point) that belong in `gps_shimura_test` columns.

## Steps

1. `\d shimcurve_points` on devmirror; also `\d modcurve_points` as the semantic reference. Pin down each of the 20 source columns by comparing several records against curves whose points are known (e.g. genus-0 conics with obvious points); document the inferred layout in the Log.
2. Apply T01's label map; park UNMAPPED records in `artifacts/T03-points-parked.txt`.
3. Emit two staged files in `artifacts/`:
   - `T03-shimcurve_points.txt` — one row per known point (coordinates from col 6), with `degree=1`, `residue_field='1.1.1.1'`-style rationals convention copied from modcurve_points, `coordinates` in the model/coordinate convention the frontend displays (check `web_curve.py` display code; coordinates must reference a model uploaded in T02 — if the model reference scheme is per `model_type`, encode which model the coordinates live on).
   - `T03-gps-points-update.txt` — per-curve update file (`label|num_known_degree1_points|pointless|...`) for `db.gps_shimura_test.update_from_file`: count `0` ⇒ `num_known_degree1_points=0` (leave `pointless` NULL unless a proof exists — a search finding nothing is not pointlessness), `infinite` ⇒ set `num_known_degree1_points` NULL? or a sentinel — **check how modular curves handle genus-0 infinite points** (they use `pointless=f` and leave counts for isolated points; copy that convention) — document the decision.
4. Write load commands into the Log (copy_from / update_from_file), for David to execute.
5. After David loads: verify one curve page shows its points, and the low-degree point search returns rows (`/ShimuraCurve/Q/low_degree_points`). Note: the curve-page points sections are currently commented out in `shimcurve.html:185-240` — re-enabling them is part of T24; verification before that lands can use the search page only.

## Acceptance criteria

- Every source record is either in a staged file or parked with a reason; a lint script validates column counts/label regex/types.
- The count-vs-point-record split is documented and consistent with modcurve conventions.
- Load commands in the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-G-opus): **DONE → review.** Stacked on `ticket/T02-upload-models`
  (branch `ticket/T03-upload-points`). Split the points file into per-point records
  (`shimcurve_points`) and per-curve counts (`gps_shimura_test`), staged/parked by T01's
  map. Artifacts under `shimcurve_tickets/artifacts/`; scripts in `code/scripts/t03_*.py`.
  No DB writes; devmirror read-only.

  **Source parse (`data/rational points/lmfdb_shim_rational_pt_updated.txt`, 424 records,
  all 20-col clean, all distinct labels).** 0-indexed columns used: `col2`=#points
  (`0..10`/`infinite`), `col5`=coordinate set, `col6`=genus, `col10`=M, `col11`=legacy
  label; rest `\N`. Genus matches T01 on all 424 (0 mismatches). 317 individual points
  total; coordinate arity is **3 (289 pts, P²) or 4 (28 pts, P³)**.

  **Authoritative schema = `\d shimcurve_points` on devmirror** (uses `Clabel` not
  `Elabel`, plus `Igusa_invs`, `quo_info`; `coordinates` is **jsonb**). Column layout of
  the staged copy file (19 search_cols, introspected order):
  `Clabel|Igusa_invs|cardinality|cm|conductor_norm|coordinates|curve_genus|curve_index|
   curve_label|curve_level|curve_name|degree|isolated|j_field|j_height|jinv|jorig|quo_info|
   residue_field`.

  **Point→model reference (modcurve convention, verified on `modcurve_points`):**
  `coordinates` jsonb = `{"<model_type>": ["a:b:c"]}` — one row per degree-1 point,
  colon-separated projective coords, keyed by the **model_type of the T02 model whose
  `number_variables` == the point's coordinate arity**. This join is **clean: 0
  unresolved/ambiguous points** — every arity-3 point sits on a genus≥1 3-var model
  (all type 5; the genus-0 conic quotients have *infinitely* many points and never
  materialize finite coords) and every arity-4 point on a 4-var embedded model (type 8).
  Result: 289 points → key `"5"`, 28 points → key `"8"`. Per-point fields set:
  `degree=1`, `residue_field="1.1.1.1"`, `curve_level=1`, `curve_genus` from source;
  `cm`,`isolated`,`jinv`,… left `\N` (source gives no CM/isolatedness/j data — no guessing).

  **Count-vs-point split (modcurve conventions, verified on `gps_gl2zhat`):**
  - `col2=k>0` → `num_known_degree1_points=k`, `pointless=f`, and k point rows.
  - `col2=0` → `num_known_degree1_points=0`, `num_known_degree1_noncm_points=0`,
    `pointless=\N` (a search finding nothing is not a proof; Shimura's D>1 theorem →
    `pointless=t` is a Q9/T15 determination, not T03's).
  - `col2='infinite'` → genus-0 curve with a rational point (≅ P¹): `pointless=f`,
    `num_known_degree1_points=\N` (matches modcurve genus-0 handling: pointless set, count
    left NULL, not enumerated). 139 such labels.

  **Staged vs parked (accounting — acceptance criterion met).**
  - Points: **0 staged + 317 parked = 317.** ALL 317 points lie on UNMAPPED AL-quotient
    curves (no target row yet); the 42 MAPPED `[1]`-base curves carry 0 points. The staged
    `T03-shimcurve_points.txt` is therefore a valid but EMPTY copy file (documented inside).
  - Per-curve counts: **42 staged + 382 parked = 424** (one count row per source record).
    Staged = the 42 MAPPED bases (all `num_known=0`); parked = 382 UNMAPPED.

  **Artifacts (all PROVISIONAL, label-keyed ⇒ re-key after T27 via T01-report §4):**
  - `T03-shimcurve_points.txt` — staged copy file (banner + 3 header lines + 0 rows).
  - `T03-points-parked.txt` — 317 parked point rows: join key + arity + model_type +
    `degree|residue_field|coordinates`. Coordinate fidelity spot-checked vs source
    (e.g. `26.1-[1,13]` → `{"5":["4:-9:1"]}`,…; `14.3-[1,21]` P³ fractions → `{"8":[…]}`).
  - `T03-gps-points-update.txt` — staged count update, 42 MAPPED bases
    (`label|num_known_degree1_points|num_known_degree1_noncm_points|pointless`).
  - `T03-gps-points-parked.txt` — 382 parked count updates (join key + counts + `coords_na`).

  **Load commands (DAVID; ONLY after T27 reload + re-key — labels predate T29):**
  ```python
  # sage -python, editor credentials, from ~/claude/lmfdb ; from lmfdb import db
  # per-point rows -- park file becomes loadable once each curve row exists (join key -> curve_label):
  #   build load.txt with shimcurve_points columns (curve_label from the join key, degree=1,
  #   residue_field=1.1.1.1, coordinates as staged), then:
  db.shimcurve_points.copy_from('points_load.txt', sep='|')      # (staged file is empty today)
  # per-curve counts -- staged 42 MAPPED bases (re-key labels first):
  grep -v '^#' shimcurve_tickets/artifacts/T03-gps-points-update.txt > /tmp/pts_cnt.txt
  db.gps_shimura.update_from_file('/tmp/pts_cnt.txt', label_col='label', sep='|')
  # parked counts load per join key once the curves exist.
  ```

  **Verification (no writable DB — lint + round-trip, per instructions):**
  `code/scripts/t03_lint.py` → **PASS** (staged points header = shimcurve_points cols+types,
  every `curve_label` LABEL_RE, valid jsonb `{mt:["a:b:c"]}` on all 317, `degree=1`,
  `residue_field=1.1.1.1`, gps header/types, `pointless∈{t,f,\N}`, accounting 0+317=317 and
  42+382=424). jsonb `::jsonb` cast + `jsonb_object_keys` validated on postgres. Coordinate
  round-trip spot-checked against source (above). Did not touch the port-37778 dev server;
  low-degree-point search page verification deferred to David post-load (curve-page point
  sections are commented out pending T24, per the ticket).

  **Flags for David:** (1) **Frontend inconsistency:** the points queries use bare
  `self.coarse_label` (`web_curve.py:765,769,773,778`) while models use
  `mu_label.coarse_label`; I keyed `curve_label` on the **full** coarse label (unique,
  matches `shimcurve_models.shimcurve` and `modcurve_points.curve_label`) — the frontend
  should be fixed to match (T24). (2) **9 curves have `col2=2` but `col5='NA'`** (count
  known, coordinates not materialized): `57.1-[1,57]`, `58.1-[1,58]`, `82.1-[1,82]`,
  `6.17-[1,102]`, `6.17-[1,6,17,102]`, `10.13-[1,130]`, `10.13-[1,5,26,130]`,
  `10.19-[1,2,95,190]`, `10.19-[1,10,19,190]` — flagged `coords_na=t` in the parked count
  file; `num_known_degree1_points=2` is set but they yield no point rows (regenerate coords?).
  (3) `cm`/`num_known_degree1_noncm_points` are `\N` for all point-bearing curves (source has
  no CM data) — CM enrichment is Q9/T15. (4) All 317 points auto-load only after the
  T19→T20→T09→T08 chain generates their AL-quotient curve rows.

- 2026-08-01 (opus session): **[D20] DECIDED — full label.** See [DECISIONS.md](DECISIONS.md).
  `shimcurve_points.Clabel`/`curve_label` store the full `mu_label.coarse_label` label,
  matching `shimcurve_models.shimcurve` and `modcurve_points.curve_label`. **This ticket's
  staged files are already keyed that way, so there is nothing to re-key** — the frontend was
  the side that had to move, and it did (T24 commit `4b71e8d8d`, pushed). The PROVISIONAL
  banner still applies for the ordinary T27-reload reason ([D5]), not for keying.
  When T02's `shimcurve_modelmaps` eventually gets rows, stage `domain_label` on the full
  label too — T24 now queries it that way for consistency.
  **Ticket stays `review`**: [D19] (count conventions) and [D21] (the 9 coordinate-less
  curves) are unanswered.
