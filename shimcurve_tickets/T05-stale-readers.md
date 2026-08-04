---
id: T05
title: Fix or remove stale readers; update README data section and roundtrip test
status: review
owner: wave3-M-opus
priority: P1
tier: 0
repos: [ShimCurve]
depends_on: [T04]
questions: []
---

## Context

Three things still speak the **legacy** `EnumerateH` output format (9 columns, `QuaternionAlgebra<...>` preamble, rows containing `<...>` tuples), which the current pipeline no longer writes:

1. `code/utils/read-write.m` — `LineToRecord` (`:2`) and `GeneraTableToRecords` (`:41`) only accept lines containing `<`; on current 68/70-column files they silently skip **every** data row.
2. `code/upload_scripts/shimcurve_generate.py` — parses the legacy preamble (`:26-57`), plus two open TODOs (`:19` coarse/fine, `:22` ram_data_elts). The current files are direct `copy_from`-ready, so this script's role is gone.
3. `README.md` "## Data" section (~lines 246-270) — documents the legacy format, contradicting the "# Data for LMFDB" section above it.

Also `tests/data_roundtrip.m` writes a synthetic **legacy** fixture and tests the legacy reader — it passes while testing the wrong thing.

Downstream consumers of `GeneraTableToRecords` exist (`qm-mazur/ICERM-code-demo.m:2`, `qm-mazur/utils-qm-mazur.m` `read_data`) — the Magma reader is genuinely useful for research scripts and should be **fixed, not deleted**.

## Steps

1. Rewrite `GeneraTableToRecords`/`LineToRecord` to parse the canonical format from T04: read the 3-line header, map column names → record fields, split rows on the canonical separator, decode `{...}` sequences / `T`/`F` / `\N`, and decode `generators` (8·k integer lists → pairs of O-elements) and `ram_data_elts` (Lehmer ranks via `DecodePerm`, `code/level-structure/lehmer.m:8`). Return records compatible with what `ICERM-code-demo.m` expects (check its usage and adapt either side).
2. Rewrite `tests/data_roundtrip.m`: generate a tiny real dataset (D=6, deg 1, N=1 → 5 rows) via the actual writer into a temp path, read it back with the new reader, assert genus/index/torsion of a known row (`X(6;1)`: genus 0, fuchsian_index 1 — verify against `data/genera-tables/genera-D6-deg1-N1.m` before hardcoding). Keep it deterministic and under ~2 min.
3. Delete `code/upload_scripts/shimcurve_generate.py` (git preserves it) and replace with `code/upload_scripts/README.md` documenting the actual load path:
   ```python
   from lmfdb import db
   db.gps_shimura_test.update_from_file('data/genera-tables/<file>', sep='?')   # or copy_from for fresh tables
   ```
   copying the fuller recipe from `code/utils/lmfdb-data-guide.txt:36-80` and `data/quaternion-orders/make-table.m`.
4. Rewrite README "## Data" to describe the current 70-column format (reference the T04 schema constant), and remove the legacy example.
5. `tests/run_quick.m` green.

## Acceptance criteria

