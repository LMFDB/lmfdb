---
id: T19
title: Generalize NormalizerPlusGenerators beyond D ∈ {6, 10, 15}
status: review
owner: wave1-C-fable
priority: P1
tier: 3
repos: [ShimCurve]
depends_on: []
questions: [Q8]
---

## Context

`NormalizerPlusGenerators(O)` (`code/level-structure/elliptic-elements.m:2-55`) returns **hardcoded** generator lists of N_{Bˣ}(O)⁺/ℚˣ for the maximal orders of D = 6, 10, 15, and the string `"oops, not written for this discriminant yet"` otherwise. Everything scales through it: `NormalizerPlusGeneratorsEnhanced` (`polarization-twisting.m:157`), `GetG1plus` (`enumerate-H.m:40`), `EnhancedEllipticElements` (`elliptic-elements.m:199`), hence the entire enhanced enumeration. This is blocker #1 for any discriminant beyond {6,10,15} (blocker #2 is T20).

Q8 decides the method. The natural general route: Magma's `FuchsianGroup(O)` computes a fundamental domain and generators of the unit group Γ⁰(O) (norm-1); AL/normalizer representatives for each m ∥ D·M come from elements of norm m in O normalizing O. Expensive but cacheable.

## Steps

1. Read Q8. Implement `NormalizerPlusGenerators(O)` generally:
   - norm-1 part: `FuchsianGroup(QuaternionAlgebra(O))` / `Group(...)` side-generators (check Magma docs `FuchsianGroup`, `Generators`), pulled back to O-elements;
   - AL part: for each m ∥ disc(O)·level, find x ∈ O with nrd(x) = m and x·O·x⁻¹ = O (short-vector search on the norm form, reusing T08's enumeration machinery; positivity of norm automatic since B is indefinite and nrd(x)=m>0).
   - Constraints from Q8.2 (whatever the enhanced wrapper needs — inspect how the current hardcoded lists are consumed by `NormalizerPlusGeneratorsEnhanced` before choosing output normalization).
2. **Regression gate**: for D = 6, 10, 15 the new code must generate the **same subgroup** of Bˣ/ℚˣ as the hardcoded lists (not necessarily the same generators): verify by comparing the generated enhanced images G1plus in GL₄(ℤ/N) for N = 3, 4 — identical groups. Keep the hardcoded lists as a test oracle, not as the code path.
3. Cache: persist computed generators per order label under `data/normalizer-gens/` (Magma-readable), keyed by order label, with a loader that recomputes on miss. FuchsianGroup at D ~ 1000 may take minutes — record timings for D ∈ {6,10,15,21,22,26,33,…,~200} in the Log.
4. Smoke the downstream: run `GenerateDataForGerbiestSurjectiveH` for D=10, deg 1, N=3 end-to-end (it will hit T20's elliptic-point limitation — for this ticket, stub the ν-columns as NULL if T20 isn't done; genus via Riemann–Hurwitz still works since `EnhancedGenus(sigma)` is general).
5. Tests: add D=10 generator-subgroup regression to `tests/`.

## Acceptance criteria

- D ∈ {6,10,15}: generated == hardcoded (as subgroups), asserted in tests.
- D = 21 (next discriminant, not hardcoded): generators produced, `EnhancedImageGL4`/`GetG1plus` run, index-2 (or per-T10 corrected) relation holds at N=3.
- Timing table in the Log; cache round-trips.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave1-C-fable): **Route (B) implemented** on `ticket/T19-normalizer-gens`
  (worktree, based on T29), commit `897d143`. Studied `upstream/beyond_disc6` (fetched;
  commits db9298c, cbdbd7c): Eran's scheme search (`normalizing_element_of_norm`) +
  `find_q`/`eichler_order` helpers; confirmed Q8's diagnosis (denominator-filtered
  integrality equations, p=2 punt, elliptic/AL conflation, fixed ±5 box). **Not reused as a
  code path** (route (A) = stopgap only per Q8); reused its ideas: the general
  Hall-divisor architecture, the normalizer assert (now on every generator), and
  `require IsEichler`.
