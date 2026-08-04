---
id: T24
title: Frontend bug sweep (lmfdb repo, branch shimura_curves)
status: done
owner: wave1-F-opus
priority: P1
tier: 4
repos: [lmfdb]
depends_on: []
questions: []
---

## Context

Known defects in `~/claude/lmfdb/lmfdb/shimura_curves/` (branch `shimura_curves`; **active collaborator traffic — rebase before starting and keep the change list tight**):

1. **Sage download broken**: `main.py:560` calls `download_Shimura_curve(...)`; the method is `download_shimura_curve` (`main.py:540`). `/download_to_sage/<label>` 500s. Fix + add a test hitting all three download routes.
2. **Points column mismatch**: search code uses `Elabel` (`main.py:909`), curve page uses `Clabel` (`web_curve.py:780,847-848,865-866`). Resolve to whatever `shimcurve_points` actually has (coordinate with T03; devmirror `\d shimcurve_points` is authoritative).
3. **Copied test asserts modular-curve content**: `test_shimura_curves.py:12` checks for `X_0(N)` — rewrite the test to assert real Shimura content (e.g. homepage loads, a known curve page contains its label and "Shimura").
4. **Leftover modcurve knowls/wording**: `shimcurve.html:369` (`modcurve.fiber_product` + "realize this modular curve as a fiber product"), `shimcurve.html:407` (`modcurve.modular_cover`), magma-download comment `main.py:502`. Point at `shimcurve.*` knowls (T26 creates them; referencing a not-yet-existing knowl renders as a broken-knowl link, acceptable on beta) and fix wording.
5. **Stats count workaround**: `main.py:1059-1062` counts `{'discB': {'$gt': 0}}` with comment "For some reason counting the empty query returns 0 ?" — root-cause it (likely the stats/counts table for `gps_shimura_test` is stale on the DB, `gps_shimura_test_counts` rows; check `db.gps_shimura_test.stats.total`) and either fix properly or document why the workaround stays.
6. **Dead code**: `url_for_RZB_label`/`url_for_CP_label` (`main.py:224-227`) + the `CP_LABEL_GENUS_RE` import (`main.py:56`), unused `FINE_LABEL_RE` (`main.py:61`), duplicate unused `shimcurve_link` (`main.py:120-124`, hardcodes a stray level≤70 cutoff), unused `web_curve.py` methods (`full_torsion_field_degree:573`, `newform_level:734`, `old_db_nf_points:877-895` and its `ec_nfcurves` import). Delete.
7. **Commented-out feature blocks** — do NOT delete, they're staged features: CM-points search (`main.py:293,304,615-627,798-807,860,873-874`), rational/non-rational points sections (`shimcurve.html:185-240`), low-degree-points link (`shimcurve_browse.html:49-53`), `points_type` noncm option (`main.py:607-608,818`), `factor` search box (`main.py:768-773`). Add a single `# STAGED: enable when <table/column> is populated (see shimcurve_tickets T03/T15)` marker on each so their purpose is discoverable.
8. **`contains_negative_one` vs `is_coarse`**: commented template block at `shimcurve.html:223-227` references the old column name; reconcile with T11's outcome.

## Steps

1. `git -C ~/claude/lmfdb checkout shimura_curves && git pull` (note upstream drift in the Log); branch `ticket/T24`.
2. Fix items 1-6, marker-pass item 7-8. Keep each item its own commit for reviewability.
3. Test: `cd ~/claude/lmfdb && sage -python -m pytest lmfdb/shimura_curves/ -x` plus a manual pass on a running dev server (`sage -python start-lmfdb.py --debug`): homepage, search with results, one curve page per kind (level-1, level-structure, Eichler `X(D,M;1)`), all three downloads, random, stats, diagram page.
4. List the verification evidence in the Log. Leave the branch local; David pushes/PRs.

## Acceptance criteria

