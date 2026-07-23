---
id: T30
title: Fix the indefinite trace formula + GL4→GL2 bridge (unblocks enhanced-curve Jacobians)
status: review
owner: wave2-H-fable
priority: P1
tier: 2
repos: [ShimCurve]
depends_on: [T13]
questions: [Q13]
---

## Context

T13 (2026-07-22, branch `ticket/T13-jacobian-decomp` @ df63e42) productionized `code/jacobian_decomp/` and validated the **coarse arm**: `JLDecomposition` agrees exactly with 32/32 devmirror ground-truth rows (discB 6–403, Eichler + maximal, genus 0–31). But it found the **enhanced arm** (trace-matching for general X_H) broken and never previously exercised:

- **Finding A:** `IndefiniteTrace` is a *maximal-order* trace formula — its `O := MaximalOrder(B)` is vestigial (computed, never reused) and there is no input path for an Eichler order of level M coprime to N. T13's candidate-side M-fixes (`levelbound = discO·N²`) are necessary but not sufficient for Eichler rows.
- **Finding B:** the enhanced enumeration produces `H ⊆ GL(4, Z/N)`, but `IndefiniteTrace`/`HTraces` require `H ⊆ GL(2, Z/N)`. The GL4→GL2 bridge does not exist anywhere in the repo.
- **Finding C (blocker):** `HTraces`/`ShimuraNewformDecomposition` are called nowhere in the repo (never validated). Bypassing B with a hand-built GL2 Borel, **HTraces fails known answers**: X₀⁶(5) gives `[2,6,8,12,…]` where newform 30.2.a.a demands `[-4,0,2,6,…]`, and genus-0 X₀⁶(1) yields nonzero traces where a trivial Jacobian forces 0. The Eichler–Selberg implementation is buggy/unfinished.

B+C together block T14's enhanced-curve decompositions (the coarse `JLDecomposition` arm is trustworthy and ready for T14 now). Full forensics in T13's Log.

## Task

Make `HTraces` produce provably correct Frobenius traces of X_H (maximal orders first, then Eichler level M), so `ShimuraNewformDecomposition`'s trace-matching works; build the GL4→GL2 bridge (or reformulate the trace formula to consume the GL4 subgroup directly).

## Steps