- `GeneraTableToRecords` on `data/genera-tables/genera-D6-deg1-N2.m` returns 28 records with correct genus values (spot-check 2 against the file).
- `qm-mazur/ICERM-code-demo.m`'s read step works (run just its first lines) or its call site is updated in the same commit.
- No code in the repo parses the legacy format; README sections agree with each other.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave3-M-opus): **DONE → review.** Branch `ticket/T05-stale-readers` (worktree tier1core, on T15 @ 975b2df, which stacks T04→T09→T07→T10→T29→T28). Commits `ba1f82c` (reader), `e35ca31` (roundtrip test), `cbd6b43` (upload README), `98b0bef` (README `## Data` + ICERM), `48c9f0c` (remove write-to-latex.m).

  **Reader (`code/utils/read-write.m`) — header-driven, per T04 reality.** `GeneraTableToRecords`/`LineToRecord` rewritten; new engine `ReadGeneraTableFile(filename : O, sort)`. Parses the 3-line header, **auto-detects the separator** (picks whichever of `|`/`?` occurs most in the names line — so it reads BOTH the current 69-col `?` corpus AND fresh 71-col `|` writer output with no code change), maps column names → record fields, validates names against `GpsShimuraColumns()`. Custom `splitKeepEmpty` splits on a single sep **preserving empty fields** (Magma's builtin `Split` drops them → would misalign rows). Decodes `{...}` arrays (incl. nested `generators`), `T/F`, `\N` (→ field unset). `generators` (nested 8-int blocks) → **pairs of O-elements** `<O!coords[1..4], O!coords[5..8]>` (O supplied, else derived as `MaximalOrder(QuaternionAlgebra(discB))` when discO=discB); `ram_data_elts` (Lehmer ranks) → **permutations via `DecodePerm(rank, fuchsian_index)`** — verified the perm degree is exactly `fuchsian_index`, the product is `Id`, and `EncodePerm` inverts the stored ranks on every N1 row. Each record carries the full column→value map in `` s`data `` plus ergonomic named fields and the legacy aliases (`fuchsindex`, `torsioninvariants`, `endogroup`, `AutmuOnorms=Set(autmuO_norms)`, `Hsplit`, `ramification_data`).

  **qm-mazur compatibility.** The only downstream references to `GeneraTableToRecords` are the `ICERM-code-demo.m:2` doc-comment and a commented line in `disc6-[2,2].m:44` — **no live callers** (utils-qm-mazur.m `read_data` is an unrelated Igusa/defining-eqn reader, untouched). Updated the ICERM comment: its old read call used `endogroup:=" C2 "` (never matches the new `galEnd` labels like `4.2`) and `[1]` of a 9-row result; now a uniquely-identifying filter → `6.1.4.12.0.a.1`, with current field names + decodings.

  **Roundtrip test (`tests/data_roundtrip.m`).** (1) Generate D=6 deg1 N1 with the **actual 71-col `|` writer** into a gitignored `tmp/` path (≈1 s), read back, assert X(6;1)=`6.1.1.1.0.a.1` genus 0 / fuchsian_index 1 / index 1 / trivial torsion / split, generators decode to O-element pairs, and ram-rank↔perm inverse with product Id on all 5 rows. Fresh generation reproduces the committed N1 labels exactly (canonical sort is deterministic here). (2) Read-only pass over the committed **69-col `?`** `genera-D6-deg1-N2.m` → 28 records, genus spot-checks (`6.1.2.3.0.a.1`=0, `6.1.2.48.3.a.1`=3), genus filter → 16. Added `tmp/` to `.gitignore`.

  **Upload path (`code/upload_scripts/`).** Deleted `shimcurve_generate.py` (parsed the retired EnumerateH text format; had the two open TODOs); replaced with `README.md` documenting the real load path — schema.m as column source of truth, **per-file separator** (`|` fresh / `?` corpus), `copy_from` vs `update_from_file(label_col="label")` (label is column 41), the `base_gerbiness` `add_column` and the T27 label-reload caveat.

  **README `## Data`.** Rewritten to describe the postgres-copy layout (references `GpsShimuraSchema`), explicitly notes the corpus is still 69-col `?` pending the reconciled regeneration (not papered over), documents reading via `GeneraTableToRecords`/`ReadGeneraTableFile` with an accurate example, and removes the legacy 9-column example — now consistent with `# Data for LMFDB`.

  **FLAG — extra legacy parser removed (not in the ticket's enumerated 3).** `code/utils/write-to-latex.m` positionally parsed the legacy 9-col `?` layout (and skipped a 6-line preamble via `count ge 7`), so it was fully broken against the current corpus; it is **not in `spec`, never loaded, unreferenced**, and carried pre-existing bugs (misaligned `tors_latex`; stale `split` var). Removed to satisfy "no code parses the legacy format" (git-preserved). It generated a LaTeX paper table; **if still wanted, reimplement on `GeneraTableToRecords`** — the open item is the `galEnd` group-label → TeX-name mapping (a T18/T26 presentation convention), which is why it was deleted rather than ported here.

  **Acceptance:** all met. `GeneraTableToRecords` on genera-D6-deg1-N2 → 28 records, genus spot-checks pass; ICERM read step updated + runnable; no legacy-format parser remains; README sections agree. `tests/run_quick.m` **green (0 failures, 0 skips)** — T19 smoke, T29 determinism, T09 autmuO, roundtrip, T15 points/obstructions all pass.
