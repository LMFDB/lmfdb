---
id: T13
title: Make jacobian_decomp production-ready + acquire cmfdata
status: review
owner: wave1-D-opus
priority: P1
tier: 2
repos: [ShimCurve, db-readonly]
depends_on: []
questions: [Q13]
---

## Context

`code/jacobian_decomp/` computes isogeny decompositions of Jac(X_H) by Jacquet–Langlands + trace matching:

- `helpers.m` — `CMFLoad` reads an external **`cmfdata.txt`** (`:66`; record format `cmfrec` at `:13-19`) which is **not in the repo**; `ClassNumberTable` caches to `xgclassnumbers.dat` (also absent, but auto-generated).
- `indefinite.m` — trace formula (`IndefiniteTrace`) + `HTraces(H,...)` (Frobenius traces of X_H over F_q).
- `level_dividing_D.m` — local GL₂(O_p) models for p | gcd(D, N·M) (`BuildG`, `BuildGSubgroup`, `FindI/FindJ/Findc` with retry-style string errors "increase NumTries"/"increase Bound or NumTries").
- `newform_decomp.m` — `JLDecomposition` (for J₀^D(N)) and `ShimuraNewformDecomposition(H,...)` (general X_H): solves a linear system matching H-traces against newform traces; failure codes −1 (genus 0), −2 (linear-system), −3 (cutoff) documented at `:62`; stray debug `print` at `:74, :83-86`.

This is the machinery for the currently-null columns `newforms, dims, mults, conductor, rank, simple, squarefree, genus_minus_rank, traces, trace_hash` (T14 does the mass computation; this ticket makes the tool trustworthy). The 339 rows that already have decomposition data came from the X₀(D;N) arm (`tablesX0DN.m:1` "requires downloading the appropriate cmf data") — the same cmfdata dependency.

## Steps

1. **cmfdata.txt**: reverse-engineer the exact format from `CMFLoad`/`cmfrec` (fields, separators, sort). Write `code/jacobian_decomp/make_cmfdata.py` (sage -python) that dumps it from the LMFDB: `db.mf_newforms` (+ `db.mf_hecke_traces` or the `traces` column) restricted to weight 2, trivial character, level ≤ a parameter; include whatever `cmfrec` needs (per Q13.2 — likely label, level, dim, traces list, AL eigenvalues from `fricke_eigenval`/`atkin_lehner_eigenvals`). Document the command and generate a file covering level ≤ 4000 (enough for D·N·M in current scope) into `~/claude/ShimCurve/data/cmfdata/` (gitignored if large; note size).
2. Remove debug prints; convert string/int error returns into Magma errors or `<ok, result, reason>` returns consistently; make the retry parameters (`NumTries`, `Bound`) self-escalating with a hard cap instead of asking the caller to retry.
3. Determinism/robustness pass on `ShimuraNewformDecomposition`: the linear system must be checked for unique solvability (currently what happens on underdetermined systems? −2?); raise the trace cutoff adaptively until the solution is unique or the cap hits; assert Σ dims·mults = genus at the end (fundamental consistency check).
4. Validate against ground truth: the 339 devmirror rows with `dims/mults/newforms` populated (X₀(D;N) rows). Recompute ≥ 20 of them across different D (query: `select label,"discB","discO",newforms,dims,mults from gps_shimura_test where dims is not null limit 20;`) and require exact agreement. Also validate `JLDecomposition` for 2-3 classical cases from the literature (e.g. J₀^6(1) trivial, a known D=6 N=5 or D=10 decomposition).
5. Wire a convenience intrinsic `JacobianData(H, G, O, mu, N) -> rec` returning all columns T14 needs (newforms sorted by `CMFLabelCompare`, dims, mults, conductor = product/factored per Q13.1, simple, squarefree), leaving rank/trace_hash to T14 (they need LMFDB analytic-rank data / the hash algorithm, python-side).
6. Add `tests/regression_jacobian_decomp.m` (one small X_H with known decomposition; keep < 2 min).

## Acceptance criteria

- `make_cmfdata.py` reproducibly generates the file; format documented in the script header.
- 20-row ground-truth validation passes; Σ dims·mults = genus asserted globally.
- No debug prints; failure modes are structured; regression test green.

## Log

- 2026-07-16: ticket created from survey.

