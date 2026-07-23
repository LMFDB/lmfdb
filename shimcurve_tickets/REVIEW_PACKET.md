# Shimura Curve Swarm — Review Packet

*Assembled 2026-07-22 for David. Covers the 10 tickets in `status: review`: T28, T29, T10, T07, T09, T01, T02, T03, T13, T24. In-flight tickets (T04, T08, T19, T30) are NOT in this packet — they'll get their own when they land.*

Every decision below is numbered **D1–D26** so you can respond compactly ("D7 approved, D20: full label, D14: drop them"). Each has: **Context** (why this exists), **What was done**, **Evidence**, and **Your call** (what approving means). FYI items need no response unless you disagree.

**Decision types:**
- 🔴 **semantic sign-off** — changes what a column/label *means*; affects shipped or future data
- 🟡 **convention call** — several defensible options; someone must pick
- 🟢 **approve work** — review the diff, confirm the approach
- ⚪ **FYI** — awareness only

---

## Recommended review order

The branches are **stacked**, so review in stack order — each section's diff command shows only that ticket's changes:

1. **Foundation**: T28 → T29 (labels; gates everything)
2. **Tier-1 stack**: T10 → T07 → T09 (one branch chain, worktree `tier1core`)
3. **Legacy-data stack**: T01 → T02 → T03
4. **Standalone**: T13 (ShimCurve), T24 (lmfdb)

**If you only have an hour**: D3, D4, D5 (label semantics + reload strategy — everything else rides on these), D7 (gerbiness), D20 (Clabel keying — blocks T03/T24 coherence), D25 (T24 push), and skim the Decision index.

---

## Decision index

