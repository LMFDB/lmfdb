---
id: T04
title: Unify the two table writers on one canonical schema
status: review
owner: wave2-I-fable
priority: P0
tier: 0
repos: [ShimCurve]
depends_on: []
questions: []
---

## Context

Two writers emit rows for the same postgres table (`gps_shimura_test`) with **incompatible layouts**:

- `WriteHeaderAndSubgroupsDataToFile` / `WriteHeaderToFile` / `WriteSubgroupsDataToFile` (`code/level-structure/enumerate-H.m:498-618`; canonical list `GPS_SHIMURA_FIELDS` at `:427-496`): **68 columns**, `?`-separated. Asserts 68 fields per row (`:614`).
- `X0DNdata` (`code/tables/tablesX0DN.m:30-31`): **70 columns**, `|`-separated — adds `level_is_prime`, `level_is_prime_power`, and places `aut_gerbiness` at a different position.

The devmirror table has all 70 columns, so the canonical schema is the 70-column superset. Keeping two hand-maintained column lists is how the mismatch happened; they were merged into the DB manually.

## Task

Single source of truth for the schema; both writers emit identical headers and compatible rows.

## Steps

1. Create one Magma constant (e.g. `GPS_SHIMURA_FIELDS` moved to `code/utils/schema.m`, added to `spec`) holding the ordered 70 `<name, postgres-type>` pairs — order matching the current devmirror `gps_shimura_test` column order (pull with `\d gps_shimura_test`; exclude `id`).
2. Make `WriteHeaderToFile`/`WriteSubgroupsDataToFile` consume it: add the two missing columns (`level_is_prime := IsPrime(level)`, `level_is_prime_power := IsPrimePower(level)` — match how `tablesX0DN.m` computes them, note level 1 edge case) and replace the `assert nf eq 68` with the list length.
3. Make `tablesX0DN.m` consume the same constant. Decide one separator for both (recommend `|`, since `?` appears inside no field but `|` matches the larger existing corpus — actually **check both corpora for separator collisions first** and record the finding in the Log; psycodict `copy_from` accepts any sep).
4. Keep a regeneration escape hatch: writers should take the field list from the constant so future column additions happen in exactly one place. Add a comment in the constant pointing at `lmfdb-data-guide.txt` and this ticket.
5. Regenerate one small file of each kind and diff against the old ones column-by-column (`genera-D6-deg1-N1.m` — 5 rows, fast: the README driver with `deg=1, N=1`; and a tiny X0DN run, e.g. `X0DNdata(30, 1)` variant) to prove only the intended layout changed, not values. **Do not regenerate the full corpus in this ticket** (Tier-1 fixes will force regeneration anyway).
6. Run `tests/run_quick.m`; update `tests/data_roundtrip.m` expectations if the header layout is what it checks (see T05 — coordinate if both in flight).

## Acceptance criteria

- Exactly one ordered column list exists in the codebase; both writers reference it.
- Sample regenerated files: identical values to the old files modulo the two added columns and separator; documented diff in the Log.
- `tests/run_quick.m` passes.

## Key files