- 2026-07-22 (wave1-D-opus): worked the ticket in worktree `ticket/T13-jacobian-decomp`
  (based on T29). Summary of deliverables, findings, and flags below.

  ### cmfdata dump (Steps 1-2, Q13.2)
  - Wrote **`code/jacobian_decomp/make_cmfdata.py`** (`sage -python`), parametric on
    `--level-bound`, `--trace-depth`/`--tiered`, `--weight`, `--out`, `--lmfdb-root`. Format
    (fixed by `helpers.m` cmfrec/CMFLoad) is `label:level:cond:dim:rank:traces`, one Galois
    orbit per line, `traces` an eval-able Magma list. Column mapping from `db.mf_newforms`
    (weight 2, `char_order=1` trivial character): `cond = char_conductor` (**mf_newforms has NO
    `conductor` column**; JLDecomposition's `cond ne 1` test is the trivial-character test),
    `rank = analytic_rank` (the Galois-orbit **analytic** rank), traces = the `traces` column.
    AL/Fricke eigenvalues NOT dumped (superseded, per Q13.2). Full header documents format + commands.
  - **Materialized `data/cmfdata/cmfdata.txt`** (T28 `DataFile` location; gitignored): near-term
    corpus `--level-bound 2000 --trace-depth 1000` = **15,899 forms, 44.4 MiB** (1000 traces each,
    0 NULL ranks). Covers D=6 enhanced (discO*N^2<=216), D=10/15/21 headroom (discO<=50, N<=6 ->
    <=1800), and all 339 coarse X0(D;N) ground-truth rows (max discO=998). Verified CMFLoad reads it
    in ~0.1s (the divisibility filter runs before `eval`).

  - **⟐ trace-length caveat VERIFIED on the devmirror (2026-07-22).** `mf_newforms.traces` length is
    itself tiered by LMFDB: **1000** coefficients for level <~ 1000, **~3000** for mid-level, but only
    **100** for level >~ 10000-20000; and **`analytic_rank` is NULL for level >= 10001**. Sturm bound
    Sturm(L)=floor(L/6 * prod_{p|L}(1+1/p)) (wt 2): near-term needs only Sturm(1800)=720 primes, and
    every level<=2000 form has >=1000 traces + a populated rank, so the near-term dump is fully
    sufficient. A **deep production dump is NOT** (see estimate below): above level ~10000 the default
    column has only 100 traces and no analytic_rank, so extended a_p must be pulled/derived from
    `mf_hecke_nf` (which exists on the mirror). The `-3` "cutoff reached" return is the intended
    self-heal hook (regenerate deeper + retry) and is wired accordingly.

  ### M-awareness (Step 3, Q13.3)
  - **CMFLoad** (`helpers.m`): added optional `discO`; default `levelbound = discO*N^2` when discO
    supplied, else `D*N^2`; default `cmfdatafile = DataFile("cmfdata/cmfdata.txt")`. Backward-compatible
    (tablesX0DN passes `levelbound` explicitly). Every contributor to Jac(X_H) has level | discO*N (⊆
    discO*N^2), so the divisibility pre-filter loads a correct superset.
  - **ShimuraNewformDecomposition** (`newform_decomp.m`): candidate filter `level <= D*N^2` ->
    `level <= discO*N^2` via a new optional `discO` (defaults to D = maximal order).
  - **JLDecomposition left as-is on purpose.** Its second argument is the **Eichler/order level** of
    the classical X_0^D(N) (tablesX0DN calls it that way, with congruence level 1), so
    `AmbientLevel = D*N = discO` is already correct; changing it to `discO*N` would double-count M.
    Clarified this in the docstring. (The Q13.3 phrasing "AmbientLevel := D*N -> discO*N" targets the
    general enhanced path, which lives in ShimuraNewformDecomposition's filter, not JLDecomposition.)
  - **⟐ HTraces / level-M check -- FINDING A (flag).** Verified `IndefiniteTrace` (`indefinite.m`):
    its `O := MaximalOrder(B)` (line 8) is its ONLY reference to O and is **never used again** -- the
    embedding numbers come solely from `RamifiedPrimes(B)` + congruence level N. So HTraces is a
    **maximal-order** trace formula with **no input path for an Eichler level M** coprime to N. The
    M-aware candidate-filter/levelbound fixes are necessary but **not sufficient**: for Eichler rows
    (discO=D*M, p|M, p∤N) the HTraces *target values themselves* are not M-corrected. Correcting the
    Eichler local embedding factors in IndefiniteTrace is a separate task (needs O and the p|M local
    orders threaded in).

  ### Robustness (Step 2-3)
  - Removed all stray debug prints (`newform_decomp.m` old `print(Q)` / `print(A);print(b);print(e)`
    / `print(A);print(b)`); converted the one string-return in `indefinite.m` ("needs to input the
    genus...") to an `error`.
  - **Fixed a latent cutoff bug** in ShimuraNewformDecomposition: old `cutoff = #primes<=NthPrime(m)`
    (= m) let the loop access `traces[NthPrime(maxi)]` past the list end; corrected to
    `cutoff = #PrimesInInterval(1, m)` (traces are read by prime VALUE, so the largest safe prime is
    <= m = shortest trace list). Added guards: empty candidate set -> `-2`; non-integral/negative
    multiplicity vector -> `-2`; kept `assert sum dims*mults = genus`. Failure protocol is now
    consistent (`-1` genus 0, `-2` data/linear-system, `-3` cutoff) with empty sequences.
  - **FindI/FindJ** (`level_dividing_D.m`): replaced the `return false,"increase NumTries"` string
    antipattern with **self-escalating** search (Bound/NumTries grow geometrically to
    `BoundCap=64, TriesCap=2e6`), raising a descriptive `error` only if the caps are exhausted.

  ### Convenience intrinsic (Step 5) + representation gap
  - Added **`JacobianData(H, G, O, mu, N : g:=-1, cmfdatafile:="") -> Rec`**: computes
    `g = EnhancedGenus(H,G,O,mu)` (genera.m), reads discB/discO off O, loads cmfdata M-aware, calls
    ShimuraNewformDecomposition, and returns a record `<newforms (CMFLabelCompare-sorted), dims,
    mults, conductor (factored prod level^(mult*dim), Q13.1), simple, squarefree, genus, rank, code>`
    (rank/trace_hash left authoritative to T14 python-side per the ticket; rank included as the
    cmfdata analytic-rank sum for convenience).
  - **FINDING B (flag) -- representation gap, and FINDING C (flag) -- trace-formula bug.**
    ShimuraNewformDecomposition/HTraces are **called nowhere in the repo** (JacobianData is the first
    caller); the trace arm was never validated. Two blockers found while validating it:
    - **B (representation):** the enhanced enumeration builds `H ⊆ GL(4,Z/N)` (EnhancedElementInGL4modN),
      but `IndefiniteTrace` builds `beta ∈ GL(2,Z/N)` and evaluates `f(beta)` with `f = perm char of
      GL(Degree(H),·)` -- i.e. it **requires `H ⊆ GL(2,Z/N)`** (or the local GL2(O/p^e) model when
      p|gcd(D,N)). The GL4->GL2 enhanced-representation bridge does not exist in the repo; it is the
      outstanding T14 integration step (documented in JacobianData's docstring).
    - **C (math bug):** even bypassing B with a hand-built GL(2,Z/5) Borel `H` (= X_0^6(5)), HTraces
      does **not** reproduce the known answer. HTraces at p=7,11,13,17,19,23,29,31 gives
      `[2,6,8,12,6,12,12,20]`, but Jac(X_0^6(5)) = 30.2.a.a has a_p = `[-4,0,2,6,-4,0,-6,8]`; and for
      the genus-0 curve X_0^6(1) (H=GL2) HTraces gives `[4,6,6,9,9,12,15,16]` where a trivial Jacobian
      must give all-zeros. So `IndefiniteTrace`'s Eichler-Selberg trace formula is **incorrect/unfinished**
      (the values look like an embedding-number mass, ~ (p+1)/2 with class-number corrections, not the
      cuspidal Frobenius trace). **This blocks T14's enhanced-curve decomposition** and needs debugging
      against Eichler / Voight *Quaternion Algebras* Ch. 30 before the trace-matching arm can be trusted.
      (My robustness cleanup is correct plumbing; the bug is in the math, upstream of it.)

  ### Ground-truth validation (Step 4)
  - **JLDecomposition arm: 32/32 devmirror rows agree EXACTLY** (script kept in scratchpad),
    spanning **discB = 6..403, Eichler + maximal orders, genus 0..31, analytic rank 0..3, dims 1..10,
    multiplicities 1..2** (well over the 20-row bar). Rows matched by INVARIANT data `<discB, discO,
    genus, rank, ...>`, not by shipped shimura label (labels predate the canonical sort; note the CMF
    *newform* labels used inside are stable, only the shimura-curve labels are not). This
    simultaneously validates the dump's label/level/cond/dim/analytic_rank columns. Classical checks
    included: X_0^6(1) genus 0 trivial; X_0^6(5) -> 30.2.a.a; X_0^14(3) -> {14.2.a.a x2, 42.2.a.a};
    X_0^35(1) -> {35.2.a.a, 35.2.a.b(dim2)}.
  - **Regression test** `tests/regression_jacobian_decomp.m` (wired into `run_quick.m`): JLDecomposition
    on 4 known rows + Sum dims*mults=genus + ShimuraNewformDecomposition structured-return (no-crash) +
    FindI self-escalation; **guards on cmfdata presence (TestSkip if absent)** so run_quick stays green
    on a bare checkout. `run_quick.m` GREEN: **0 failures, 0 skips, ~4s** (my block 22/22 PASS).

  ### Handoffs
  - **tablesX0DN.m:119 (agent A / T04) -- path handoff.** It hardcodes
    `cmfdatafile := "./code/jacobian_decomp/cmfdata.txt"` (violates T28: data belongs under `data/`).
    The materialized file now lives at `data/cmfdata/cmfdata.txt`. Exact diff:
    `CMFLoad(D, N : cmfdatafile := "./code/jacobian_decomp/cmfdata.txt", levelbound:=D*N)`
    -> `CMFLoad(D, N : levelbound:=D*N)` (uses the new `DataFile` default). Its `levelbound:=D*N` is
    already M-correct for the coarse arm (discO=D*N, congruence 1) -- no other change needed. **Until
    that lands I left a gitignored bridge symlink** `code/jacobian_decomp/cmfdata.txt ->
    ../../data/cmfdata/cmfdata.txt` so the current reader keeps working.
  - **T14:** (1) enhanced trace-matching is blocked on Findings B (GL4->GL2 bridge) and C (IndefiniteTrace
    math bug) -- until fixed, only the JLDecomposition (coarse) arm is trustworthy; (2) for the mass run,
    regenerate cmfdata with a higher `--level-bound` covering the actual `discO*N^2` reached, and use
    `--tiered` (extended a_p from `mf_hecke_nf` for level >~10000 where the default column is short and
    analytic_rank is NULL); (3) rank/trace_hash stay python-side.

  ### Production-scale estimate (Step 1, Q13)
  - Full `discO <= 1000, N <= 6` -> level <= 36000 = **574,497** weight-2 trivial-character forms
    (vs 15,899 at level<=2000). **NOT materialized** (per ticket -- estimate only).
    - **Default-depth** (what the `traces` column offers today): 450,908,008 trace values ->
      ~**1.3 GB** at ~2.93 bytes/value. But **446,398 forms (77.7%) have NULL analytic_rank** and only
      ~100 traces (every level>=10001 form), so a default-depth dump is unusable for the deep tiers.
    - **Sturm-correct** (`--tiered`, depth min(avail, Sturm(level*36)) capped at Sturm(36000)=14400):
      since level*36>=36000 already for level>=1000, most of the 574k forms cap at ~14400 coefficients
      -> ~8e9 trace values, order **25-30 GB**, and requires (a) extended a_p from `mf_hecke_nf` above
      level ~10000 and (b) computing the 446,398 missing analytic ranks. Impractical as one monolith;
      the intended path is default/near-term depth + the `-3` self-heal (extend only candidates that
      actually hit cutoff) during T14's mass run.

  Files changed (all under my ownership): `code/jacobian_decomp/{helpers,indefinite,level_dividing_D,
  newform_decomp}.m`, new `code/jacobian_decomp/make_cmfdata.py`, new
  `tests/regression_jacobian_decomp.m`, `tests/run_quick.m` (+1 load line), `.gitignore` (+3 artifacts).
  Did NOT touch enumerate-H.m or tablesX0DN.m (agent A).

  **Status -> review.** Committed as `df63e42` on `ticket/T13-jacobian-decomp`. Acceptance criteria
  met: make_cmfdata.py reproducibly generates the documented-format file; 32-row (>20) ground-truth
  validation passes exactly; no debug prints; failure modes structured; `run_quick.m` green (0/0).
  Left for David/review: Finding C (IndefiniteTrace trace-formula bug) and Finding B (GL4->GL2 bridge)
  are new discoveries beyond the original "productionize" scope and warrant a follow-up ticket, since
  together they block T14's enhanced-curve (trace-matching) decompositions; the coarse
  JLDecomposition arm is fully trustworthy and ready for T14 now.