| # | Ticket | Type | One-liner |
|---|--------|------|-----------|
| D1 | T28 | 🟢 | Repo-root path convention (mechanical) |
| D2 | T29 | 🟢 | Canonical label sort implements Q15's design |
| D3 | T29 | 🔴 | `is_split` redefined: "some conjugate splits" |
| D4 | T29 | 🔴 | `G1` := kernel of reduced-norm hom (psl2label changes on 98% of rows) |
| D5 | T29 | 🔴 | T27 reload = full atomic `copy_from`; re-key the 304 pictures (= Q15.3 sign-off) |
| D6 | T10 | 🟢 | `[G:G1plus]` assert: 2 → φ(N); closes Q4's ⟐ |
| D7 | T07 | 🔴 | `gerbiness` := #ker(f); old value → `base_gerbiness`; schema 68→69 cols |
| D8 | T07 | 🟡 | Kept the `aut_mu_O.m:66` injectivity assert (deviation from Q2.4) — Eran confirms |
| D9 | T07 | 🟡 | `Gerby_gen` convention: primitive integral `Eltseq(B!·)` (Q2.3's ⟐) |
| D10 | T07 | 🟡 | "gerbiness=1 ⟸ deg μ=1" asserted for maximal orders only — Eran confirms scope |
| D11 | T07 | 🟢 | Post the drafted closing comment on upstream issue #6 |
| D12 | T09 | 🟢 | Convention-independent Aut_{±μ}(O) construction; shipped rows verified undamaged |
| D13 | T01 | 🟢 | Legacy-label grammar + old→new map (53 mapped / 400 pending / 5 unmappable) |
| D14 | T01 | 🟡 | The 4 grammar-violating labels: drop vs adopt plausible-intent corrections |
| D15 | T01 | 🟡 | The `15.4` family (16 labels): extend generation to non-squarefree M, or park forever |
| D16 | T02 | 🟡 | model_type derivation scheme; aux-square models parked as type 8 |
| D17 | T02 | 🟡 | Corrupted `39.1-[1,13]` quartic (+3 siblings to verify): regenerate |
| D18 | T02 | 🟢 | `create_table` for shimcurve_modelmaps/teximages — safe to run **now** |
| D19 | T03 | 🟡 | Point-count conventions: 0 ⇒ pointless NULL; infinite ⇒ pointless=f, count NULL |
| D20 | T03/T24 | 🟡 | **`shimcurve_points.Clabel` keying: full label vs bare coarse label** |
| D21 | T03 | ⚪ | 9 curves with count=2 but no coordinates — regenerate later |
| D22 | T13 | 🟢 | jacobian_decomp productionized, M-aware; JLDecomposition left D·M on purpose |
| D23 | T13 | 🟢 | Findings A/B/C → T30 spinoff; T14 restricted to the coarse (JL) arm for now |
| D24 | T13 | 🟢 | cmfdata strategy: near-term dump + `−3` self-heal (no 25–30 GB monolith) |
| D25 | T24 | 🟢 | Frontend sweep (10 commits): approve + push |
| D26 | T24/T27 | 🟡 | `factorization` column: add to schema vs strip frontend references |

Cross-cutting ⟐ items not owned by any review ticket (Q11 name votes, Q14 `area` rename, Q8 route) are at the end.

---

# 1. Foundation — T28, T29

These two predate the wave (2026-07-16/17) and everything else is stacked on them. Nothing in waves 1–2 can merge before they do.

## T28 — path conventions ([T28-path-conventions.md](T28-path-conventions.md))

**Review**: `git -C ~/claude/ShimCurve diff 5e7c460..ticket/T28-path-conventions` — 11 files, +48/−31.

### D1 🟢 Adopt the repo-root path convention

**Context.** The codebase had three mutually incompatible cwd conventions (`"ShimCurve/data/…"` assuming the *parent* dir, `"./data/…"` and `"data/…"` assuming repo root). No working directory made all writers land correctly; the README's instruction ("work one directory above") made the *main* writer emit outside the repo. This is the likely mechanical cause of T06's `.m`-vs-`.txt` file disagreements, and it made parallel worktrees unsafe (writes escaping into shared directories).

**What was done.** Single accessor `DataFile(rel)` in new `code/utils/paths.m`; all ~22 reader/writer sites routed through it; README now says: run Magma from the repo root, `AttachSpec("spec")`. Drive-by: fixed a pre-existing syntax error in `tests/data_roundtrip.m` that was aborting `run_quick` on main.

**Evidence.** Live-verified: `EnumerateO`, `EnumerateOmu`, `WriteHeaderAndSubgroupsDataToFile` all write inside `<repo>/data/`, parent stays clean. Quick suite green.

**Your call.** Mechanical and already load-bearing (every wave-1/2 agent worked on top of it). Approving = merge to your integration branch.

## T29 — label determinism ([T29-label-determinism.md](T29-label-determinism.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T28-path-conventions..ticket/T29-label-determinism` — 6 files, +254/−25. Key file: `code/level-structure/canonical-sort.m` (new).

**Context for all of D2–D5.** Measured fact: running the pipeline twice on identical inputs assigned labels differently (the `a`/`b` letters swapped between the two genus-0 index-2 D=6 curves). Root cause: `updateLabels` sorted by permutation character only; ties fell back to Magma's `Subgroups()` enumeration order, which is not stable. Since LMFDB labels are permanent public identifiers, and every Tier-1/2 ticket stages label-keyed `update_from_file`s, unreproducible labels made every reload unsafe. Q15 (DECIDED, Eran) fixed the design; T29 implemented it.

### D2 🟢 The canonical sort implements Q15's design

**What was done.** Sort key = permutation character (Gassmann class → the class letter, as before) → **Atkin–Lehner content** (sorted multiset of squarefree Aut-component norms over cosets — a conjugacy-class invariant, unlike the generator-dependent `autmuO_norms` column) → **Sutherland-style canonical generators** (lex-minimal generating sequence, minimized over the G-conjugacy class, computed lazily only on residual ties). Rows now written in sorted label order.

**Evidence.** Full corpus (all 15 (deg,N) files), two independent passes: identical labels, identical values in every column except two presentation-dependent encodings (`generators`, `ram_data_elts` — see FYI below). Regression test `tests/regression_label_determinism.m` wired into run_quick/run_all. Full corpus regen ≈ 19 min/pass on your machine.

**Your call.** Confirm the implementation matches the intent of your Q15 answer (AL content as tiebreaker 1, canonical generators as tiebreaker 2).

### D3 🔴 `is_split` redefined

**Context.** Testing exposed that `is_split` was computed as `H ∩ Image(Ahom)` — which is **not conjugation-invariant**: its value flipped between identical runs depending on which conjugate of H the enumeration produced. So the shipped column is partly noise.

**What was done.** Now `true` iff **some conjugate** of H splits against the standard section — a genuine invariant of the curve.

**Evidence.** Values change on "a handful" of rows vs shipped (exact rows visible in the T27 reload diff).

**Your call.** This is a semantic change to a stored column. The old definition was representative-dependent (i.e. not well-defined), so there's no honest alternative, but you should bless the specific fix.

### D4 🔴 `G1` := kernel of the reduced-norm determinant hom

**Context.** `G1` feeds `psl2label` and `scalar_label`. It was computed as `O1_subs[last]` — the last element of a filtered subgroup list. At N=3 that list contains **several incomparable** maximal det-trivial subgroups, so the choice was mathematically arbitrary *and* unstable across runs.

**What was done.** `G1 := Kernel` of the reduced-norm determinant hom on G — the SL₂-analogue, canonical.

**Evidence.** `psl2label` changes on **2158/2198 rows (98%)** vs shipped; `scalar_label` follows.

**Your call.** Again the old value was arbitrary, but the blast radius (98% of psl2labels + the pictures table keying, see D5) makes this the biggest semantic sign-off in the packet.

### D5 🔴 Reload strategy for T27 (= the formal Q15.3 sign-off)

**Context.** T29 step 4 asked: do shipped labels survive the canonical sort? Answer: **no** — 1614/2198 rows (73%) change which curve their label names.

**What this means.** Label-keyed `update_from_file` against the current `gps_shimura_test` is **unsafe** (it would attach values to the wrong curves). Consequences, all already baked into how wave 1–2 staged their artifacts:

1. T27 must be a **full atomic reload** via `copy_from` (with the rename to `gps_shimura`, per Q12.3) — not incremental updates.
2. The 304 `shimcurve_pictures` rows are keyed by `psl2label` and must be **re-keyed** at reload.
3. Every artifact in `artifacts/` carrying a `PROVISIONAL — pending T27 reload` banner stays parked until then.

Your Q15.3 answer anticipated this ("still in alpha and we expected labels to change") — this is the formal sign-off on executing it.

**⚪ FYI (open follow-up, not blocking):** the `generators` and `ram_data_elts` encodings are still presentation-dependent (Ngens rep / coset-numbering Lehmer codes churn per process). This does NOT affect label safety or any other column; canonicalizing those two encodings is a cosmetic follow-up ticket if you want byte-identical files.

---

# 2. Tier-1 math corrections — T10, T07, T09

One stacked branch chain by agent wave1-A (worktree `tier1core`), in this order. All on top of T29. `tests/run_quick.m` green (0 failures, 0 skips) at the stack tip, including the new gerbiness and construction regression tests.

## T10 — the N=5 assertion ([T10-N5-assertion.md](T10-N5-assertion.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T29-label-determinism..ticket/T10-N5-assertion` — 3 files, +191/−5.

### D6 🟢 Assert `[G:G1plus] = 2` → `= EulerPhi(N)`; Q4's ⟐ closed

**Context.** `assert #G/#G1plus eq 2` failed at D=6, N=5, which is why N=5 is missing from all shipped data. Q4 (DECIDED) diagnosed it: the quotient G/G1plus is the reduced-norm map onto (ℤ/N)ˣ, so the index is **φ(N)**, not 2 — every previously tested N just happened to have φ(N) ≤ 2. N=5 is the first N with φ(N) = 4; nothing was mathematically wrong. Q4 left one ⟐: a maintainer sign-off that no *other* site silently assumes index 2.

**What was done.** The assert fixed at all three sites (`enumerate-H.m` ×2, `genera.m:66`), mechanism documented as a docstring. The ⟐ discharged by a repo-wide grep (`#G/#G1plus`, `#G/2`, `eq 2`, `index 2`, `Gplus` over `code/` + `tests/`): **only the three assert sites** assume index 2; nothing downstream consumes the index (the Fuchsian index is computed independently). The `X0DN_code.m` "index 2 subfield" hits are unrelated CM ring-class-field statements.

**Evidence.**
- Spot-check at N=5: #G = 1920, #G1plus = 480, index 4 = φ(5); G/G1plus ≅ (ℤ/5)ˣ. Matches Q4's table.
- **No-regression proof**: N=3 (36 rows) and N=4 (262 rows) regenerated pre- and post-fix — identical in all 66 canonical fields (the 2 churning fields are the known T29 leftover, shown to churn between *identical-code* runs too).
- **N=5 evidence file** generated clean: `data/genera-tables/genera-D6-deg1-N5.m`, 175 rows, 3.5 s (committed as PROVISIONAL evidence; mass level generation stays in T23).
- Coarse cross-check: `SignatureX0DN(6,5)` = (genus 1, e₂=4, e₃=0) matches the trivial-Aut-projection row `6.1.5.24.1.b.1` exactly (genus 1, ν₂=4, ν₃=0).

**Your call.** Approve the fix + accept the grep as closing Q4's ⟐. This unblocks T23 (higher levels).

## T07 — gerbiness ([T07-fix-gerbiness.md](T07-fix-gerbiness.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T10-N5-assertion..ticket/T07-fix-gerbiness -- code/ tests/` for the code (commit `2aa137f`); commit `9defaf1` is the regenerated 69-column corpus (treat as generated data — the verification is the diff summary below, not eyeball review).

**Context for D7–D11.** Upstream issue assaferan/ShimCurve#6: the gerbiness computation "should be 1 when deg μ = 1 but can be larger" — yet the shipped column stored 2/4/6 for deg 1/2/6. Q2 (DECIDED, Eran) resolved the confusion: **three distinct quantities were sharing one name**. The decision: `gerbiness` = |ker(f: Aut_{±μ}(O) → Aut(coarse curve))| — the moduli-stack gerbe, trivial iff deg μ = 1; the old stored value (#KG_level, the root-of-unity band ⟨ζ_{2n}⟩ of O reduced mod N) survives renamed as `base_gerbiness`; `aut_gerbiness` is kept for the Gauss–Bonnet genus normalization.

### D7 🔴 `gerbiness` := #ker(f); `base_gerbiness` added; schema grows

**What was done** (commit `2aa137f`):
1. New intrinsics `GerbeKernel(O,μ)` / `Gerbiness(O,μ)` in `aut_mu_O.m`, docstrings = the decided definitions (the lasting spec Q2 asked for).
2. `createRecord`: `gerbiness` column now #ker(f) (with `assert #KG eq 2*gerb`); `base_gerbiness` := #KG_level added; `aut_gerbiness` untouched.
3. `LMFDBRowEntry`: `Gerby_gen` now a genuine generator of ker(f) (was hardcoded identity); polarized writers 10 → 11 cols (`gerbiness` appended **last**, so existing positional readers are unaffected).
4. `X0DNdata`: hardcoded `gerbiness := 1` replaced with live `Gerbiness(O,μ)` where μ is in hand, theorem-backed 1 otherwise.
5. **Schema: `?`-writer 68 → 69 cols, `|`-writer 70 → 71** (`base_gerbiness integer` after `bad_primes` in both — the exact delta handed to T04/T25).

**Evidence.**
- **Full-corpus regeneration + field-mapped diff vs a pre-change baseline: all clean.** 2,198 rows, 15 files: row counts and label sequences identical; new `base_gerbiness` == old `gerbiness` on **every** row (including the mod-level band collapse at N ∈ {1,2}); new `gerbiness` = 1/3/2 for deg 1/2/6 uniformly (level-independent, as the definition demands); no other column changed (mod the 2 known churn fields).
- Sanity theorem "gerbiness = 1 ⟺ deg μ = 1" holds on every regenerated row.
- The LSSV §3.5 2-liner you asked for in Q2.4 is done (ticket Log): ker(f) is precisely the residual gerbe band via LSSV Lemma 3.5.3 + Minkowski faithfulness (Lemma 3.5.7).

**One finding worth your attention**: the new `gerbiness` **coincides numerically with the existing `aut_gerbiness` on all D=6 data** (both count the band whenever reduction mod N ≥ 3 is faithful, which it always is at working level). Q2.1 predicted #ker(f) would be "generally smaller than aut_gerbiness" — it is a genuinely distinct quantity *semantically*, but not in value on this corpus. Flagged so nobody is surprised when the columns look redundant; the ⟐ option to rename `aut_gerbiness` → `aut_band` (Q2.2) would remove the confusion — your pick, renames are free (nothing displays these yet).

**Your call.** Approve the redefinition, the `base_gerbiness` name (Q2.2 offered `unit_gerbiness`/`automorphism_band` as alternatives), and the schema delta.

### D8 🟡 Deviation from Q2.4: the injectivity assert was kept

**Context.** Q2.4 said the unconditional injectivity assert at `aut_mu_O.m:66` "must be dropped/relaxed — it would fire on exactly the deg μ > 1 rows."

**What was done — deliberately not that.** The agent's analysis: that assert checks `grp_map: A → Bˣ/Qˣ`, which is injective **by construction** (A is built to biject with its image; downstream `#Domain` counts rely on it). The non-injective map of issue #6 is the *moduli* map f — now computed directly by `GerbeKernel`, not via grp_map. Empirically the assert does **not** fire on the gerby deg-2/6 cases (the full corpus regenerated through it, twice under T29 + once here). A comment at the assert documents the distinction.

**Your call (routes to Eran).** Confirm the analysis, or ask for the relaxation anyway (one-line change). The Q2.4 concern was reasonable from the outside; the code distinction makes it moot.

### D9 🟡 `Gerby_gen` coordinate convention (Q2.3's ⟐)

**What was done.** Per the ⟐ recommendation: primitive integral B-coordinate representative (`Eltseq(B!·)`, primitivized to fit the `integer[]` column exactly as `AutmuO_generators` is). Note the norm-1 unit itself can have half-integral coordinates — recoverable as gen/√nrd.

**Your call.** Ratify (it followed your recommended option; the alternative was `Eltseq(O!·)`).

### D10 🟡 Scope of the deg-1 theorem (routes to Eran)

**Context.** "gerbiness = 1 ⟸ deg μ = 1" is a theorem **for maximal orders** (μ² = −disc, squarefree ≥ 6 kills the ℚ(μ)-side band) and is asserted in code there. For **Eichler** orders it is not forced in general; for the X(D,N;1) rows the ℚ(μ)-side is provably trivial (D·N = 3k² or 4k² impossible for a genuine quaternion discriminant with gcd(D,N)=1), leaving only a possible χ-side ζ₄; spot-checks (B₆, Eichler levels 2/5/11) all give 1 — but it is **not asserted as a general theorem in code**.

**Your call.** Eran confirms the intended assertion scope (maximal-only assert + spot-checked Eichler is what's implemented).

### D11 🟢 Post the issue-#6 closing comment

A complete draft closing comment sits in T07's Log (bottom of the file) explaining the three-quantities resolution. Per the hard rules the agent did not post it. **Your call**: post it (presumably when the branch merges — it references the commits).

**⚪ FYI — Pollack-class dependence (feeds T08).** Gerbiness is an invariant of the polarization **class**, not just (O, deg): the shipped deg-2 rows carry a ζ₄-band μ (old values 4/2) while the current `HasPolarizedElementOfDegree` picks a ζ₆-band μ (6/3 → new gerbiness 3). One more consumer for T08's canonical-and-complete Pollack-class enumeration (in flight, agent wave1-B). Also why the full polarized-file regeneration (`EnumerateOmu(1000)`) was **deferred to the post-T07+T08 "T06 wave"** — running it mid-T08 would produce files conflicting with agent B's. Ratify the sequencing implicitly with D7.

## T09 — Aut_{±μ}(O) construction ([T09-autmuO-fixmes.md](T09-autmuO-fixmes.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T07-fix-gerbiness..ticket/T09-autmuO-fixmes` — commit `b9d375f`; key files `aut_mu_O.m`, `enumerate-O.m`, new `tests/regression_autmuO_construction.m`.

### D12 🟢 Convention-independent construction; shipped rows verified undamaged

**Context.** Two FIXMEs marked the C4/C6/D4/D6 cases of `Aut` as broken: the code addressed pc-group generators as `.1`/`.2` and assumed they carry full element orders, which is presentation-dependent (Magma's pc-presentations use prime relative orders for composite n). Feared consequence: silently wrong Aut data poisoning `quaternion_orders_polarized` (119 D4 + 39 D6 rows shipped) and all downstream enumeration.

**What was done.**
- Established the real failure model first: **crash-on-other-versions, silent wrongness impossible in any version** — Magma's `map<>` constructor rejects inconsistent element lists outright (verified by direct simulation), and `MapIsHomomorphism(… injective)` is a total check. In V2.29-7 the old code happened to work.
- Fix: generators **searched canonically** (w_μ := first element of order cyc_order; w_χ := first order-2 element outside ⟨w_μ⟩ inverting w_μ) — never `.1/.2`; element list built from the explicit decomposition with a bijectivity assert; order-preservation asserts added. `AutmuO_generators` in `LMFDBRowEntry` now comes from the canonical generators (the second fragile site).
- Regression test: D6 (6.2) and D4 (6.6) end-to-end including `EnhancedImageGL4` at N=3 against the honest product formula (note recorded: 3 ramifies in B₆ so #(O/3)ˣ = 72, not |GL₂(𝔽₃)| = 48).

**Evidence for "shipped data is fine".** New `LMFDBRowEntry` output vs devmirror for all D=6/10/15 rows (8 labels): μ and `AutmuO_generators` **byte-identical** — the canonical search reproduces the old picks in this version, so the shipped D4/D6 rows carried correct Aut data. No corrected rows need staging. (`Gerby_gen` differs on all 890 rows — but that's T07's redefinition, riding the deferred post-T08 polarized regen.)

Also established: **no C4/C6 instance exists** over discO < 1000 (the missing 10.10/15.3/15.15 rows are because `HasPolarizedElementOfDegree` is genuinely false there, not bug casualties — probed directly).

**⚪ FYI — side-find for T08 (already routed).** For some Eichler cases (e.g. discO=30, deg 30) `HasPolarizedElementOfDegree` returns a μ that does **not normalize O**, crashing `IsTwisting` with an illegal coercion. T08's canonical μ must enforce normalization.

**Your call.** Approve. The construction change is behavior-preserving on everything shipped, version-robust going forward, and regression-tested.

---

# 3. Legacy data resurrection — T01, T02, T03

One stacked chain (T02/T03 by wave2-G on top of wave1-E's T01). **Context for the whole group**: 462 model records + 424 rational-point records were computed years ago under the old label scheme `D.N-[m1,…]` and never uploaded. These tickets decode the old labels, build the old→new crosswalk, and stage everything uploadable — all `PROVISIONAL — pending T27 reload` per D5, keyed for a one-command re-key afterward (recipe: [artifacts/T01-report.md](artifacts/T01-report.md) §4).

## T01 — the label map ([T01-legacy-label-map.md](T01-legacy-label-map.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T29-label-determinism..ticket/T01-legacy-label-map` — 5 files, +901 (scripts only). Read [artifacts/T01-report.md](artifacts/T01-report.md) (the real deliverable) + [artifacts/T01-label-map.csv](artifacts/T01-label-map.csv).

### D13 🟢 Grammar confirmed; map built

**What was done.** 458 distinct legacy labels extracted (models ⊇ points). Grammar = exactly your Q1 reading: `D.M-[Hall divisors]` = X₀(D;M)/⟨w_m⟩, prefix is discriminant·**Eichler level**. Validated two independent ways, zero contradictions: combinatorially (42/69 families exhibit the complete AL-subgroup lattice) and by genus (53/53 bases vs devmirror, 43/43 vs points file, **198/198 quotients** vs `SignatureX0DNmodAtkinLehnerElement`).

Map result: **53 MAPPED_PROVISIONAL** (the `[1]` bases → coarse X₀(D;M) rows; provenance label only), **400 UNMAPPED_PENDING_GENERATION** (all proper AL-quotients — no target rows exist until the T19→T20→T09→T08 chain generates level-1 enhanced rows for those discriminants, which your Q1.2 decision (option b) put in scope), 4 grammar violations (D14), 1 no-coarse-row (D15). Everything carries a durable join key `(discB, discO, deg_mu, level, al_subgroup)` so the map auto-completes as generation lands — the pending 400 are a crosswalk waiting for its targets, not lost work.

**Your call.** Approve the methodology + artifacts. Note the D=6 curiosity: the 5 existing enhanced discO=6 rows have *no* legacy label (legacy D=6 is all Eichler M ≥ 5), so they validated the recipe but map to nothing.

### D14 🟡 The 4 grammar-violating labels

**Context.** Four labels have an AL component that is **not a Hall divisor** of D·M — impossible under the grammar. All four sit in the `y²=quartic` model block near known-corrupt records. Per the no-guessing rule they were left unmapped. The report's table ([T01-report.md](artifacts/T01-report.md) §5.1):

| label | bad component | Hall divisors of DM | plausible intent |
|---|---|---|---|
| `77.1-[1,17]` | 17 | {1,7,11,77} | `[1,7]`? |
| `85.1-[1,2]` | 2 | {1,5,17,85} | `[1,5]`? |
| `94.1-[1,89]` | 89 | {1,2,47,94} | spurious (94.1 already complete) |
| `178.1-[1,30]` | 30 | {1,2,89,178} | corrupt |

**Your call.** (a) Drop all four as data-entry errors (recommended by the agent), or (b) if you remember the provenance of the models file, correct them at the source. Genus cross-checking a "plausible intent" guess against the model equation could confirm/refute — say the word if you want that run.

### D15 🟡 The `15.4` family — non-squarefree Eichler level

**Context.** 16 labels live over `X₀(15;4)` (discO = 60). M = 4 is non-squarefree; the coarse pipeline asserts `IsSquarefree(N)` and never produced that row, so the whole family is unmappable.

**Your call.** Scope decision: (a) extend the coarse generator to non-squarefree M (new work, touches Q12's release scope), or (b) permanently park these 16 models. This is the only legacy family that no currently-planned work will ever absorb.

## T02 — models upload ([T02-upload-models.md](T02-upload-models.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T01-legacy-label-map..ticket/T02-upload-models` (scripts); artifacts below.

### D16 🟡 model_type derivation + the type-8 parking

**Context.** The source file's `model_type` code is **not** the LMFDB code (source ∈ {3,5,7} with source-5 spanning everything from conics to hyperelliptics; LMFDB ∈ {0,2,5,7,8}). So types had to be derived from equation shape, calibrated against `modcurve_models` and the frontend's `formatted_model()` — which strict-parses only types 5 and 7 and will 500 on a shape mismatch.

**What was done.** Conic in 3 vars → **2** (plane; matches the 1 existing devmirror row) [152 records]; single 3-var equation with y², deg ≥ 3 → **5** (Weierstrass; matches how modcurve stores genus-2..9 y²=f in 3 vars) [241]; everything else — 4-var quadric intersections, double covers, 2-var y²=quartic — → **8** (embedded, rendered by the crash-proof generic branch) [69]. Equation normalization is lossless and syntactic only (no homogenization, no coefficient changes); stored in the existing shimura implicit-multiplication convention.

**The parking decision inside this**: the genus-1/3 "geometric hyperelliptic" source models are in 2-/3-variable auxiliary-square forms the frontend's 4-var type-7 parser cannot consume. Rather than risk a mathematical re-expression, they're stored as type 8 (safe generic display, no Weierstrass-style rendering). 28 affine `y² = quartic` records could be promoted to type 5 by homogenizing into weighted P(1,2,1) — deferred (needs sign/weight care).

**Your call.** Ratify the mapping + parking, or commission the re-expression pass (a new small ticket: promote the 28+ quartics to proper type 5/7 display). Display-only stakes; correctness is not at risk either way.

### D17 🟡 Corrupted model reps

`39.1-[1,13]`'s y²=quartic rep has a doubled `−34x³` term (definitely corrupt). Its three siblings with duplicate quartic reps (`55.1-[1,5]`, `62.1-[1,2]`, `69.1-[1,3]`) should be verified too. The duplicates themselves are legitimate (two distinct models of one genus-1 curve — both kept), all four are parked-pending anyway, so nothing blocks. **Your call**: regenerate/verify the four quartic reps (needs whoever/whatever produced the models file — your side).

### D18 🟢 Create the two auxiliary tables — safe now

**Context.** The frontend reads `shimcurve_modelmaps` and `shimcurve_teximages`, which **do not exist** — a latent 500 for any pure-Python consumer (T24 found and guarded one such crash in the downloads). No map data is derivable from the source files, so both tables are created **empty**.

**What was done.** Complete `create_table` statements (in T02's Log, validated structurally against the modcurve blueprints — `modcurve_modelmaps` minus `upload_id`, `modcurve_teximages` verbatim), plus a script `code/scripts/t02_create_tables.py --execute`.

**Your call.** Approve + **run now** (editor credentials) — this is label-independent, so it does *not* need to wait for T27, and it closes the latent-500 class for real. The models `copy_from` itself waits for T27 + re-key (commands staged in the Log).

## T03 — points upload ([T03-upload-points.md](T03-upload-points.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T02-upload-models..ticket/T03-upload-points` (scripts); artifacts below.

**What happened (context).** The points file mixes two kinds of information; T03 split it: 317 individual point records (→ `shimcurve_points`, jsonb coordinates keyed by model_type per the modcurve convention — the arity→model join resolved cleanly for all 317, 289 P² points → key "5", 28 P³ → key "8") and 424 per-curve counts (→ `gps_shimura_test` columns). Staging outcome: **0 points staged / 317 parked** (every point lies on a proper AL-quotient whose row doesn't exist yet — same T19→T20→T09→T08 dependency as T02), **42 count-rows staged / 382 parked**. Genus agrees with T01 on all 424 records.

### D19 🟡 Count conventions (copied from modular curves)

- count = k > 0 → `num_known_degree1_points = k`, `pointless = f` (+ k point rows);
- count = 0 → `num_known_degree1_points = 0`, `num_known_degree1_noncm_points = 0`, **`pointless = \N`** — a search finding nothing is not a proof; pointlessness proofs (Shimura's theorem etc.) are Q9/T15's job;
- count = "infinite" → genus-0 with a rational point: `pointless = f`, **count left NULL** (matches modcurve genus-0 handling; 139 labels).

**Your call.** Ratify. The 0-count/pointless-NULL line is the one with mathematical content.

### D20 🟡 **The `Clabel` keying convention** (decides T03 + T24 coherently)

**Context.** The devmirror schema is authoritative: `shimcurve_points` has `Clabel` (no `Elabel` — T24 already aligned the search code to that). But *what value* goes in it: the frontend's points queries filter by the **bare** `self.coarse_label` (`web_curve.py:765-778`), while T03 keyed the staged `curve_label` on the **full** label (`mu_label.coarse_label` form) — matching `shimcurve_models.shimcurve`, `modcurve_points.curve_label`, and the rest of the schema. One side must change; T24 deliberately did not touch it pending your call.

**Your call.** (a) **Full label** (agent recommendation: consistent with models + modcurve precedent; then T24 gets a one-line follow-up fixing the frontend queries), or (b) bare coarse label (then T03's staged files get re-keyed — cheap, they're parked anyway). Deciding now keeps the two tickets from merging incoherently.

**⚪ D21 FYI — 9 curves have count=2 but no materialized coordinates** (`coords_na=t` in the parked file; labels in T03's Log). Their counts load; their points can't until coordinates are regenerated. Queue behind the generation chain.

---

# 4. Jacobian machinery — T13 (+ T30 spinoff)

## T13 — jacobian_decomp productionized ([T13-jacobian-decomp-productionize.md](T13-jacobian-decomp-productionize.md))

**Review**: `git -C ~/claude/ShimCurve diff ticket/T29-label-determinism..ticket/T13-jacobian-decomp` — 8 files, +450/−63. Standalone branch (only touches `code/jacobian_decomp/` + tests).

**Context.** This is the machinery for the ~all-NULL Jacobian columns (`newforms, dims, mults, conductor, rank, …`); T14 does the mass run once it's trustworthy. It needed an external `cmfdata.txt` that existed nowhere.

### D22 🟢 Productionization + the M-awareness interpretation

**What was done.**
- **`make_cmfdata.py`** written (format reverse-engineered: `label:level:cond:dim:rank:traces`; the non-obvious mapping: `cond = char_conductor` — `mf_newforms` has no `conductor` column — and `rank = analytic_rank` of the Galois orbit, per Q13.2). **`data/cmfdata/cmfdata.txt` materialized**: 15,899 forms, level ≤ 2000, 1000 traces each, 44.4 MiB, gitignored. Covers the whole near-term corpus incl. all 339 coarse ground-truth rows.
- **M-awareness (Q13.3, DECIDED)**: `CMFLoad` and `ShimuraNewformDecomposition` now take `discO`, candidate filter `level ≤ discO·N²`. **`JLDecomposition` deliberately left with `AmbientLevel = discO`** — its second argument is already the Eichler/order level (tablesX0DN calls it with congruence level 1), so `D·M` is already correct there and changing it would double-count M. Q13.3's phrasing targeted the general enhanced path, which lives in the filter. Docstring clarified. ← *this is the interpretation you're ratifying.*
- Robustness: debug prints removed; a **latent cutoff bug fixed** (traces are indexed by prime *value*; the old cutoff let the loop read past the list end); `FindI/FindJ` retry-strings replaced with self-escalating search + caps; consistent failure protocol (−1 genus 0 / −2 data / −3 cutoff); `assert Σ dims·mults = genus` kept.
- New **`JacobianData(H, G, O, mu, N)`** intrinsic returning everything T14 needs per row (conductor factored per Q13.1; rank/trace_hash stay python-side per the ticket).

**Evidence.** **32/32 devmirror ground-truth rows agree exactly** (bar was 20), spanning discB 6..403, Eichler + maximal, genus 0..31, rank 0..3, dims 1..10 — matched by *invariants*, not by the unstable shipped labels. Classical checks: X₀⁶(1) trivial; X₀⁶(5) → 30.2.a.a; X₀¹⁴(3) → {14.2.a.a ×2, 42.2.a.a}; X₀³⁵(1) → {35.2.a.a, 35.2.a.b}. Regression test wired into run_quick (green, ~4 s; skips gracefully on a bare checkout without cmfdata).

**Your call.** Approve, including the JLDecomposition interpretation.

### D23 🟢 Findings A/B/C → T30; T14 restricted to the coarse arm

**Context.** While validating the never-before-called trace-matching arm, the agent found the enhanced path is **not usable yet** — three discoveries beyond "productionize" scope:

- **A**: `IndefiniteTrace` has no input path for an Eichler level M (its `O := MaximalOrder(B)` is never used again) — the M-aware filters are necessary but not sufficient for Eichler rows.
- **B (representation gap)**: the enhanced enumeration produces H ⊆ GL₄(ℤ/N), but the trace formula needs H ⊆ GL₂(ℤ/N); the GL₄→GL₂ bridge doesn't exist in the repo.
- **C (math bug)**: even with a hand-built GL₂ Borel (= X₀⁶(5)), `HTraces` does not reproduce the known Jacobian — and for genus-0 X₀⁶(1) it returns nonzero traces where a trivial Jacobian forces zeros. The values resemble an embedding-number mass, not cuspidal Frobenius traces. Needs debugging against Eichler / Voight Ch. 30.

**What was done.** [T30](T30-trace-formula.md) created for A+B+C (agent wave2-H is on it now); T14's dependency updated to T13+T30, with the coarse arm explicitly unblocked: **JLDecomposition is fully validated and T14 may run coarse rows on it today**.

**Your call.** Ratify the spinoff + sequencing. (Nothing shipped is wrong — the broken arm was never called by anything.)

### D24 🟢 cmfdata production strategy

**Context.** Q13's ⟐ caveat is now **verified on the devmirror**: `mf_newforms.traces` holds only ~100 coefficients and `analytic_rank` is NULL for level ≥ 10001, so a naive full-scope dump (level ≤ 36000: 574k forms) is unusable at default depth and a Sturm-correct one is 25–30 GB + requires computing 446k missing ranks.

**What was proposed** (and wired): ship the near-term dump; during T14's mass run treat the `−3` "cutoff reached" return as *regenerate deeper for the affected candidates (via `mf_hecke_nf`) and retry* — a detectable, self-healing failure instead of a monolith. **Your call.** Ratify.

---

# 5. Frontend — T24 ([T24-frontend-bug-sweep.md](T24-frontend-bug-sweep.md))

**Review**: `git -C ~/claude/lmfdb diff dfe40d0fe..ticket/T24-frontend` — 5 files, +78/−74, **10 commits, one per item** (newest `dc64d2f35` … oldest `1dd7a0fca`). Drift-checked: base was exactly one tickets-commit ahead of both `origin/shimura_curves` and `eran/shimura_curves`; note local `shimura_curves` has since merged main (`5c2fbc140`), so merge at push time.

### D25 🟢 The sweep itself — approve + push

All 8 planned items landed, plus discoveries:

1. **Sage download 500** (typo'd method name) fixed; the new 3-route regression test then surfaced **two more pre-existing 500s** in the shared download builder — a `factorization` KeyError (see D26) and an unguarded query against the nonexistent `shimcurve_modelmaps` (see D18) — both fixed defensively.
2. **`Elabel` → `Clabel`** per the authoritative devmirror schema; also removed the `cusp` search filter that validated against a column `shimcurve_points` doesn't have (Shimura curves are compact — `?cusp=no` was a guaranteed 500).
3. Test asserting modular-curve content (`X_0(N)`) rewritten to assert Shimura content + a curve-page test added.
4. `modcurve.*` knowl references → `shimcurve.*` (broken-knowl links until T26 — acceptable on beta), wording fixes.
5. **Stats workaround root-caused**: `count({})` had returned a stale cached total of 0; on the current devmirror the stale stat is gone and plain `count()` returns 2,587 — workaround removed; T27's reload regenerates the stat properly.
6. Dead code deleted (`url_for_RZB_label`, `url_for_CP_label`, unused regexes/methods/imports); pyflakes clean.
7. 12 `# STAGED:` markers on the commented-out feature blocks (CM points, rational-points sections, low-degree link…) so their purpose is discoverable — nothing enabled, nothing deleted.
8. Staged block's `contains_negative_one` → `is_coarse` (matches Q5: is_coarse ⟺ −1 ∈ H).
9. (No-change verification) the `show_genus` `aut_gerbiness` factor from Q14 was already present at base — noted in T06's Log.

**Evidence.** `pytest lmfdb/shimura_curves/` → 3 passed. Manual curl checklist on the port-37778 dev server: homepage, searches, level-1 / level-structure / Eichler / deg-μ>1 curve pages, all three downloads, random, stats, diagram, low-degree points — **all 200**.

**Your call.** Review + push (agent left the branch local per the rules).

**⚪ FYI — the one remaining 500 is not Shimura's.** `/ShimuraCurve/data/<label>` 500s via `api.py:422` `datapage` (`LMFDBSearchTable has no attribute 'extra_cols'`) — the control `/EllipticCurve/Q/data/11.a2` fails identically, so it's this machine's environment. Given the venv moved to **psycodict 1.0.0rc1** last night, this smells like an rc regression or API drift worth checking before the 1.0.0 release — relevant to your PyPI project, not to T24.

### D26 🟡 The `factorization` column

**Context.** `gps_shimura_test` has **no `factorization` column**, yet main.py (jump-box fiber products, `parse_element_of factor`) and web_curve.py (`fiber_product_of`) reference it — Jinja masks it on curve pages; pure-Python paths error (one such crash fixed defensively in item 1).

**Your call.** Add the column to the T04/T25 canonical schema (and populate at T27), or strip the frontend references. Can be deferred to T27 planning, but the schema ticket (T04, in flight) would like to know.

---

# 6. Cross-cutting ⟐ decisions not owned by any review ticket

From [QUESTIONS_ANSWERS.md](QUESTIONS_ANSWERS.md) ("Open sub-decisions" section) — listed here so the packet is the one place to sweep:

- **Q11 — the three name-grammar votes** (second slot M vs discO; partial-AL notation; deg μ decoration). The appendix in QUESTIONS_ANSWERS has the full proposal; recommended default: `X_0(D, M; N)`, TeX quotients, names only for deg μ = 1. Needed before T18 (names) and affects `NAME_RE`.
- **Q14 — the `area` column**: keep value φψ/12 but rename (`covol/(4π)`-style honesty) vs store φψ/6 and adjust both genus formulas. Recommendation on file: keep value, rename. T06 executes.
- **Q8 — normalizer route**: recommendation (B) algebraic — **T19 (in flight) is already executing route B** with strong results; formal ratification can wait for T19's review packet. Preview of what's coming from its log: the general machinery works across a D-spread, a real bug in its own first version was caught by Eran's assert (norm m·k² elements need not normalize O), and it found a **suspected upstream bug in `SignatureX0DNmodAtkinLehnerElement`** (`s3 := e3` should be `e3/2` when 3 ∤ m — check case D=10, m=5: genus 0 + area 1/3 forces s3 = 2, code says 4; the returned *genus* is unaffected since Ogg's Eqn 3 uses only fixed-point counts).
- **Q2 minor**: rename `aut_gerbiness` → `aut_band`? (bundled into D7's context.)
- **Q7 minor**: which signature source is authoritative (fixed generators vs Ogg formulas) — T20's problem, but the T19 finding above is relevant evidence.

---

# 7. Artifacts inventory (all in [artifacts/](artifacts/))

All label-keyed files are **PROVISIONAL — pending T27 reload** (D5); each carries the banner + its load commands. Nothing may touch a writable DB until you run it.

| file | rows | for | load gate |
|---|---|---|---|
| `T01-label-map.csv` (+ report + intermediate) | 458 labels | the crosswalk | reference only |
| `T02-shimcurve_models.txt` | 53 | `shimcurve_models.copy_from` | T27 + re-key |
| `T02-shimcurve_models-keys.csv` | 53 | the re-key join | — |
| `T02-models-parked.txt` | 409 | waits on generation chain | T19→T20→T09→T08 |
| `T02-gps-models-count-update.txt` | 53 | `models` counts | T27 + re-key |
| `T03-shimcurve_points.txt` | 0 (valid empty) | `shimcurve_points` | T27 |
| `T03-points-parked.txt` | 317 points | waits on generation chain | same |
| `T03-gps-points-update.txt` | 42 | point counts | T27 + re-key |
| `T03-gps-points-parked.txt` | 382 | point counts | generation chain |
| `T07-gerbiness-update.txt` (+ README) | 2,373 | `gerbiness`/`base_gerbiness` | T27 (or moot if T27 reloads from the 69-col genera files, which already carry both) |

Plus, in the repos (not artifacts/): the regenerated 69-col D=6 corpus + N=5 file (ShimCurve, T07/T10 branches) and `data/cmfdata/cmfdata.txt` (44.4 MiB, gitignored, regenerable via `make_cmfdata.py`).

---

# 8. After sign-off — action checklist

In dependency order:

1. **Record verdicts**: set approved tickets' frontmatter `status: review → done`; put D-answers that are Q-answers into `QUESTIONS.md` (Q4 ⟐, Q2.3, Q15.3, …). Route D8/D10 to Eran.
2. **Merge/push ShimCurve** (your push, per the hard rules): the stack `T28 → T29 → T10 → T07 → T09` first (T04 is building on its tip), then `T01 → T02 → T03`, then `T13`. Note T13 also left a one-line path handoff for `tablesX0DN.m:119` that T04 (in flight) is picking up.
3. **Push lmfdb** `ticket/T24-frontend` (merge with current `shimura_curves` first — it has since merged main).
4. **Post the issue-#6 comment** (D11) once T07 is pushed.
5. **Run the two `create_table` calls** (D18) — safe now, independent of T27.
6. **Decisions that unblock in-flight work fastest**: D20 (Clabel — lets T24+T03 close coherently), D26 (factorization — T04 wants the schema call), D5 (formally green-lights T27 planning).

The wave-2 queue behind these: T06 wave (hygiene + the single reconciled polarized regen, post-T08), T20 (elliptic points, has T19's crash-site intel), T11, T15, T12, T02/T03 re-key at T27.