1. **Ground truth first** — assemble a test battery with known answers before touching the formula: X₀⁶(1) and X₀¹⁰(1) (genus 0 ⇒ all traces 0); X₀⁶(5) vs 30.2.a.a (the D-new space at level 30); ≥1 genus>0 coarse case where the answer is forced by the **validated** `JLDecomposition` — on coarse curves the two arms must agree: `ShimuraNewformDecomposition(Borel-type H)` == `JLDecomposition(D, N)`.
2. **Debug `IndefiniteTrace` against the literature** (Voight, *Quaternion Algebras*, Ch. 30 trace formula + Ch. 39; Eichler–Selberg for quaternionic Shimura curves). Localize the bug: class-number weights, elliptic-term embedding numbers, the H-conjugacy counting, or the q-expansion bookkeeping. The corrected formula, with citation, becomes the intrinsic's docstring.
3. **The bridge (Finding B):** decide (a) GL4→GL2 projection — for N coprime to D, O/N ≅ M₂(Z/N) and the enhanced rep is Aut ⋉ (O/N)ˣ, so the congruence part of H has a well-defined GL2 image via the splitting already used by the enumeration — vs (b) reformulating the trace formula to take the GL4 subgroup directly. Pick whichever is mathematically cleaner against LSSV §3.5, implement it, and log the rationale (flag for Eran if genuinely uncertain).
4. **Eichler-M support (Finding A):** thread the actual order O (with its level) through `IndefiniteTrace`; validate against `JLDecomposition` on Eichler coarse rows (devmirror has many).
5. Wire the fixed path into `ShimuraNewformDecomposition`; extend `tests/regression_jacobian_decomp.m` with the step-1 battery (keep < 2 min: small N only).
6. Do **not** mass-populate columns (that's T14). End state: validated pipeline + a T14 handoff note in the Log saying exactly what is now trustworthy for enhanced rows.

## Acceptance criteria

- Battery passes: genus-0 zero-traces; X₀⁶(5) matches 30.2.a.a; coarse-curve arm-agreement on ≥5 rows including ≥1 Eichler order.
- `tests/run_quick.m` green; docstrings state the corrected formula + bridge convention with citations.
- T14 handoff note in the Log.

## Log

- 2026-07-22: ticket created from T13's findings A/B/C (agent wave1-D-opus); see T13's Log for the full forensic detail. Coarse arm explicitly NOT blocked — T14 may run coarse rows on T13 alone.

- 2026-07-22 (wave2-H-fable): claimed; worktree `/Users/roed/claude/shim-wt/T13`, branch
  `ticket/T30-trace-formula` off T13's df63e42. Baseline reproduced T13's exact failing
  vectors before any edit (X⁶(1) full-H mod 5: `[4,6,6,9,9,12,15,16]`; X₀⁶(5) Borel:
  `[2,6,8,12,6,12,12,20]` at p=7..31).

  ### THE BUG (Finding C localized) — commit 3947168
  **`IndefiniteTrace` summed the elliptic term only over `t in [-Floor(2*sqrt(n))..0]`** —
  i.e. it dropped every t>0 conjugacy class, half the class-number-weighted embedding mass.
  Smoking gun: the third (local-model) branch HAS the compensating `t ne 0 select 2*(...)`
  doubling; the two split branches don't — the author knew the sum is over all t²<4n and
  forgot it in two of three branches. Hand-check X⁶(1), p=7: t≤0 elliptic sum = 4, code
  returned σ₁(7)−4 = 4 (matches T13's first value); full ±t sum = 8 = p+1 ⇒ trace 0 as
  genus 0 forces. This also explains T13's "suspicious positivity ≈ (p+1)/2": the returned
  values were σ₁(p) minus roughly half of p+1.
  **Fix**: loop over all t with t²<4n, evaluating the permutation character at β_t per
  sign (NOT a blanket ×2 — β_t and β_{−t} are different elements of GL2(Z/N), so this
  stays correct when −1 ∉ H and automatically projectivizes: X_H = X_{±H}).
  **Formula as now implemented+documented** (header of `indefinite.m`, with the Lefschetz
  derivation): for gcd(n, D·M·N)=1, n non-square,
  `tr T_n|S_2(X_H) = σ₁(n) − Σ_{t²<4n} Σ_{Z[α_t]⊆S⊆O_K} m(S)·f(β_{t,S})·h(S)/|S^×|`,
  m(S) = ∏ local optimal-embedding numbers (p|D: 0 if p|cond(S), else 1−(disc K/p);
  p|M: Hijikata; p|N: absorbed into f), f = perm character of GL2(Z/N) on GL2/H,
  β_{t,S} = a + b·companion(ω_S) mod N (b = cond of Z[α_t] in S) — the reduction of ANY
  S-optimal embedding is GL2(Z/N)-conjugate to it (local quadratic orders are Gorenstein ⇒
  proper local ideals principal ⇒ (Z/N)² is S⊗Z/N-free of rank 1). No hyperbolic/parabolic
  terms (division algebra). Square n = m²: diagonal excision `σ₁ − 1 + g − Σ'` where Σ'
  omits the classes γ = m·ζ, ζ ∈ S^× of order >2 (u=1, b²=n, D0∈{−3,−4}) — those generate
  the ideal m·O, i.e. lie on the excised diagonal component; this branch was already right.
  ### Second bug: Hecke vs Frobenius at square q — same commit
  The formula computes the HECKE trace tr T_q. For prime q that equals tr Frob_q
  (Eichler–Shimura), but at q=p² they differ: tr Frob_{p²} = tr T_{p²} − p·g (per form
  a_p²−2p vs Hecke a_{p²}=a_p²−p). Diagnosed numerically: X₀⁶(5) at q=49 gave 9 =
  a₇²−7 (Hecke) where Frobenius = 2 = a₇²−14. `HTraces` (docstring promises Frobenius)
  now converts at square q and REQUIRES each q prime or prime-square (higher powers need
  the whole Hecke tower — refused, not silently wrong).
  ### Also in the commit (unvalidated-yet parts flagged as such)
  - Eichler level M threading (`M:=1` optional): multiplies Hijikata local counts at p|M
    into the embedding numbers. Justified cases only: e=1 (m = 1+{S/p}, Eichler symbol,
    = 2 split / 0 inert / 1 ramified / 2 if p|cond(S)); e≥2 with p∤cond(S) (tree fixed-locus:
    split 2 / inert 0 / ramified 0); e≥2 with p|cond(S) = the general Hijikata case,
    **deliberately errors** rather than ship a mistranscription ⇒ use squarefree M.
    Validation against JLDecomposition pending (next step).
  - Local-model branch (p0 | gcd(D,N)): removed the ×2, and refined the inert case
    (m_{p0}=2): the two local embedding classes are swapped by the uniformizer, which is
    NOT inner in (O/p0^e)^× — contribution is f(β)+f(t−β), not 2·f(β). (Untested — no
    ground truth exercised yet; N=p^e single ramified prime enforced, as BuildG assumes.)
  - Removed vestigial `O := MaximalOrder(B)` (T13 Finding A).
  ### Battery (all pass, post-fix)
  | target | result |
  |---|---|
  | X⁶(1) N=1, p=5..31 | all 0 ✓ (genus 0) |
  | X⁶(1) via full H mod 5 and mod 7 | all 0 ✓ (exercises β branches, f≡1) |
  | X¹⁰(1) N=1 | all 0 ✓ |
  | X₀⁶(5) Borel mod 5 (upper AND lower) | `[-4,0,2,6,-4,0,-6,8]` = 30.2.a.a exactly ✓ |
  | X₀⁶(5) q=49 (g:=1) | 2 = a₇²−2·7 ✓ |
  | X⁶(1) q=49, q=25 | 0 ✓ |

  ### Stage 2: arm agreement + two MORE latent bugs (commit 34a800d-ish, see git log)
  Threaded M into ShimuraNewformDecomposition→HTraces (M := discO div discB; prime filter
  now gcd(N·discO)). Running the arm battery flushed out two latent bugs in the
  never-before-executed SUCCESS path of ShimuraNewformDecomposition:
  1. `Sort(forms, CMFLabelCompare)` passes a bare Intrinsic — Magma runtime error
     ("Bad argument types ... Intrinsic"). JLDecomposition wraps in func<>; this didn't.
  2. **forms/mult misalignment**: forms label-sorted, mult left in candidate order —
     scrambled pairing whenever the winning candidates weren't already sorted. Diagnosed
     via X₀⁶(35): trace arm printed mult [2,1,1,2,1,1,1] vs JL [2,2,1,1,1,1,1], but the
     JL-implied trace vector equals the HTraces vector at every checked prime — the
     "impossible" disagreement of a unique linear solve ⇒ output-array misalignment.
     Fixed with the same perm-to-both pattern JLDecomposition uses.
  **Arm-agreement battery (trace arm vs devmirror-validated JL arm) — all EXACT:**
  | curve | g | routes | result |
  |---|---|---|---|
  | X₀⁶(5) | 1 | Borel m5 | AGREE (30.2.a.a) |
  | X₀⁶(7) | 1 | Borel m7 | AGREE (42.2.a.a) |
  | X₀⁶(11) | 3 | Borel m11 | AGREE (66.2.a.a/b/c) |
  | X₀⁶(13) | 1 | Borel m13 | AGREE (78.2.a.a) |
  | X₀¹⁰(3) | 1 | Borel m3 | AGREE (30.2.a.a, cross-D) |
  | X₀⁶(35) | 9 | M=7+Borel m5; M=35+N=1; Borel m35 | all three routes give IDENTICAL
    trace vectors [-12,14,2,-12,-8,-2] (p=11..29) and AGREE with JL: mult [2,2,1,1,1,1,1],
    rank 1 — validates the Hijikata e=1 factors against the pure-congruence formula |
  Square-q, genus 3: X₀⁶(11) at q=25 → −10 = Σ(a₅²−10) ✓.
  Note: Borel-m35 with the D·N²=7350 corpus returns −3 (cutoff): the candidate set
  (all forms of level | 7350, level ≤ 2000) is too large for the 1000-coefficient trace
  depth even at 168 primes (twist-congruent pairs differing only at {2,3,5,7}); with the
  divisor-210 corpus it resolves and agrees. −3 is the designed self-heal signal — for
  T14's enhanced scope (N ≤ 6) this explosion cannot occur.

  ### Stage 3: literature extraction — Voight GTM 288 (quat-book.pdf v1.0.x, fetched), Ch. 30
  Facts extracted (book pp. 538–549), recorded here so no re-read is needed on crash:
  - **Prop 30.5.3(a)**: m(S, M₂(R); GL₂(R)) = 1 for EVERY local quadratic order S at a
    split place, realized by the regular representation γ ↦ [[0,−n_γ],[1,t_γ]] (rational
    canonical form, eq. 30.5.4; proof: R² is an invertible ⇒ principal S-module). This is
    the exact citation for our β_{t,S} companion-form representative being THE
    GL₂(Z/N)-class of every S-optimal embedding (the u-loop/b-conductor bookkeeping).
  - **Prop 30.5.3(b)**: p ramified in B, O the valuation ring: Emb(S,O) = ∅ unless K is a
    field and S = R_K integrally closed (⇒ our p|cond(S) ⇒ 0, i.e. gcd(u,p) zeroing);
    then m(S,O;O^×) = 1 − (K/p) (2 inert / 1 ramified / 0 split), while
    m(S,O;N_{B^×}(O)) = 1: **the two inert classes are swapped by conjugation by j
    (normalizes, doesn't centralize)** — the uniformizer-swap justification for the
    local-model branch refinement f(β)+f(t−β) (classes not conjugate under O^× alone).
  - **§30.6 (Eichler, residually split; follows Hijikata [Hij74, Thm 2.3])**: ϖ = [[0,1],[π^e,0]],
    N_{B^×}(O)/F^×O^× = ⟨ϖ⟩ ≅ Z/2 for e ≥ 1 (30.6.2). **Prop 30.6.12 (general, incl.
    p=2)**: for e ≥ 1, with M(s) := #{x ∈ R/p^s : f_γ(x) ≡ 0 mod p^s} (γ a generator of S,
    d_γ = disc S): m(S,O;O^×) = #M(e) if d_γ ∈ R^×, else #M(e) + #img(M(e+1) → R/p^e).
  - **Lemma 30.6.16** (e=1, S maximal, any p): m = 1 + (K/p).
  - **Lemma 30.6.17** (q = #k odd, e ≥ 1, f := ord_p(d_γ)): (a) f=0: m = 1+(K/p);
    (b) e<f: m = 2q^{(e−1)/2} (e odd), q^{e/2−1}(q+1) (e even); (c) e=f: m = q^{(f−1)/2}
    (f odd), q^{f/2} + q^{f/2−1}(1+(K/p)) (f even); (d) e>f>0: m = 0 (f odd),
    q^{f/2−1}(q+1)(1+(K/p)) (f even). [Only for q odd; Example 30.6.14: Z₂[i] into level-2^e:
    m = 1 (e≤1), 0 (e≥2) — shows the odd-q closed form fails at p=2, use 30.6.12 there.]
  - **Cross-check of what stage 1 shipped**: rho=0 split any e → (a) m=2 ✓; rho=0 inert → 0 ✓;
    rho=0 ramified e=1 → (c) f=1 odd: q⁰=1 ✓, e≥2 → (d) f=1 odd: 0 ✓ (and verified directly
    at p=2 via the M(2)=∅ maximality argument of 30.6.16's proof); rho≥1 e=1 → (b) e=1<f:
    2q⁰=2 ✓ (verified at p=2 by direct 30.6.12 root count: #M(1)=1, f(x₀)≡0 mod 4 ⇒ +1).
    So every case implemented in stage 1 is literature-confirmed; the e≥2, p|cond error
    stub can now be REPLACED by the general Prop 30.6.12 root count (valid all p).
  - **Thm 30.7.3 / Example 30.7.4, eq. (30.7.6)**: for B indefinite (#Cls O = 1 by strong
    approximation 28.2.11), O Eichler of squarefree level M: m(S,O;O^×) =
    h(S)·∏_{p|D}(1−(K/p))·∏_{p|M}(1+(K/p)) — the global product structure of our formula
    (level-N refinement replaces the p|N factor 30.5.3(a)=1 by the fixed-coset count f(β)).
  Plan from here: replace the HijikataLocalCount e≥2/p|cond error stub with Prop 30.6.12
  (odd p via 30.6.17 closed form, p=2 and all general cases via direct root count);
  validate on X₀⁶(25) (M=5², exercises (a) with e=2 and f≥2 cases via 5|cond terms)
  against JLDecomposition; then bridge, then tests.

  **Stage 3 DONE (commit 3c10a38):** grid check 0/2240 mismatches (closed forms vs
  independent Prop 30.6.12 root count over dK ∈ 10 fundamental discs, cond ∈ 14 values,
  p ∈ {2,3,5,7}, e ∈ 1..4); X₀⁶(25) AGREES with JL via both the M=25,N=1 route and the
  Borel-mod-25 route (raw traces identical: [-4,4,2,6,-12] at p=7..19; decomp
  30.2.a.a×2 + 150.2.a.{a,b,c}, g=5); X₀⁶(49) (M=7²) AGREES (42.2.a.a×2 + seven
  294-forms, g=9, rank 1). Non-squarefree Eichler M now fully supported — no error stub.

  ### Stage 4 (next): GL4→GL2 bridge
  Design decided (rationale logged for Eran): the repo NEVER splits O/N ≅ M₂(Z/N) — the
  enumeration lives entirely in GL4 via the RIGHT-regular representation of (O/N)^× on
  O/N ≅ (Z/N)⁴ (UnitGroupToGL4; embed-in-GL4.m), with the Aut_{±μ}-part acting by
  conjugation (NormalizingElementToGL4). So there is no existing isomorphism to reuse;
  the bridge constructs one, and by Skolem–Noether over Z/N (Pic(Z/N)=0 ⇒ every
  Z/N-algebra automorphism of M₂(Z/N) is inner) the GL2-image of H is well defined up to
  conjugacy — labels/H-conjugacy and permutation characters are splitting-independent.
  Plan: idempotent-splitting per p^e || N (Hensel-lifted eigen-idempotent ε, right ideal
  ε·(O/p^e) free rank 2, right-mult action = the M₂ image), CRT across p; H-detection via
  GL4ToUnitGroup/inONx (congruence part = regular rep); **H with nontrivial Aut_{±μ}-image
  is REFUSED with a precise error**: X_H then covers a further AL-type quotient and its
  trace formula needs the w-twisted Eichler terms tr(T_n ∘ w_m) (norm n·nrd(w) classes) —
  not implemented; needs either that formula or newform AL-eigenvalue data (dropped from
  cmfdata per Q13.2). ⟐ FLAG for Eran: a large slice of the 2198 enhanced rows has
  Aut-part; decide twisted-trace formula (Eichler/Ogg-style) vs re-adding AL signs to
  cmfdata + eigen-space selection for the product-type H = W ⋉ H_cong cases.

  **Stage 4 DONE (commit 1bad62b):** new `code/jacobian_decomp/bridge.m` —
  `SplittingModN` (algebra iso O/N ≅ M₂(Z/N), asserted unital-hom on the basis, inverse
  included), `EnhancedCongruenceToGL2` (adjoins −1, refuses Aut-part and det-nonsurjective
  H), `EnhancedCongruenceToLocalModel` (GL4 → BuildG local model at N = p^e, p | discB);
  `JacobianData` dispatches on Degree(H) — GL4 input accepted directly. Also fixed:
  **BuildG crash** (level_dividing_D.m: `Findc` returns GF(p) coords, `c[2]*I` type error —
  the local model had NEVER run; lift through Z), and JacobianData's `mu` type
  (HasPolarizedElementOfDegree returns a B-element, upstream is inconsistent). Battery:
  splitting round trip; GL4-Borel(80) → GL2 → exact 30.2.a.a traces; JacobianData(GL4) =
  [30.2.a.a] code 0; refusals fire (genuine norm-6 AL element μ; det-proper subgroup);
  local model N=2,3,4 full-(O/N)^× (orders 12/72/192) → all-zero traces (X⁶(1)).

  ### Stage 5: local-model validation on devmirror rows (nontrivial H)
  Devmirror recon: the 1,711 "newforms non-NULL" enhanced rows all store **`{}`** — no
  enhanced decomposition has ever been shipped; T14 starts from zero. But `generators`
  (format: 8 ints per generator = w-part 4 coords ∥ x-part 4 coords w.r.t.
  Basis(MaximalOrder(QuaternionAlgebra(6))); congruence-only rows have w = (1,0,0,0),
  identifiable by `1 = ALL("autmuO_norms")`) lets one rebuild H exactly. Four rows
  reconstructed and run through JacobianData (g from the row's genus column):
  | row | N | g | result |
  |---|---|---|---|
  | 6.1.2.16.1.a.1 | 2 | 1 | [24.2.a.a]×1, code 0 |
  | 6.1.2.24.1.b.1 | 2 | 1 | [24.2.a.a]×1, code 0 |
  | 6.1.2.48.3.a.1 | 2 | 3 | [24.2.a.a]×3, code 0; **independent check: trace vector
    exactly 3·a_p(24.2.a.a) at p=5..23** — the strongest possible ramified-branch test |
  | 6.1.3.36.2.a.1 | 3 | 2 | [54.2.a.a, 54.2.a.b], code 0 |
  All genus asserts (Σ dims·mults = g) passed — joint validation of the local-model
  trace branch and the shipped genus column. (EnhancedGenus itself crashes upstream:
  `EnhancedRamificationData` "Bad argument types" — genera.m/T09/T19 territory, flagged;
  JacobianData takes g as input so T30/T14 are unaffected.)

  ### Stage 6: regression + close-out (commit 9df143b)
  `tests/regression_jacobian_decomp.m` extended with the full T30 battery (cmfdata-guarded);
  `tests/run_quick.m`: **0 failures, 0 skips, ~5 s**. Acceptance criteria all met:
  genus-0 zero traces ✓; X₀⁶(5) = 30.2.a.a ✓; arm agreement on 8 curves incl. 6 Eichler
  configurations ✓; docstrings carry the corrected formula + Voight/Hijikata/Eichler
  citations (indefinite.m header, HTraces, bridge.m, ShimuraNewformDecomposition) ✓.

  ### Where the bugs were (summary, term by term)
  1. `IndefiniteTrace` elliptic sum: **t-loop only over t ≤ 0** — half the elliptic mass
     missing in both split branches (the local-model branch had the ×2). [3947168]
  2. `HTraces` at square q: formula computes **Hecke** tr T_q; Frobenius = Hecke only at
     prime q; at q = p², Frob = T_{p²} − p·g. Now converted; Q restricted to primes and
     prime squares. [3947168]
  3. `ShimuraNewformDecomposition` success path (never executed pre-T30): `Sort` handed a
     bare Intrinsic (crash), and **forms sorted while mults stayed in candidate order**
     (scrambled pairing). [8772b82]
  4. No M-threading into HTraces (T13 Finding A last mile) + prime filter missing M.
     [8772b82] Hijikata local counts for p | M: all cases, literature-verified. [3c10a38]
  5. Finding B: no GL4→GL2 bridge existed; built + wired + refusals. [1bad62b]
  6. `BuildG` type crash (local model never ran). [1bad62b]
  7. Local-model inert two-class refinement: f(β) + f(t−β) instead of 2·f(β) (uniformizer
     swap is not inner; Voight 30.5.3(b)/30.6.2). [3947168; exercised via stage 5 rows]

  ### T14 HANDOFF — what is now trustworthy
  Branch `ticket/T30-trace-formula` (worktree /Users/roed/claude/shim-wt/T13), commits
  3947168, 8772b82, 3c10a38, 1bad62b, 9df143b on top of T13's df63e42.
  - **Trustworthy now**: (a) coarse arm (`JLDecomposition`) unchanged from T13 (32/32);
    (b) enhanced **congruence-only** H (trivial Aut_{±μ}-image, det-surjective) via
    `JacobianData(H_GL4, G, O, mu, N : g:=genus)` — GL4 input bridged automatically —
    for gcd(N, discB) = 1 (split) AND N = p^e at a single ramified prime (local model);
    (c) Eichler orders of ANY level M (gcd(M, D·N) = 1) threaded through discO.
  - **Refused / not yet supported** (structured errors, never wrong numbers):
    (i) H with Aut_{±μ}-part — most of the 2,198 enhanced rows; needs the AL-twisted
    trace formula or AL-eigenvalue data (⟐ Eran decision above);
    (ii) det-nonsurjective H (geometrically disconnected X_H);
    (iii) **mixed N with a ramified prime**: N = 6 = 2·3 for D = 6 — BuildG models a
    single p^e only, so D=6 N=6 congruence rows need a two-prime local model (CRT of
    BuildG blocks + a split factor; straightforward extension, not done here) — T14
    should partition its run accordingly;
    (iv) square-q Frobenius needs g supplied; higher prime powers q = p^r (r ≥ 3) are
    rejected (need the Hecke tower).
  - **Practical**: supply `g` from the enumeration/DB genus column (EnhancedGenus is
    broken upstream, see stage 5); `generators`-column reconstruction convention above;
    `-3` = deepen-traces-and-retry (only an issue when discO·N² is large with the full
    corpus; enhanced scope N ≤ 6 is safe); CMFLoad's divisibility prefilter is what keeps
    candidate sets small — pass discO.
  - **Flags for David/Eran**: the Aut-part decision (above); upstream
    EnhancedGenus/EnhancedRamificationData type bug; upstream `mu` type inconsistency
    (AlgQuatElt vs AlgQuatOrdElt across intrinsics — worked around in my files).

  **Status → review.** All acceptance criteria met; nothing pushed; no DB writes.
