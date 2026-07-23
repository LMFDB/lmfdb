# T01 — Legacy model/point label grammar and old→new map

**Status: PROVISIONAL — pending T27 reload.** Owner: wave1-E-opus. Branch
`ticket/T01-legacy-label-map` (worktree `/Users/roed/claude/shim-wt/T01`).

Deliverables (this directory):
- `T01-label-map.csv` — every distinct legacy label → mapping (this report explains it).
- `T01-report.md` — this file.
- `t01_labels_intermediate.csv` — per-label decomposition + metadata (reproducible intermediate).

Reproducible scripts (committed in the worktree under `code/scripts/`):
- `t01_extract_labels.py` — robust label extraction from both files.
- `t01_make_magma_checks.py` + `t01_validate.m` + `t01_magma_checks.m` — genus cross-checks.
- `t01_build_map.py` — joins extraction ↔ devmirror to produce `T01-label-map.csv`.

---

## 1. The grammar (validated)

A legacy label is `D.M-[m1,…,mk]` and always matches `^\d+\.\d+-\[[0-9,]*\]$`.

**Decoding (Q1 DECIDED, now empirically confirmed):**

| token | meaning |
|-------|---------|
| `D` | quaternion discriminant `discB` |
| `M` | **Eichler level** (the "N" of Q1); the order is Eichler of level M, so `discO = D·M` |
| `[m1,…,mk]` | the Atkin–Lehner subgroup `H = ⟨w_{m1},…,w_{mk}⟩ ⊆ Aut_{±μ}(O)`; the `mᵢ` are the **Hall divisors** `m ‖ D·M` (i.e. `m | DM`, `gcd(m, DM/m)=1`) **with `w_m ∈ H`**, **listed as the full element set, including `m=1` for the identity** |

So `D.M-[m1,…]` = `X₀(D;M) / H`. Special cases: `[1]` = the trivial quotient =
`X₀(D;M)` itself; the complete Hall-divisor list = `X*(D;M)` (full AL quotient).

**The corresponding LMFDB row invariants are:**
`discB = D`, `discO = D·M`, `deg_mu = 1`, **congruence `level = 1`** (all the
level structure lives in the Eichler order; the congruence level is trivial).
The prefix is `D.M`, **not** `discB.discO` and **not** `order_label.deg_mu`.