- 2026-07-22: design facts discovered en route (all empirically verified):
  - The old hardcoded D=10/15 lists **no longer coerce into `MaximalOrder(QuaternionAlgebra(D))`**
    in Magma V2.29 (`O!map(a)` illegal coercion at old elliptic-elements.m:31) — the current
    tree could not even run D=10 hardcoded. Oracle comparisons now happen inside
    `MaximalOrder` of the defining algebras (-2,5), (-3,5), where the lists do live.
  - `NormalizerToAutmuO` can only lift generators whose AL class lies in
    **W_mu := image(Aut_{±mu}(O) → (Z/2)^r)** (≤ 4 classes, since Aut is dihedral/cyclic on
    ≤ 2 generators). For D=21, deg-1 mu: W_mu = {1, 21} ⊊ (Z/2)^2 — a full-X* generator
    list *cannot* work there; ditto every Eichler order with ω(discO) ≥ 3 (T22!). Hence the
    **mu-aware** `NormalizerPlusGenerators(O, mu)` building the spherical system for
    X(D;M)/W_mu; `NormalizerPlusGeneratorsEnhanced`/`EnhancedEllipticElements` now route
    through it. This is the "enhanced bottom depends on mu" flag of Q7 made precise.
  - The monodromy/genus pipeline (enumerate-H.m:822 `assert &*(sigma) eq Id`) requires the
    generator list to be a **spherical system** (product scalar, one generator per cone of
    the bottom orbifold) — AL representatives alone are *not* enough; this is the deep
    reason the two jobs were conflated in the hardcode. Construction: pick pool elements
    for all cones but one, complete the last as `Conjugate(partial product)` (product
    scalar by construction), accept iff the completion has the expected order+class;
    certify by Gauss–Bonnet equality + Ogg cone data + spanning of W + (in tests) G1plus
    index = phi(N). Sorted ascending by order via product-preserving Hurwitz moves
    (T20 reads the bottom orders off this list).
- 2026-07-22: **regression gate green** (tests/regression_normalizer_gens.m, wired into
  run_quick): G1plus(hardcoded oracle) == G1plus(general) in GL4(Z/N) for N ∈ {3,4} at
  D=6 (deg mu ∈ {1,2,6} — the shipped degrees), D=10, D=15; D=21 produced + index
  [G:G1plus] = phi(N) at N ∈ {3,4}; cache determinism; constructed orders == Ogg cone
  data. Full tests/run_quick.m green (incl. the pre-existing D=6 GenerateData + label
  determinism suites).
- 2026-07-22: **D=10 downstream smoke** (deg 1, N=3): `GenerateDataForGerbiestSurjectiveH`
  runs the whole enumeration (93 gerbiest surjective H) and **crashes exactly at the T20
  hardcode**: `EnhancedEllipticPoints` (genera.m:18, `bottom := [2,4,6]`) called from
  enumerate-H.m:294 → "Sequence index 4 should be in the range 1 to 3" (D=10's system has
  4 elliptic generators, orders (2,2,2,3)). **Intel for T20**: replace `bottom` by the
  orders of `EnhancedEllipticElements(O,mu)` (ascending, matching my sort); note the
  Gauss–Bonnet per-record assert (enumerate-H.m:302) sits right after and will then pass.
  ν-columns cannot be stubbed from my side without editing agent A's enumerate-H.m, so the
  smoke ends there by design. Pre-ν pipeline verified by hand for **all 93 subgroups**:
  sigma product-identity failures 0/93, genera {0^36, 1^28, 2^22, 3^5, 5^2}.
- 2026-07-22 (later): **hardening round** (commit `74ea791`) after the first D-spread run:
  - The Eran-style normalizer assert **caught a real bug in my own first version** at D=77:
    an element of J_m with norm m·k² (k>1) need not generate J_m and hence need not
    normalize O — the index argument requires nrd = ±m exactly. Fixed: search both signs,
    repair a norm-(−m) generator by a norm-(−1) unit (nrd(O×) = {±1}), and *filter* the
    class-m last resort by the normalizer property.
  - Search bounds must scale with disc(O), not with the class m (an embedded √(−m) for
    small m in a large-discriminant order is tall).
  - Deterministic hybrid tuple enumeration (lex odometer + fixed-seed LCG sampling):
    each finds spherical systems the other misses (D=57/65 lex-only, D=35 sampling-only).
    Per-pass budget capped (MaxTuples 40000, two escalation rungs) so hard cases fall
    back in ~1 min instead of grinding; prefix-product caching + an ellipticity
    trace-precheck reject almost every tuple in O(1).
  - Fallback lists now append **norm-one unit generators from Magma's FuchsianGroup**:
    strong approximation then gives the full Aut ⋉ (O/N)¹ mod every N, so GetG1plus
    remains correct even where no spherical system exists (positive-genus bottoms, e.g.
    W_mu-quotients at D=57/82 deg-1, full X* at D=91 (g*=1), D=123 (g*=1)). The
    sigma/EnhancedRamificationData pipeline still requires the spherical property — T20.
  - `Order(x::AlgQuatProjElt)` (enhanced-constructors.m:262) returns the *string*
    "infinity" — anyone comparing it to `Infinity()` or using it as a range bound gets a
    runtime error; NormalizerToAutmuO now guards on the type.