- `code/level-structure/enumerate-H.m:427-496` (field list), `:498-618` (writers)
- `code/tables/tablesX0DN.m:30-31` (header), `:110-112` (driver caps)
- `code/utils/lmfdb-data-guide.txt` (upload recipe to keep in sync)

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-I-fable): **DONE → review.** Branch `ticket/T04-unify-writers` (worktree tier1core, stacked on T09 → T07 → T10 → T29 → T28), commits `2d6ceb3` (schema + writers + diff-evidence samples) and `37ee1a5` (sample restore + data-guide note).

  **Canonical schema — 71 columns, NOT the ticket's 70 (T25/T27 coordination).** The ticket predates T07, which added `base_gerbiness integer` to both writers (69-col `?` / 71-col `|`). The unified canonical schema is therefore the devmirror 70 columns (pulled with `\d gps_shimura_test` 2026-07-22, excluding `id`) **plus `base_gerbiness`, inserted between `bad_primes` and `cm_discriminants`** (the position T07 established — same spot in both alphabetical and devmirror order). **The live DB does not have `base_gerbiness` until T27**: `db.gps_shimura_test.add_column("base_gerbiness", "integer")` before the reload. This delta is documented prominently in schema.m's header comment and in lmfdb-data-guide.txt.
  - Implementation: new **`code/utils/schema.m`** (added to `spec`): `GpsShimuraSchema()` (ordered `<name, postgres-type>` pairs — intrinsic, not a top-level constant, because Magma package-file variables are file-scoped), `GpsShimuraColumns/Types/Separator`, `WriteGpsShimuraHeader(file)`, `GpsShimuraRow(assoc)`. `GpsShimuraRow` **requires the key set to equal the column set** (missing OR unknown columns fail loudly) — no writer asserts a literal column count anywhere any more.
  - Column order = devmirror physical order ⟹ `label` is column 41, not 1: `update_from_file` calls need `label_col="label"`; `copy_from` reads the header. Recorded in schema.m + guide.

  **Separator decision (ticket step 3): `|`.** Collision scan of both corpora: **zero `|` characters in all 17 `?`-separated genera-D6 files, zero `?` characters in the 2 `|`-separated SignatureTableX0DN files** — both candidates were safe; `|` wins (larger existing corpus + psycodict's default sep, so load commands need no `sep` argument).

  **Writer changes:**
  - `enumerate-H.m`: hand-maintained `GPS_SHIMURA_FIELDS` (69 entries, label-first-alphabetical) and `assert nf eq 69` deleted; `WriteHeaderToFile` delegates to `WriteGpsShimuraHeader`; `WriteSubgroupsDataToFile` keeps its name-keyed assoc and now also fills **`level_is_prime` := IsPrime(level)** and **`level_is_prime_power` := (level > 1 and IsPrimePower(level))** — computed exactly as tablesX0DN does (level 1 ⟹ F/F).
  - `tablesX0DN.m`: hand-maintained 71-col header strings and the 71-arg positional Sprintf replaced by assoc + `GpsShimuraRow` (also fixes a latent format-string footgun: rows were passed to fprintf AS the format). **Bug found & fixed:** the resume logic hardcoded `parts[40]` as mu_label — T07's base_gerbiness insertion had silently shifted mu_label to 41, so resume dedup was dead (collected `models`≡`\N`); now schema-derived (`Index(cols,"mu_label")`), plus a **stale-header guard**: resuming onto a file whose header ≠ canonical errors out instead of appending mixed-layout rows.
  - `tablesX0DN.m:119` cmfdata path (T13 handoff, merge-safe version): `cmfdatafile := "./code/jacobian_decomp/cmfdata.txt"` → `cmfdatafile := DataFile("cmfdata/cmfdata.txt")` keeping the explicit arg and `levelbound:=D*N`; **post-T13-merge the explicit cmfdatafile arg can drop entirely** (T13 makes that path CMFLoad's default). Worktree runs use a gitignored symlink `data/cmfdata/cmfdata.txt` → the T13 worktree's materialized 46.5 MB dump.
  - Encoding normalization: `GpsShimuraRow` converts raw BoolElts to `T`/`F`. The old `|`-writer printed `simple` (a BoolElt from JLDecomposition) via `%o`, leaking **`true`/`false`** into the corpus (postgres happens to accept those spellings; repo convention is T/F). Deliberate, semantics-preserving encoding change, visible in the diff below.

  **Verification (ticket step 5) — one small file of each kind, field-mapped old-vs-new diff (script in session scratchpad):**
  - `genera-D6-deg1-N1` (5 rows): 69 common columns **identical on every row**; only changes = separator `?`→`|`, order → devmirror, + `level_is_prime`/`level_is_prime_power` (both `F`, level 1). CLEAN.
  - `genera-D6-deg1-N3` (36 rows): identical except the two documented per-process churn fields (`generators` 29 rows, `ram_data_elts` 11 rows — presentation-dependent, T29/T10 known issue, reproduced by identical-code reruns); new columns `T`/`T` (level 3; note both are T for a prime — matches devmirror's populated rows). CLEAN.
  - `X0DNdata(30,5)` (11 rows, new file vs the committed `SignatureTableX0DN_400_400.txt`): joined on **invariant keys (discB, discO, level, deg_mu) 11/11**; all common columns identical except (a) `simple` `true/false`→`T/F` (the encoding fix, 11 rows), (b) the **label family (`label`, `mu_label`, `order_label`, `psl2label`) — PRE-EXISTING code-vs-corpus grammar drift, not T04**: the committed corpus has old-grammar `order_label = "D.N"` (e.g. `6.5.1`) while the code at my base (97bef4f, T29) already writes `"discB.discO"` (`6.30.1`, the Q1.3 convention). One more reason shipped labels are unreproducible until T27. New column `base_gerbiness` = 2 = 2·gerbiness on all 11 rows (T07 relation). CLEAN.
  - `tests/run_quick.m` **green (0 failures, 0 skips)**. `tests/data_roundtrip.m` needed **no** expectation change: it tests the *legacy* 9-field reader `GeneraTableToRecords` on a synthetic fixture, not the 71-col layout.
  - Sample files then **restored to the committed layout** (`37ee1a5`): keeping 2 of 17 corpus files in the new layout would leave `data/genera-tables` mixed; the corpus moves wholesale at the Tier-1 regeneration wave. New-layout evidence preserved in commit `2d6ceb3` and scratchpad.

  **Notes for T05** (not in flight): the legacy pair — `GeneraTableToRecords`/`LineToRecord` (`read-write.m`) and the legacy 9-field writer inside `EnumerateH(write:=true)` (`enumerate-H.m` ~:830) — still speak the old `?`-format and don't read the postgres-copy files at all; after the corpus regenerates in the unified layout, T05 should port or retire them and add a true roundtrip test against `WriteGpsShimuraHeader`/`GpsShimuraRow` (parse header from schema, not fixtures).

  **Data-quality flag for T27:** devmirror has **71 coarse level-1 rows with `level_is_prime = t`** (discB 6..39 — the oldest batch; 1 is not prime) vs 268 with `f` — junk from an older loader, self-heals at the T27 reload since both unified writers now emit F at level 1.
