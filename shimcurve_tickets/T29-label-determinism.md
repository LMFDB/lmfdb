---
id: T29
title: Make labels deterministic and reproducible (BLOCKS all regeneration+reload)
status: review
owner: claude (session 2026-07-16/17)
priority: P0
tier: 1
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q15]
---

## Context — measured, not hypothesized

Running the current pipeline twice on identical inputs produces **different label assignments**. Probe (2026-07-16, worktree of `main` @ 5e7c460):

```
AttachSpec("spec");
B := QuaternionAlgebra(6); O := MaximalOrder(B);
tr, mu := HasPolarizedElementOfDegree(O,1);
subs := GenerateDataForGerbiestSurjectiveH(O,mu,1);
WriteHeaderAndSubgroupsDataToFile(subs, O);
```

Two consecutive runs of exactly this, and the committed `data/genera-tables/genera-D6-deg1-N1.m`, disagree: the curve with `autmuO_norms = {6,1,1,1,1,1}` (generators `{{2,-2,-3,1,0,0,0,0},...}`) is labeled `6.1.1.2.0.a.1` in one run and `6.1.1.2.0.b.1` in the next — the `a`/`b` assignment **swaps between the two genus-0 index-2 curves**. Same set of curves, same invariants; only the label↔curve correspondence moves.

### Why this is P0

LMFDB labels are permanent public identifiers (cited in papers, linked from other object pages). Worse, operationally: **every Tier-1/2 ticket that regenerates data stages a `update_from_file` keyed by label** (T07, T11, T12, T14, T15, T17, T18). If labels aren't reproducible, those updates silently attach data to the *wrong curve*. Any regeneration+reload is therefore unsafe until this is fixed.

### Suspects (diagnose before fixing)