- All 8 items addressed with per-item commits; pytest green; manual checklist in the Log with no 500s.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (orchestrator, post-review note from T03): T03's staging found a further
  frontend inconsistency IN SCOPE for this ticket's review: the curve-page/search
  points queries filter `shimcurve_points.Clabel` by the **bare `self.coarse_label`**,
  while T03 keyed staged `Clabel` values on the **full label** (`mu_label.coarse_label`
  form) to match the rest of the schema. One side must change; which key
  `shimcurve_points.Clabel` uses is a data-convention call for David (see T03's Log,
  "curve_label keying" flag). Not fixed in the T24 branch — surfacing here so the
  review of T24+T03 decides it coherently.
- 2026-07-22 (wave1-F-opus): worked in worktree `/Users/roed/claude/lmfdb-wt/T24`,
  branch `ticket/T24-frontend`, base `dfe40d0fe` (local `shimura_curves`). Branch
  left local; not pushed.

  **Drift check (no pull/merge, per instructions):** `git fetch origin` (read-only).
  Branch `shimura_curves` is hosted on `origin` (roed-math) and `eran` (assaferan).
  No upstream drift: base `dfe40d0fe` is exactly one local-only tickets commit ahead
  of both `origin/shimura_curves` (`0941c356e`) and `eran/shimura_curves`
  (`136b481eb`); both are ancestors of HEAD. Nothing to merge. All work based on the
  local state.

  **Root causes / fixes (one commit per item):**
  - **Item 1** (`1dd7a0fca` + `5a4c9f011`): `/download_to_sage` called
    `download_Shimura_curve` (capital S) — nonexistent → 500. Fixed the name. Added a
    3-route download regression test. That test surfaced two *further* pre-existing
    500s in the shared magma/sage builder `download_shimura_curve_magma_str`:
    (a) `rec['factorization']` KeyError — **`gps_shimura_test` has no `factorization`
    column** (on the curve page the analogous `self.factorization` is silently
    swallowed by Jinja; the pure-Python download is not) → `rec.get('factorization')
    or []`; (b) `db.shimcurve_modelmaps.search(...)` — **that table does not exist yet**
    → guarded with `"shimcurve_modelmaps" in db.tablenames`. All three routes now 200.
  - **Item 2** (`0e4a74f23` + `dc64d2f35`): point search used `Elabel`; authoritative
    `\d shimcurve_points` (devmirror) has **`Clabel`, no `Elabel`** (web_curve.py
    already uses `Clabel`) → aligned the search column to `Clabel`. Same class of bug
    found on the checklist: `?cusp=no` 500'd because `parse_bool(...,"cusp")` validates
    against a **`cusp` column that shimcurve_points lacks** (Shimura curves are compact)
    → removed the cusp parse.
  - **Item 3** (`871ae8ecb`): `test_home` asserted `X_0(N)` (modcurve boilerplate that
    never appears here). Rewrote to assert Shimura content (`abelian surfaces`,
    `X(D;1)`) + added `test_curve_page` (label + "Shimura curve").
  - **Item 4** (`94647654d`): `modcurve.fiber_product`→`shimcurve.fiber_product`,
    `modcurve.modular_cover`→`shimcurve.modular_cover`, "this modular curve"→"this
    Shimura curve" (shimcurve.html), and magma-download "to a modular curve isomorphic
    to P^1"→"...Shimura curve..." (main.py). The `shimcurve.*` knowls are T26's; they
    render as broken-knowl links until then (acceptable on beta).
  - **Item 5** (`fc3781fdb`): `count({})` returns the cached unconstrained *total* stat;
    it had been recorded as 0 (stats computed against a stale/empty table), hence the
    `{'discB':{'$gt':0}}` workaround. On the current devmirror that stale stat is absent,
    so `count()` falls through to a live COUNT and returns the correct **2587** (verified
    via `db.gps_shimura_test.count()`, `.stats.total`, and the rendered homepage
    "$2{,}587$"). Replaced with plain `count()`, matching the sibling
    `gps_gl2zhat_fine.count()`. A proper reload (T27) regenerates the stat.
  - **Item 6** (`ee58b67e6`): deleted dead `url_for_RZB_label`, `url_for_CP_label`, the
    `CP_LABEL_GENUS_RE` import, unused `FINE_LABEL_RE`, the duplicate `shimcurve_link`
    (main.py); unused `full_torsion_field_degree`, `newform_level`, `old_db_nf_points`
    (web_curve.py) + the now-orphaned `prod`/`euler_phi`/`integer_prime_divisors`
    imports. `py_compile` + `pyflakes` clean (no unused imports).
  - **Item 7** (`d7e21b482`): marker pass only — 12 `# STAGED: ...` markers on the
    commented CM-points column/db_cols/query/search-box + staged UI array rows, the
    `points_type` noncm option, the factor/fiber-product box (main.py), and the rational
    / non-rational point sections (shimcurve.html) and low-degree link (browse). Nothing
    enabled or deleted.
  - **Item 8** (`76fb854a6`): staged non-rational block referenced the modcurve column
    `contains_negative_one`; the Shimura equivalent is `is_coarse` (is_coarse ⇔ −1∈H,
    QUESTIONS_ANSWERS Q5), so `not contains_negative_one`→`not is_coarse`. Block stays
    STAGED (item 7 marker). T11 owns −1/is_coarse and can revisit on enable.
  - **Item 9** (no code change): the `show_genus` `aut_gerbiness` factor was **already
    present at base** (commit `560c20a89`, ancestor of `dfe40d0fe`), not dropped. Verified
    on aut_gerbiness=3 curves — see note added to **T06 Log** (2026-07-22). T06 status
    unchanged.

  **Verification.** `sage -python -m pytest lmfdb/shimura_curves/ -q` → **3 passed**
  (test_home, test_download, test_curve_page), 39s. Manual curl checklist on the
  `--debug -p 37778` server (all 200 unless noted):
  homepage 200; search `?genus=0&discB=6` 200, `?family=XDstar` 200; level-1
  `10.1.1.4.0.a.1` 200; level-structure `6.1.2.12.0.a.1` 200; Eichler `X(10,11;1)`
  `10.110.1.1.2.5.a.1` 200; deg μ>1 `6.2.1.1.0.a.1` 200; downloads magma/sage/text 200
  (also magma on the Eichler curve 200); random 200; stats 200; diagram 200;
  low_degree_points `?cusp=no` 200 (was 500), `?degree=2-4` 200. Item 9 genus row and
  item 5 total confirmed in the rendered HTML.

  **The one remaining 500 is NOT a shimura bug and NOT introduced here:**
  `/ShimuraCurve/data/<label>` 500s with `AttributeError: 'LMFDBSearchTable' object has
  no attribute 'extra_cols'` in `lmfdb/api/api.py:422` (`datapage`). This is a global
  env/psycodict issue on this machine — the control `/EllipticCurve/Q/data/11.a2` 500s
  identically. `shimcurve_data` is untouched by T24. **Flag for T25/T27** (or an
  infra/psycodict bump), not this ticket.

  **Discovered, logged here for other tickets:**
  - `gps_shimura_test` has **no `factorization` column**, yet main.py (jump fiber
    products, `parse_element_of factor`) and web_curve.py (`self.factorization`,
    `fiber_product_of`) reference it. On the curve page Jinja masks it; elsewhere it will
    error. **T27/T02**: decide whether to add the column or drop these references.
  - Tables **`shimcurve_modelmaps` and `shimcurve_teximages` do not exist** on devmirror
    (only `shimcurve_models` (1 row), `shimcurve_points` (0), `shimcurve_pictures` (304)).
    web_curve.py's `modelmaps_to_display`/`nearby_lattice` hit these; masked by Jinja on
    the page but a latent 500 for any pure-Python consumer. **T02** creates them.
  - The staged low-degree-points UI still emits `cusp=...` params (browse link +
    web_curve descriptions); now harmless no-ops after the item-2 cusp removal. **T03**
    can drop them when it enables the section.
  - Pre-existing pyflakes nit unrelated to T24: `web_curve.py` `rational_points_description`
    has an f-string with no placeholders (`fr'Local obstructions ... not known.'`). Left
    as-is (out of scope).

  **Status → review.** 10 local commits on `ticket/T24-frontend` (base `dfe40d0fe`),
  newest first: `dc64d2f35` (item2 cont/cusp), `5a4c9f011` (item1 cont/download robust),
  `76fb854a6` (item8), `d7e21b482` (item7), `ee58b67e6` (item6), `fc3781fdb` (item5),
  `94647654d` (item4), `871ae8ecb` (item3), `0e4a74f23` (item2), `1dd7a0fca` (item1).
  David reviews/pushes.