- 2026-07-22 (closing, wave1-C-fable): **DONE — status: review.** Branch
  `ticket/T19-normalizer-gens` (worktree `/Users/roed/claude/shim-wt/T19`, based on T29);
  commits `897d143` (core), `74ea791` (hardening), `76a45a9` (WIP snapshot after a session
  kill), `ccbf5fd` (mod-N generation validation), `a8c1166` (final caches).
  **tests/run_quick.m: 64 PASS, 0 FAIL** (includes the new tests/regression_normalizer_gens.m
  plus the pre-existing D=6 GenerateData, label-determinism and roundtrip suites).
  - **Route (B) CONFIRMED-as-built** (⟐ for Eran per Q8.1): algebraic construction — AL
    representatives as short vectors of the two-sided ideals J_m = (m·O^♯) ∩ O (with a
    norm-(−m)·norm-(−1)-unit sign repair when the +m generator is tall), elliptic elements
    from short-vector searches in J_m, spherical systems assembled by conjugate-completion.
    Eran's scheme search (`beyond_disc6`) was studied but not used as a code path; his
    normalizer assert is now on every returned generator (and caught a real bug in MY first
    fallback — class-m elements of norm m·k² need not generate J_m, hence need not
    normalize).
  - **Regression gate (acceptance)**: G1plus(hardcoded oracle) == G1plus(general) in
    GL₄(Z/N), N ∈ {3,4}, for D=6 at deg μ ∈ {1,2,6} (the shipped degrees), D=10, D=15 —
    all PASS. Oracle lists live in tests/regression_normalizer_gens.m (the old code path is
    deleted; note the old D=10/15 lists no longer coerce into
    MaximalOrder(QuaternionAlgebra(D)) in Magma V2.29, so the oracle runs in their own
    algebras (−2,5), (−3,5)).
  - **D=21 acceptance**: generators produced; EnhancedImageGL4/GetG1plus run;
    [G:G1plus] = φ(N) at N = 3 AND 4 (8.4s cold). Deep intel: for W_μ = {1,21} every
    small-height certified (0;2⁶) spherical system is *degenerate* (conjugate-paired; mod-4
    enhanced index 8 ≠ 2, invisible mod 3) — the **spherical certificates (product, orders,
    Ogg cones, class spanning, Gauss–Bonnet) are necessary but NOT sufficient for
    generation**. The μ-aware path now validates every candidate by the enhanced
    [G:G1plus] = φ(N) check at N ∈ {3,4}, retries the deterministic search (Skip), and
    falls back to the validated AL+torsion+FuchsianGroup-unit list. Cache records the
    validation status; μ-aware callers re-validate unvalidated entries on load.
  - **Triple-check (Q7 DECIDED)**: three-way genus agreement — my Gauss–Bonnet signature
    derivation (from OggCountFixedPoints cone data) vs `SignatureX0DNmodAtkinLehnerElement`
    (Ogg83 Eqn 3) vs the Eichler e₂/e₃ mass-formula inputs — for EVERY single-AL quotient
    X(D;M)/w_m over the spread: **105 comparisons OK, 0 mismatches, 0 errors** (genus up to
    4; s4/s6 counts also equal). Eichler orders: discO = 6.30, 6.42, 10.30, 22.66 (r=3) and
    6.210 (r=4, level 35): all spherical in ≤ 0.23s with all 7–15 per-order genus values
    matching Ogg (genus up to 5).
  - **Spread table** (full-W X* per maximal order; timings on the shared 16-core box;
    "spherical [orders]" = certified system, FALLBACK = validated generating set):
    D=6 (2,4,6) 0.07s; 10 (2,2,2,3) 0.17s; 14 (2,2,2,4) 0.07s; 15 (2,2,2,6) 0.03s;
    21 (2⁵) 0.34s; 22 (2,2,3,4) 0.32s; 26 (2⁵) 0.14s; 33 (2⁴,6) 0.38s; 34 (2⁴,3) 0.43s;
    35 (2⁶) 0.03s; 38 (2⁴,4) 0.12s; 39 (2⁶) 0.01s; 46 (2³,3,4) 0.68s; 55 (2⁶,3) 9.5s;
    57 (2⁷) 10.7s; 58 (2⁵,3) 14.5s; 62 (2⁵,4) 0.22s; 65 (2⁸) 1.4s; 69 (2⁶,6) 0.84s;
    74 (2⁷) 0.41s; 94 (2⁵,3,4) 1.6s — spherical; FALLBACK (g*=0, no system within budget;
    17–200s incl. Fuchsian units): 51, 77, 82, 85, 86, 87, 93, 95, 106, 111, 115, 118,
    119, 122; FALLBACK (g* > 0, correctly no system): 91, 123. Cache round-trip verified
    (second call identical, < 0.01s).
  - **D=10 downstream smoke** (deg 1, N=3): full enumeration (93 gerbiest surjective H),
    sigma product-identity 0/93 failures, genera {0³⁶,1²⁸,2²²,3⁵,5²}; the writer crashes
    exactly at T20's hardcode (`EnhancedEllipticPoints`, genera.m:18 `bottom := [2,4,6]`,
    called from enumerate-H.m:294 — "Sequence index 4 should be in the range 1 to 3").
  - **Follow-ups (explicitly not done)**: (i) spread D ∈ {129,…,194} unswept (Magma's
    FuchsianGroup hangs at Area(O) ≥ 7, now gated by MaxFuchsianArea — those orders get
    AL+torsion lists and the downstream φ(N) assert as guard); (ii) the degenerate-tuple
    phenomenon means T21's production run should either raise MaxTuples/MaxPool per order
    or accept validated fallbacks where the spherical search fails — and positive-genus
    bottoms (first at deg-1 W_μ-quotients of D=57/82, full-X* at D=91/123) need T20's
    hyperbolic-generator/genus-aware EnhancedGenus work regardless; (iii) the μ-free
    `NormalizerPlusGenerators(O)` cannot self-validate (no μ) — its spherical output
    carries the certificates only; (iv) non-squarefree Eichler levels untested (theory
    handled: J_m via m·O^♯ is valuation-general).
  - **Flags for David/Eran sign-off**: (a) route (B) as built, per above (⟐ Q8.1);
    (b) the μ-aware W_μ architecture (Aut_{±μ}(O) covers ≤ 4 AL classes, so the enhanced
    bottom is X(D;M)/W_μ, μ-dependent — this contradicts the μ-free
    NormalizerPlusGenerators(O) signature the old code implied and is forced for every
    Eichler order with ω(discO) ≥ 3, T22); (c) AL representatives are exact-norm-m when a
    short generator exists, else norm m·k² (matching the shipped hardcode practice, vs the
    letter of Q8.2); (d) the s3 = e3 (should be e3/2) suspect bug in
    SignatureX0DNmodAtkinLehnerElement's else-branch (X0DN_code.m:185, m ≡ 1,2 mod 4,
    m ∉ {2}) — genus output unaffected, ν₃ counts wrong for those quotients.
- 2026-07-22: **suspected upstream bug found** (not my file, not fixed):
  `SignatureX0DNmodAtkinLehnerElement` (code/X0DN/X0DN_code.m:185 and the unattached copy
  in code/tables/signatures_single_AL_element_X0DN.m), `else` branch (m ≡ 1,2 mod 4,
  m ∉ {2}): sets `s3 := e3` where it should be `e3/2` (w_m pairs up the order-3 points;
  no -3-CM point is w_m-fixed when 3 ∤ m). Check: D=10, m=5: e3(X(10)) = 4, code returns
  s3 = 4, but genus 0 + area 1/3 forces s3 = 2. The genus it returns is unaffected (Ogg
  Eqn 3 uses only the fixed-point count). My triple-check therefore compares **genus**
  values (mine via Gauss–Bonnet vs Ogg Eqn 3) and the s4/s6 counts, not their s2/s3.
