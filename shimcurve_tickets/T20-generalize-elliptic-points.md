---
id: T20
title: Generalize elliptic-point counting beyond D=6
status: in-progress
owner: wave2-J-fable
priority: P1
tier: 3
repos: [ShimCurve]
depends_on: [T19]
questions: [Q7]
---

## Context

`EnhancedEllipticPoints(sigma)` (`code/level-structure/genera.m:18-34`) is documented **"Only works for discriminant 6!"**: it assumes the ramification triple σ is indexed by three branch points of orders `bottom := [2,4,6]` — i.e. that the bottom orbifold (quotient of X(D;1) by the full enhanced normalizer-plus group) is the (2,4,6)-triangle for D=6/deg 1. The ν₂/ν₃/ν₄/ν₆ columns are only correct under that assumption; even D=10/15 (unlocked by T19) would be wrong. Note `EnhancedGenus` (`genera.m:4`) is already general (pure Riemann–Hurwitz) — only the ν-bucketing is D=6-specific. Also note `RamificationData`/`EnhancedRamificationData` (`enumerate-H.m:171`, `genera.m`) produce σ **relative to the same assumed bottom** — the generalization must produce (bottom signature, σ over its branch points) as a pair.

Q7 decides the mathematical route (Ogg-style counting as in `X0DN_code.m` extended to the enhanced quotient, vs. computing the Fuchsian signature of the bottom group directly) and the schema question (can ν-orders other than 2,3,4,6 occur → list-of-pairs column?).

## Steps