- 2026-08-01 (opus session): **APPROVED + PUSHED → status: done.** David's verdicts
  [D25](DECISIONS.md) (approve + push), [D20](DECISIONS.md) (full-label keying) and
  [D26](DECISIONS.md) (add the `factorization` column). Two follow-ups landed on the branch
  before pushing, then `ticket/T24-frontend` was pushed to `origin` (roed-math/lmfdb).
  **No PR opened** — D25 authorized the push only; GitHub's PR link is
  https://github.com/roed-math/lmfdb/pull/new/ticket/T24-frontend when you want it.

  **Merge with current `shimura_curves` (packet §8 step 3):** done first — commit `07a2354bd`.
  This also fixed the branch's test collection, which had been failing on
  `AttributeError: 'LMFDBDatabase' object has no attribute 'can_read_write_userdb'`: the
  branch predated the main merge (`5c2fbc140`) that brought the psycodict-1.0/psycopg3
  compatibility work (#7070–#7072). Not a T24 bug — it was the venv/checkout mismatch
  recorded in project memory.

  **D20 follow-up — commit `4b71e8d8d`.** The `coarse_label` *column* holds only the
  `level.index.genus.class.num` suffix, while D20 rules that the curve-keyed tables store the
  **full** `mu_label.coarse_label` label. The frontend was querying with the bare column, so
  every such query would have silently missed once T03's points load. Introduced one
  `full_coarse_label` attribute and routed through it: `shimcurve_points` (4 sites),
  `shimcurve_modelmaps` (2), the coarse link in `coarse_description`, and the two
  `shimcurve_models` sites that had been rebuilding the label inline with a shadowing local.
  **Two further latent bugs of the same family, found and fixed here:**
  - `quadratic_refinements` searched `{'coarse_label': self.label}` — suffix column vs full
    label; now matches on `(mu_label, coarse_label)`.
  - `shimcurve_data`'s `label == coarse_label` test **could never be true**, so
    `/ShimuraCurve/data/<label>` always took the else branch and handed `datapage` a bogus
    suffix label. Confirmed on devmirror: **0 of 2587** rows satisfy the old comparison, while
    `mu_label + "." + coarse_label == label` on **2587/2587**.

  **D26:** the `factorization` references stay (the column is being added, not stripped). The
  existing defensive `rec.get('factorization') or []` guard is forward-compatible — it will
  emit the factors as soon as the column is populated. The schema half landed in ShimCurve;
  see T04's Log.

  **Verification.** `pytest lmfdb/shimura_curves/` → 3 passed. Dev server on :37778, **16
  routes curled 200** (homepage, coarse / Eichler / deg-μ>1 curve pages, all three downloads,
  diagram, stats, random, `covered_by` search, low-degree points, both `/data/` pages,
  Completeness, Labels) with **zero server errors** in the log. `/ShimuraCurve/data/<label>`
  now returns **200** and renders a real datapage — the environment 500 this ticket flagged
  as "not Shimura's" is gone after the main merge. The single `shimcurve_models` row still
  renders on X(6;1), confirming the refactored models query resolves. pyflakes clean.

  **Note for T02/T03 when they load data:** `shimcurve_modelmaps.domain_label` is now queried
  with the full label too, for consistency with `shimcurve_models.shimcurve`. The table is
  still empty (created by T02), so nothing to migrate — but stage it keyed on the full label.