1. **Sort key is not a total order.** `updateLabels` (`code/level-structure/enumerate-H.m:288`) groups by `coarse_label` and sorts by `PermutationCharacter`, then assigns `coarse_class` via `Base26Encode` (`:139`). Two distinct H with equal permutation character tie; the tie is broken by input order → whatever `Subgroups(G, KG)` returned. The two swapping curves here have *different* `autmuO_norms` and generators, so they are distinguishable — the sort key just doesn't see it. Modular curves solve exactly this with a **`tiebreaker` column** (it appears in the shimura frontend's "unused cols" comment block, `~/claude/lmfdb/lmfdb/shimura_curves/main.py:326-354` — the design intent exists but was never implemented).
2. **`Subgroups(G, KG)` ordering** is not guaranteed canonical across runs.
3. **μ nondeterminism** (`HasPolarizedElementOfDegree` via Magma's `Embed` — see T08): a different μ gives a different `Aut` map, hence a different G, hence a different subgroup enumeration. **T08's canonical μ is a prerequisite for full determinism** — coordinate: do the diagnosis and tiebreaker design here, land the final determinism check after T08.

## Steps

1. **Isolate the source.** Fix μ by hardcoding the committed value (read it from `quaternion-orders-polarized`), rerun twice: if labels still swap, the cause is (1)/(2) not (3). Then check whether `Subgroups(G,KG)` returns a stable order across runs with identical μ. Record the findings in the Log and under Q15 in QUESTIONS.md.
2. **Design a total order** (needs Q15's blessing on what's canonical): extend the sort key so it never ties — proposal: `(PermutationCharacter, sorted autmuO_norms, sorted generator Eltseqs lexicographically, ...)` with a final documented tiebreaker that is intrinsic to the subgroup (not to enumeration order). Mirror modular curves' `tiebreaker` semantics where possible; if a `tiebreaker` column is warranted, add it to T04's canonical schema.
3. **Implement + prove**: generate D=6 deg-1 N=1 **three times**, assert byte-identical files. Then the full D=6 corpus twice (background; ~1h) — byte-identical.
4. **Reconcile with shipped data — the critical question**: regenerate the D=6 corpus and compare the label↔invariant mapping against the devmirror rows (join on invariants: genus, index, autmuO_norms, generators). Report in the Log: (a) do the shipped labels match the new deterministic ones? (b) if not, how many rows move? This decides the reload strategy for T27: **matching ⟹ label-keyed `update_from_file` is safe; not matching ⟹ the whole corpus must be reloaded atomically via `copy_from` into a fresh table, and every existing label reference (the 304 pictures keyed by `psl2label`, the T01 label map, any external citation) must be remapped.** Flag this prominently for David either way.
5. Add a determinism regression to `tests/`: generate a small case twice in one session, assert identical records (cheap: D=6, deg 1, N=1 ≈ 5s).

## Acceptance criteria

- Root cause identified with evidence (which of the three suspects, demonstrated).
- Three consecutive full-corpus generations are byte-identical; determinism test in `tests/`.
- The shipped-vs-regenerated label reconciliation is documented with counts, and a reload strategy recommendation is written into the Log for T27.

## Log

- 2026-07-16: ticket created. Probe evidence above (two runs → a/b swap on `genera-D6-deg1-N1.m`) obtained in a throwaway worktree; main checkout untouched.
- 2026-07-16 (claude): **Implemented**, ShimCurve branch `ticket/T29-label-determinism` (commit 97bef4f, stacked on T28). Design per David (Q15): primary = permutation character (Gassmann classes, as before), tiebreaker 1 = Atkin-Lehner content, tiebreaker 2 = canonical generators modeled on Sutherland's GL2CanonicalGenerators. New `code/level-structure/canonical-sort.m`: `ALContent` (sorted multiset of squarefree Aut-component norms over cosets of H∩(O/N)ˣ — a conjugacy-class invariant, unlike the generator-based `autmuO_norms` column), `CanonicalizedGenerators` (greedy lex-minimal generating sequence), `CanonicalGeneratorsKey` (minimized over the G-conjugacy class; computed lazily, only on residual ties). `updateLabels` rewritten accordingly; rows now written in sorted label order.
- Two more leaks found by testing, both fixed, both **semantic changes needing David's sign-off**: (1) `is_split` was representative-dependent (`H ∩ Image(Ahom)` is not conjugation-invariant — its value flipped between identical runs); now true iff SOME conjugate of H splits against the standard section. (2) `G1` (feeds psl2label + scalar_label) was `O1_subs[last]` — at N=3 the filtered list contains several incomparable maximal det-trivial subgroups, so the choice was arbitrary as well as unstable; now `G1 := Kernel` of the reduced-norm determinant hom on G (the SL2-analogue).
- 2026-07-17 (claude): **Full-corpus verification complete** (all 15 (deg,N), two independent passes): identical labels and identical values in every column except the presentation-dependent encodings `generators` (Ngens rep) and `ram_data_elts` (coset-numbering-dependent Lehmer codes). Canonicalizing those two encodings (canonical conjugate + canonical coset numbering) is the remaining follow-up; NOT needed for label-keyed update safety. Regression test `tests/regression_label_determinism.m` added to run_quick/run_all; suite green. Timing note: full corpus now ~19 min/pass on this machine (deg6 N6: 407s vs the historical 1956s).
- **Reconciliation vs shipped data (step 4, full corpus): 1614/2198 rows (73%) change which curve their label names** under the canonical sort; `psl2label` changes on 2158/2198 rows (98%, driven by the canonical G1); `scalar_label` follows; `is_split` changes on a handful. **Recommendation for T27: full reload via copy_from with canonical labels — label-keyed update_from_file against the OLD table is unsafe. The 304 `shimcurve_pictures` rows are keyed by psl2label and must be re-keyed at reload.** Formal sign-off = Q15.3 / T27.

- 2026-08-01 (opus session): **David's semantic sign-offs recorded** — see
  [DECISIONS.md](DECISIONS.md).
  - **[D3] `is_split` BLESSED**: "some conjugate of H splits against the standard section".
  - **[D4] `G1` BLESSED**: the kernel of the reduced-norm determinant hom on G.
  - **[D5] APPROVED (= the formal Q15.3 sign-off)**: T27 is a **full atomic `copy_from`
    reload** with the rename, and the 304 `shimcurve_pictures` rows **re-key at reload**.
    Label-keyed `update_from_file` against the current table is permanently off the table.
  QUESTIONS.md Q15 updated accordingly.
  **Ticket stays `review`**: [D2] (does the canonical sort implement Q15's design as intended)
  is still unanswered, as is [D1] for T28. The math is blessed; the code review is not yet in.