This convention is the one fixed in code by `SignatureX0DNmodAtkinLehnerElement`
(`code/tables/signatures_single_AL_element_X0DN.m:186`, docstring: *"m || DN … The
m=1 case is allowed, corresponding to the trivial quotient X_0(D;N)"*). **No script
in either repo emits these `D.M-[…]` strings and no crosswalk file exists** — this map
is built from scratch.

### Worked structural confirmation
`H` ranges over the subgroups of the AL 2-group `(Z/2)^ω(DM)` (ω = #distinct primes
of `DM`), each listed by its Hall-divisor element set. For `DM = 66 = 2·3·11`
(ω=3) that is `2³ = 8`-element group with **16 subgroups**, and the models file has
**exactly 16** `6.11-[…]` labels; for `DM = 26 = 2·13` (ω=2) there are **5** subgroups
and **5** `26.1-[…]` labels. **42 of the 69 `(D,M)` families present a complete
subgroup lattice** (`#labels == #subgroups`); the other 27 are deliberately curated
subsets (e.g. only the base `[1]`, or only the top `X*` quotient). No family exceeds
its subgroup count except by a data error (§5).

---

## 2. Validation evidence

Two independent oracles, **zero contradictions across 250+ checks.**

### 2a. Combinatorial (subgroup-lattice) — `t01_extract_labels.py`
`#labels(D,M) == #subgroups((Z/2)^ω(DM))` for all 42 fully-present families;
every label's bracket is a set of Hall divisors of `DM` containing `1`
(the 4 exceptions are genuine data errors, §5).

### 2b. Genus — `t01_validate.m` (Magma, `AttachSpec("spec")`)
Three genus sources compared per label: the **model** (degree of the hyperelliptic
model ⇒ genus `g` for a degree-`2g+1/2g+2` model; the points file's **column 7**
independently stores this genus), the **devmirror** row genus, and the **Ogg /
Padurariu–Saia formula** (`SignatureX0DN` for bases, `SignatureX0DNmodAtkinLehnerElement`
for single-`w_m` quotients).

| check | formula source | PASS | FAIL | n/a |
|-------|----------------|-----:|-----:|----:|
| `[1]` base vs **devmirror** genus | `SignatureX0DN(D,M)` | **53** | 0 | 1 (15.4, no row) |
| `[1]` base vs **points-file** genus | `SignatureX0DN(D,M)` | **43** | 0 | 11 (model-only, no pt record) |
| `[1,m]` quotient vs **points-file** genus | `SignatureX0DNmodAtkinLehnerElement(D,M,m)` | **198** | 0 | 0 |

Representative rows (all agree):

| label | model | model g | points col7 | devmirror / formula g |
|-------|-------|--------:|------------:|----------------------:|
| `26.1-[1]` | `y²+`sextic | 2 | 2 | 2 (`26.1.1.2.2.a.1`) |
| `35.1-[1]` | `y²+`octic | 3 | 3 | 3 (`35.1.1.2.3.a.1`) |
| `74.1-[1]` | deg-10 | 4 | 4 | 4 (`74.1.1.2.4.a.1`) |
| `95.1-[1]` | deg-16 | 7 | 7 | 7 (`95.1.1.4.7.a.1`) |
| `119.1-[1]` | deg-20 | 9 | 9 | 9 (`119.1.1.2.9.a.1`) |
| `6.11-[1]` (Eichler M=11) | deg-8 | 3 | 3 | 3 (`6.66.1.1.2.3.a.1`) |
| `26.1-[1,2]` | plane cubic | 1 | 1 | 1 (Ogg) |
| `26.1-[1,26]` | `y²−xt` | 0 | 0 | 0 (Ogg) |
| `35.1-[1,5]` | `y²+`sextic | 2 | 2 | 2 (Ogg) |
| `6.11-[1,66]` (Eichler) | `y²−xt` | 0 | 0 | 0 (Ogg) |

Reproduce: `cd /Users/roed/claude/shim-wt/T01 && magma -b code/scripts/t01_validate.m`.

---

## 3. The map (`T01-label-map.csv`)

458 distinct labels (462 model records − 4 duplicate model reps; every one of the
424 points-file labels is also a model label). Each appears **exactly once**.

Because the shipped `gps_shimura_test` labels predate the T29 canonical sort and are
reassigned on reload (Q15.3), **`new_label` is provenance only.** The **durable key**
is `(join_discB, join_discO, join_deg_mu, join_level, join_al_subgroup)` — µ-independent
invariants that survive relabeling. `join_al_subgroup` is the sorted Hall-divisor
element set of `H` (identical to the legacy bracket, `1` included).

### Status tally

| status | count | meaning |
|--------|------:|---------|
| `MAPPED_PROVISIONAL` | **53** | `[1]` base label → its unique devmirror `X₀(D;M)` row (`new_label` set) |
| `UNMAPPED_PENDING_GENERATION` | **400** | proper AL quotient; no target row exists yet — see §4 |
| `UNMAPPED_GRAMMAR_VIOLATION` | **4** | AL component is not a Hall divisor of `DM` (data error, §5) |
| `UNMAPPED_NO_COARSE_ROW` | **1** | `15.4-[1]`: base `X₀(15;4)` (discO=60) absent (§5) |
| **total** | **458** | |

Per-discriminant breakdown is printed by `t01_build_map.py` and embedded per-row in the
CSV `notes`. The 53 mapped labels are the `[1]` bases of the 53 `(D,M)` families whose
`X₀(D;M)` coarse row exists on devmirror (all 54 `[1]` labels except `15.4-[1]`).

### Why the proper quotients are all UNMAPPED today
The only level-1 **enhanced AL-quotient** rows that currently exist are the **D=6
maximal-order** family (`discO=6`): 5 rows `6.1.1.{4,2,2,2,1}.0.*` = `X₀(6;1)` and its
AL quotients. **No legacy label targets them**, because the legacy D=6 data is entirely
**Eichler** (`6.5, 6.7, 6.11, …`, i.e. M ≥ 5, discO ≥ 30). Every proper quotient in the
files is therefore of an order whose level-1 enhanced rows are not generated yet
(blocked on the T19→T20→T09→T08 chain, per Q1.2 option (b)). Their join keys are fully
recorded so the crosswalk auto-completes once those rows land.

Per Q12.1 the future level-1 rows range over **all admissible squarefree deg µ**; the
classical AL-quotient models are the **deg µ = 1** members — hence `join_deg_mu = 1` in
every key.

---

## 4. How to re-run the join after T27 (turnkey recipe)

1. **Re-dump the coarse/base rows** from the reloaded table (renamed `gps_shimura`,
   Q12.3) into `devmirror_coarse.csv` (add `deg_mu=1 and level=1`):
   ```sql
   \copy (select "discB","discO",deg_mu,level,label,genus,index,coarse_index,
          coarse_label,name,"autmuO_norms",nu2,nu3,nu4,nu6,is_coarse,order_label
          from gps_shimura where deg_mu=1 and level=1) to 'devmirror_coarse.csv' csv header
   ```
   (psql flags used originally: `-P footer=off -F'|' -A`.)

2. **Re-map `[1]` bases** (unchanged logic): for each `MAPPED_PROVISIONAL` /
   `UNMAPPED_NO_COARSE_ROW` row, the base `X₀(D;M)` is the
   `(discB=join_discB, discO=join_discO, deg_mu=1, level=1)` row of **largest `index`**
   (equivalently `autmuO_norms` all `1`). Read its new `label` into `new_label`.

3. **Complete the proper quotients** (`UNMAPPED_PENDING_GENERATION`): once level-1
   enhanced rows for `discO=join_discO` exist, for each such row reconstruct **its** AL
   subgroup from `autmuO_norms` and match it to `join_al_subgroup`:
   - the AL group law on Hall divisors is `a · b = a·b / gcd(a,b)²`;
   - `H_row = ⟨ squarefree entries of autmuO_norms ⟩` under that law, written as the
     sorted set of Hall divisors (this is exactly the legacy bracket);
   - `MATCH when H_row == join_al_subgroup`; copy that row's `label` into `new_label`
     and flip status to `MAPPED_PROVISIONAL`.

   **This recipe is verified against the one family that already exists** (D=6 maximal,
   `discO=6`): `autmuO_norms` `{2,6,…}` → `⟨2,6⟩ = {1,2,3,6}` = `X*(6;1)` row
   `6.1.1.1.0.a.1`; `{6,…}`→`{1,6}`, `{3,…}`→`{1,3}`, `{2,…}`→`{1,2}`, `{1,…}`→`{1}`
   (base). So a hypothetical `6.1-[1,2,3,6]` would map to `6.1.1.1.0.a.1`, etc.

The proper-quotient branch of `code/scripts/t01_build_map.py` is where to wire step 3
(it currently emits the join key + this instruction in the `notes`).

---

## 5. Surprises / flags for David

1. **4 grammar-violating labels** — AL component is **not a Hall divisor** of `DM`.
   All four are in the `y²=quartic` model block and look like data-entry errors
   (some sit beside near-duplicate corrupted models, e.g. lines 458/459 share the
   tail `+4x³−19x²−4x−12`). **Not mapped** (no guessing):
   | label | bad comp. | Hall divisors of `DM` | plausible-but-unconfirmed intent |
   |-------|-----------|------------------------|----------------------------------|
   | `77.1-[1,17]` | 17 | {1,7,11,77} | `[1,7]`? |
   | `85.1-[1,2]` | 2 | {1,5,17,85} | `[1,5]`? |
   | `94.1-[1,89]` | 89 | {1,2,47,94} | spurious (94.1 already has its full family) |
   | `178.1-[1,30]` | 30 | {1,2,89,178} | corrupt |

2. **`15.4` family entirely unmappable (16 labels).** `M=4` is **non-squarefree**, so
   the coarse pipeline (which asserts `IsSquarefree(N)`) never produced `X₀(15;4)`
   (`discO=60`); devmirror has **no** row at `discO=60` (any deg_mu/level). The base is
   `UNMAPPED_NO_COARSE_ROW`; the 15 quotients are `PENDING`. If Eichler level 4 is in
   scope, the generator must be extended to non-squarefree M.

3. **4 duplicate model records** (same label, two model reps): `39.1-[1,13]`,
   `55.1-[1,5]`, `62.1-[1,2]`, `69.1-[1,3]` — each appears once as a
   plane/`P³` model in the main block and once as a `y²=quartic` in the quartic block.
   Flagged in the CSV (`model_dup_count=2`); T02 must pick one representative.

4. **D=6 maximal-order rows are orphaned by the legacy data.** The 5 existing enhanced
   `discO=6` rows (`X₀(6;1)` + AL quotients + `X*(6;1)`) have **no** legacy label,
   because the legacy D=6 curves are all Eichler (M ≥ 5). So the ticket's "D=6 special
   case" matching is exercised by **zero** labels — but it validated the §4 recipe.

5. **Coverage of the pending quotients depends on non-D=6 generation.** 400/458 labels
   (all proper quotients) map to rows that require the T19→T20→T09→T08 chain — none of
   which works today. This map is the crosswalk that will auto-complete when they do.

---

## 6. Parsing notes (multi-line records)

- **Models file** (`data/models/lmfdb_shim_models.txt`): pipe-delimited, **no header**;
  the equation field `{…}` may contain **literal newlines** (e.g. lines 56–57, 333–334),
  so records span physical lines and the column count per physical line is not fixed.
  Robust extraction: read the whole file, split on `|`, keep fields matching the label
  regex. A newline inside `{…}` stays inside the (ignored) equation field and never
  corrupts a label field — physical-line splitting would. (`t01_extract_labels.py`.)
- **Points file** (`data/rational points/lmfdb_shim_rational_pt_updated.txt`, note the
  space in the dir name): one record per physical line, **20 pipe columns**;
  col 3 = rational-point count (`0…10`/`infinite`), col 6 = coordinates
  (`{}`, `{[…],…}`, `[]`, or `NA`), **col 7 = genus**, **col 11 = M**, **col 12 = label**.
  All 424 rows parsed cleanly as 20-column records (no anomalies).