1. Compute the bottom signature generally: given O, μ (and T19's generators), determine the signature of Γ = image of the enhanced normalizer-plus group — candidates: (a) Magma `FuchsianGroup` signature of the group generated (if representable); (b) formula: start from the signature of Γ⁰(D·M) (classical, `SignatureX0DN` in `X0DN_code.m`) and account for the Aut_{±μ}(O)-quotient via fixed-point counts (`OggCountFixedPoints`, `SignatureX0DNmodAtkinLehnerElement` at `code/tables/signatures_single_AL_element_X0DN.m:186` already do single-element AL quotients — the needed extension is quotients by the full subgroup W ≤ Aut, composing fixed-point data via Burnside/Riemann–Hurwitz through the tower). Follow Q7.1.
2. Rework the σ plumbing: `EnhancedRamificationData` should return σ indexed by the computed bottom branch points (arbitrary count k, orders e₁..e_k, plus bottom genus g₀); `EnhancedGenus` gets the (g₀, orders) as input (RH with 2g₀−2 base term — currently hardcoded −2·d? check line `rhs := -2*d + ...` assumes g₀=0: generalize).
3. ν-columns: per Q7.3, either keep ν₂/ν₃/ν₄/ν₆ and assert no other orders occur in scope, or migrate schema to `elliptic_orders integer[]` pairs (coordinate with T04's canonical schema and note the frontend display `web_curve.py:657`, `main.py:601-604` reads nu2..nu6).
4. Validation battery:
   - D=6 corpus regenerates **identically** (all 2,198 rows byte-equal on genus + ν columns).
   - Coarse checks: for the trivial H at (D,N) with deg 1, genus and e₂/e₃ must match `SignatureX0DN(D,N)` for D ∈ {6,10,15,21,26}, N ∈ {1,3} (X0DN_code is the independent oracle).
   - Gauss–Bonnet: the existing area assert (`enumerate-H.m:280-283`) generalizes — keep it on.
5. Tests: add a D=10 genus/ν regression case with the oracle values.

## Acceptance criteria

- D=6 byte-identical regeneration; oracle agreement for D ∈ {10,15,21,26}; area assertion holds corpus-wide.
- Documented decision (with Q7) on the ν-schema.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave2-J-fable): claimed. Worktree /Users/roed/claude/shim-wt/T20, branch
  `ticket/T20-elliptic-points` stacked on T19 @ a8c1166. Read T19 Log in full + Q7/Q8/Q4.
  T30 intel absorbed: `EnhancedGenus(H,G,O,mu::AlgQuatOrdElt)` (genera.m:38) calls
  `EnhancedRamificationData(...mu::AlgQuatElt)` (genera.m:88) — mismatched μ types make the
  4-arg EnhancedGenus uncallable with either type ("Bad argument types"). My rework
  standardizes genera.m μ arguments on **AlgQuatElt** (what HasPolarizedElementOfDegree
  returns) with AlgQuatOrdElt delegating overloads, matching the enumerate-H.m convention.
  Once this lands, T30's JacobianData `g := genus` input bypass can be removed (T14/T30
  follow-up — not edited here, jacobian_decomp is T30's).
- 2026-07-22 (wave2-J-fable): **s3 = e3 VERDICT: CONFIRMED REAL BUG, now fixed.**
  `SignatureX0DNmodAtkinLehnerElement`, else branch (m ≡ 1,2 mod 4, m ∉ {2,3}): w_m fixes
  no order-3 point when Q(√−m) ≠ Q(√−3), so the e3 order-3 points pair up: s3 = e3/2, not
  e3 (mirror of the m ≡ 3 mod 4 branch, which was already right). Evidence
  (t20-scripts/verify_s3.m): concrete value **X₀(10;1)/w₅: code returned
  (0; 2,2,3,3,3,3), Gauss–Bonnet defect 4/3; true signature (0; 2,2,3,3)** (genus 0 +
  area 1/3 force s3 = 2). Sweep: 920 Hall quotients (D ≤ 100 sqfree even-ω, N ∈
  {1,5,7,11,13}): 139 GB violations, ALL in the else branch, ALL with e3 > 0, ALL repaired
  exactly by s3 := e3/2. Fixed closed form vs T19's independent
  ExpectedAtkinLehnerQuotientSignature (Ogg cone data): 90/90 agree (maximal orders,
  |W|=2, D ≤ 100). Fixed in BOTH copies: code/X0DN/X0DN_code.m:236 (attached) and
  code/tables/signatures_single_AL_element_X0DN.m:238 (unattached duplicate).
  Blast radius: genus outputs were never affected (Ogg Eqn 3 uses only the fixed-point
  count); the shipped coarse-table ν columns are also clean (tablesX0DN.m gets ν from
  Magma's EllipticInvariants(FuchsianGroup), not from this intrinsic). Affected: any
  signature-table artifacts from SignatureTable(), and X0DN_code.m:1366's g_quot_min is
  genus-only (unaffected). This oracle is now safe for T20 validation.
- 2026-07-22 (wave2-J-fable): **core generalization implemented** (commit c74ef39 on top of
  985c58e):
  - `EnhancedBottomSignature(O, mu)` (normalizer-generators.m, new): cone orders + genus of
    the enhanced bottom X(D;M)/W_mu, **certified by requiring source (a) == source (b)**:
    the <order in B×/Q×, AL class> multiset of the actual NormalizerPlusGenerators(O,mu)
    generators must equal Ogg's cone data (ExpectedAtkinLehnerQuotientSignature), plus a
    Gauss–Bonnet re-assert on the generator orders. Memoized on O (attribute). Positive-
    genus bottoms and non-spherical (fallback) caches are REFUSED with precise errors —
    never wrong ν.
  - genera.m: `EnhancedGenus(sigma, g0)` (RH with d·(2g0−2) base term; 1-arg form = g0=0
    kept), `EnhancedEllipticPoints(sigma, bottom)` (general ν-bucketing, asserts cone
    orders ∈ {2,3,4,6} = the φ(n) ≤ 2 theorem of Q7.3, and cycle-length | cone-order;
    1-arg legacy form = [2,4,6]), `EnhancedRamificationData` now returns (sigma, bottom,
    g0) (extra return values — old single-value callers unaffected). **T30 type bug
    fixed**: 4-arg EnhancedGenus/EnhancedRamificationData standardized on mu::AlgQuatElt
    with AlgQuatOrdElt delegating overloads; verified callable both ways. T30's
    JacobianData genus-input bypass can now be retired (T14/T30 follow-up, not done here).
  - genera.m:66 (EnhancedCosetRepresentation): `assert #G/#Gplus eq 2` → `eq EulerPhi(N)`
    — SAME content as T10's fix on the parallel chain (Q4), applied here so the merge
    reconciles cleanly.
  - **enumerate-H.m edits (for the merge, exact regions)**: ONLY inside createRecord —
    (i) after the `sigma := RamificationData(...)` line: added
    `bottom, g0 := EnhancedBottomSignature(O, mu);` and `genus := EnhancedGenus(sigma, g0);`
    replacing `genus := EnhancedGenus(sigma);` (~line 232-240); (ii) ~line 300:
    `nu := EnhancedEllipticPoints(s`ram_data_elts, bottom);` (was 1-arg). The writer block
    (~:434+) and the Gauss–Bonnet area assert are UNTOUCHED (the assert generalizes as-is
    and stays on corpus-wide).
  - Sanity (t20-scripts/sanity_bottom.m): D=6 deg 1/2/6 all give bottom (2,4,6) g0=0 — the
    D=6 corpus is invariant under T20 (W_mu = full at all three degrees, confirming T19's
    regression gate); D=10 → (2,2,2,3); D=15 → (2,2,2,6); memoization instant.
- 2026-07-22 (wave2-J-fable): **tests green: 94 PASS / 0 FAIL / 0 SKIP** (T19's 64 + 30
  new in tests/regression_elliptic_points.m, wired into run_quick). New test covers: s3
  fix values, GB sweep of closed-form signatures, bottom signatures 6/10/15, loud refusal
  behavior, general ν/genus at D=10 (H=G and full-congruence H vs SignatureX0DN(10,1)
  oracle: genus 0, e3=4 ✓), T30 type fix both mu types.
- 2026-07-22 (wave2-J-fable): **degenerate-tuple wall at W_mu = {1,D}, partial rescue**:
  - D=21 deg-1 and D=26 deg-1 (both bottoms (0;2⁶)) initially refused: T19 caches held
    validated FALLBACK lists (every default-budget spherical tuple degenerate, [G:G1]=8
    mod 4 instead of 2).
  - t20-scripts/rescue_spherical.m (budget escalation MaxPool 24→40, MaxTuples 200k→400k,
    Skip 0..24, revalidating each candidate mod 3 AND 4): **D=21 RESCUED** — a validated
    spherical (0;2⁶) system found and cached (data/normalizer-gens/21-W1_21-bBC7DA0.m now
    spherical=true validated=true); EnhancedBottomSignature(21, deg-1) returns
    [2,2,2,2,2,2] g0=0. **D=26 NOT rescued**: ~50 certified systems across both rungs ALL
    fail mod-4 validation with the identical [G:G1]=8 signature — systematic, not random;
    within-budget search exhausted. ⟐ For Eran: is there a genuine obstruction for
    X(26)/w26 (all small-height product-scalar involution 6-tuples degenerate), or just
    tall generators? The pipeline REFUSES D=26 deg-1 loudly (correct; never wrong ν).
  - t20-scripts/probe_degrees.m: alternative degrees give FULL W_mu and working certified
    bottoms: D=21 deg-3 → full X* (2⁵); D=26 deg-2 and deg-13 → full X* (2⁵). So D=26 is
    enumerable at deg 2/13 today; only its deg-1 (W={1,26}) bottom is blocked.
- 2026-07-22 (wave2-J-fable): **positive-genus-bottom characterization done**
  (t20-scripts/characterize_bottoms.m → t20-artifacts/bottom-characterization.csv,
  1,968 (D,W) pairs = every W of order 2/4 + full W over maximal orders D ≤ 1000):
  **151 genus-0 vs 1,817 positive-genus**. Smallest positive-genus: (D=14, W={1,7}, g=1).
  Deg-1-relevant (D ∈ W, |W| ≤ 4): 600 positive-genus pairs, smallest (57,{1,57},g=1) —
  matches T19's independent finding (deg-1 W_mu-quotients of D=57/82 positive genus).
  These all hit the loud EnhancedBottomSignature stub; hyperbolic generators remain
  future work (characterized-but-stubbed per ticket step 3). **Implication for T21/T22
  production scope**: most of D ≤ 1000 needs either hyperbolic-generator support or
  μ choices with genus-0 W_mu-quotients (the CSV says exactly which).
- 2026-07-22 (wave2-J-fable): **validation battery — oracle spread GREEN**:
  - **D=10 deg-1 (headline, t20-scripts/battery_D10.m)**: N=3 full enumeration now
    COMPLETES with ν columns — 88 records, 1.8s, per-record Gauss–Bonnet area assert
    passed corpus-wide, genus distribution {0³¹,1²⁸,2²²,3⁵,5²} (+5 level-1 rows = T19's
    93 with genera {0³⁶,…} exactly). Oracle rows found: bottom X*(10) = (0;2,2,2,3) →
    ν (3,1,0,0); X(10;1) = SignatureX0DN(10,1) = (0; 3,3,3,3) → ν (0,4,0,0);
    X₀(10;3) = (1; 3,3,3,3) at 4× the index. N=1 tower: the three single-AL rows
    X(10)/w_m, m ∈ {2,5,10}, ALL come out (0; 2,2,3,3) = the FIXED closed form — the
    σ-pipeline and the s3 fix confirm each other independently. Headline files:
    data/genera-tables/genera-D10-deg1-N{1,3}.m, copies in t20-artifacts/ — PROVISIONAL
    pending T27 reload (labels from the T29 canonical sort).
  - **Ramified-level correction to the ticket's oracle plan**: SignatureX0DN(D,N)
    requires gcd(D,N)=1, so the "N=3" closed-form check applies only to D ∈ {10,26};
    for D ∈ {15,21} (3 | D ramified) the coprime check runs at N=2 instead, and the N=3
    corpora are validated by the per-record area assert + the ramified coarse row
    (diagnosed in t20-scripts/diagnose_D15_borel.m: at ramified 3 the finest congruence
    row is (1; 3,3,3,3)-shaped, matching ⟨KG, index-4 congruence H⟩).
  - **Spread (t20-scripts/battery_spread.m) all green**: D=15 deg-1: five level-1
    AL-tower signatures each found exactly once — X(15;1)=(1;3,3), X/w3=(0;2,2,6,6),
    X/w5=(1;3) (an else-branch case of the fixed formula), X/w15=(0;2⁴,3), X*=(0;2³,6);
    X₀(15;2)=(3;−) at N=2; ramified N=3 row ✓. D=21 deg-1 (rescued cache): X(21;1)=
    (1;2⁴), X(21)/w21=(0;2⁶), X₀(21;2)=(3;2⁴); N=3 runs (9 rows). D=26 deg-2:
    X(26;1)=(2;−), the two (1;2,2) single quotients, X(26)/w26=(0;2⁶) — the
    deg-1-blocked bottom COMPUTED AS A ROW through the (2⁵) bottom (no obstruction from
    above!), X*(26)=(0;2⁵), and X₀(26;3)=(5;−) at N=3.
  - All generated spread files copied to t20-artifacts/ (D15-N{1,2,3}, D21-N{1,2,3},
    D26-deg2-N{1,3}) — PROVISIONAL.
- 2026-07-22 (wave2-J-fable): **ν-schema decision (Q7.3, ⟐ flagged)**: KEEP the four
  fixed nu2/nu3/nu4/nu6 columns — the recommended option. The φ(n) ≤ 2 theorem makes
  them provably sufficient for every D in scope, and the code now ASSERTS it: EnhancedEllipticPoints
  requires every cone order in {2,3,4,6} and every point order lands there automatically
  (n | cone order). No schema migration; T04's canonical schema keeps the same four
  columns (no coordination needed beyond this note). Frontend (web_curve.py:657,
  main.py:601-604) unaffected.
- 2026-07-22 (wave2-J-fable): **cross-process determinism bonus check**: two independent
  T19-state processes produce byte-identical D=6 files outside generators/ram_data_elts
  (which churn: e.g. 381 masked-cell diffs at deg1-N4) — confirms the masked-comparison
  design AND T29 label determinism across processes.
- 2026-07-22 (orchestrator): **session stopped (credit limit) mid-close-out.** Work is
  substantial and preserved — branch `ticket/T20-elliptic-points` commits `6116aed`,
  `35e2988`, `e6ac659`, `78cfd8b`, plus WIP `8acb524` (D=6 identical-regeneration
  validation + t20-artifacts/ + t20-scripts/, committed by the orchestrator so nothing is
  lost). Per the Log above the substance is DONE: s3=e3 bug fixed and cross-checked
  (verify_s3.m), bottom-signature generalized (all cone orders in {2,3,4,6}, φ(n)≤2
  asserted), spread battery D=10/15/21/26 all green, D=6 regenerates byte-identically
  (masked), ν-schema decided (keep nu2/nu3/nu4/nu6). **Remaining to reach `review`:**
  (1) confirm `tests/run_quick.m` green on the final tree (a fresh agent should just run it);
  (2) add the D=10 genus/ν regression test if not already wired (check tests/);
  (3) write the one-paragraph closing summary + set status: review. A resuming agent can
  do this in minutes — do NOT redo the generation. Enumerate-H.m edit region: the
  RamificationData/EnhancedRamificationData/call-site area (verify no collision with the
  writer block if merging alongside T04). This BRANCH is what T21 (D=10/15 generation) and
  the T06 capstone build on. Flag for David: the s3=e3 fix in
  `SignatureX0DNmodAtkinLehnerElement` changes AL-quotient signatures — T25's verify was
  told this bug could only surface on generated AL-quotient rows; those rows now exist in
  t20-artifacts/, so a verify pass against them is a good post-merge check.
