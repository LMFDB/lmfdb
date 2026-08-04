# Draft answers to shimcurve_tickets/QUESTIONS.md

> **STATUS: work-in-progress draft (updated 2026-07-21).** Co-developed by Eran + Claude, grounded in the
> code. Not final and **not a substitute for `QUESTIONS.md`** (per BOARD, David answers there).
> All 15 questions have draft answers; **DECIDED (Eran)** = settled, **⟐** = open sub-decision.
> See the 'Open sub-decisions' section for the consolidated to-do list.

Prepared for Eran's review before anything is copied into the real `QUESTIONS.md` on
`roed-math/lmfdb@shimura_curves`. Everything below is grounded in the local code
(`~/Documents/GitHub/ShimCurve` and `lmfdb/lmfdb/shimura_curves/`); Q4/Q5/Q8 include
empirical Magma runs. **`DECIDED (Eran)`** marks calls Eran has already made in review;
**`⟐`** marks the sub-decisions still open (genuinely Eran's/David's call, not something the
code determines). All 15 questions have draft answers.

---

## Q1. Legacy label format `D.N-[m1,m2,…]`

**Answer:**

1. **Your reading is correct.** `D.N-[m1,…,mk]` = X₀(D;N) quotiented by the Atkin–Lehner
   subgroup ⟨w_{m1},…,w_{mk}⟩, the m being Hall divisors m ‖ DN. `[1]` = trivial quotient
   = X₀(D;N) itself; the full list of all Hall divisors = X\*. This is not just a hypothesis
   — it is exactly the convention fixed by `SignatureX0DNmodAtkinLehnerElement`
   (`X0DN_code.m:185`, and its docstring: *"the list of all non-trivial Hall divisors m ‖ DN
   so that w_m is in the subgroup W … The m=1 case is allowed, corresponding to the trivial
   quotient"*). For 26: Hall divisors {1,2,13,26}, so `26.1-[1,2,13,26]` = X\*(26;1),
   `26.1-[1,26]` = X₀(26;1)/⟨w₂₆⟩. **Nuance to record:** the prefix `26.1` is `D.N`
   (discriminant · Eichler level), *not* `discB.discO` or `order_label.deg_mu`.

2. **DECIDED (Eran): option (b) — generate level-1 enhanced rows for all discriminants we have
   models for.** These proper AL-quotient rows are produced by no code in either repo today
   (only the `[1]` coarse X₀(D;N) rows exist, from `tablesX0DN.m`). The level-1 enhanced curves
   X_H (H ≤ Aut_{±μ}(O) ⋉ (O/1)ˣ = H ≤ Aut_{±μ}(O)) *are* exactly the AL quotients, so this is
   the right target.
   **Scope this pulls in (grounded):** the models file covers **48 distinct discB from 6 to 462**
   (discO up to 462, including Eichler orders) — so this is far beyond the one working
   discriminant (D=6). It is the **T19 → T20 critical path**, and both currently fail: T19's
   general normalizer path fails its own `in O` assert even on D=6 (see Q8), and T20's
   elliptic-point counting hardcodes the (2,4,6) base (see Q7). It also needs T09 (Aut_{±μ}(O)
   for C4/C6/D4/D6) and T08's canonical μ on Eichler orders (Q3). At discO up to 462 the
   Voight/`FuchsianGroup(O)` route + disk cache (Q8.1) is the practical choice and compute time
   will matter. **Net:** the decision is sound but blocked until that chain lands — it is not a
   near-term upload. (These level-1 model rows carry N=1 but, per Q12.1, still range over **all
   admissible squarefree deg μ** for each order — the classical AL-quotient models are the deg μ=1
   members of that family, and any exotic polarizations of the same order get their own rows/labels.)

3. Confirmed: `26.1-[1]` → the row with `discB=26, discO=26·1=26, deg_mu=1, level=1,
   order_label="26", name="X(26;1)"` (`tablesX0DN.m:194,207-213`). The "1" in `26.1-[1]` is
   N, which here coincides with deg_mu=1.

**Note for T01:** no script generates the `D.N-[…]` strings and there is no old→new crosswalk
file anywhere — the join is something T01 has to build from scratch (the *reading* is fixed by
code; the *mapping* is not).

---

## Q2. `gerbiness`, `aut_gerbiness`, `Gerby_gen`

**Answer:** The crux (now resolved, see 1): **the name `gerbiness` is currently attached to
two different groups in the code**, and the LMFDB column should be neither of the two verbatim —
Eran's decision below fixes which group it is.

- In `enumerate-H.m` (`createRecord`, :246-248): `gerbiness = #KG_level` counts the reduced-mod-N
  **root-of-unity gerbe band** — the cyclic kernel `⟨ζ_{2n}⟩ ⊂ Oˣ` of
  `Aut_{±μ}(O)⋉Oˣ → N_{Bˣ}(O)/Qˣ` (`SemidirectToNormalizerKernel`, `elliptic-elements.m:128`,
  order 2/4/6). This is **generically ≥ 2** and has nothing to do with deg μ.
- In `enumerate-O.m:258-261` and `tablesX0DN.m:177-180`: `Gerby_gen` is hardcoded to the
  identity and the comment says gerbiness = 1 because `f: Aut_{±μ}(O) → N_{Bˣ}(O)/Qˣ` is
  injective — the ker(f) notion, which is what issue #6 is about.

1. **DECIDED (Eran): `gerbiness = |ker(f: Aut_{±μ}(O) → N_{Bˣ}(O)/Qˣ)|` — the size of the gerbe
   of the moduli stack (the Shimura curve).** This is the issue-#6 notion, trivial iff deg μ = 1.
   Rationale (Eran): the moduli problem's stack carries a gerbe of that size; the automorphisms
   that act trivially on the coarse moduli are exactly ker(f). (The generic ±1 that every abelian
   surface carries is *already absorbed* into the "±" of Aut_{±μ}(O), so it is not a residual
   gerbe — which is why deg μ = 1 gives gerbiness 1.)

   **⟐ Important downstream consequence for T07 (flag, not a blocker):** under this definition the
   **current `enumerate-H.m` computation is wrong** — `gerbiness := #KG_level` computes the
   *root-of-unity band* `⟨ζ_{2n}⟩` (generically 2/4/6), a **different group** from ker(f). T07
   must recompute the `gerbiness` column as `#ker(f)` directly (enumerate Aut_{±μ}(O), apply f,
   count the kernel) and generalize the `enumerate-O.m`/`tablesX0DN.m` hardcode (currently `1`,
   correct only for deg μ = 1) to the same `#ker(f)`. Note `#ker(f)` is also generally *smaller*
   than the current `aut_gerbiness` (= projection of KG onto the Aut factor), so it is a genuinely
   third quantity — neither existing column already holds it.

2. **`#KG_level` = the baseline automorphism band → rename `base_gerbiness` (DECIDED direction,
   Eran).** Precise relationship (from `elliptic-elements.m:128-152`): `KG` is built as `[<x,x⁻¹>]`
   over the **norm-1 roots of unity of O that represent automorphisms**, so `#KG_level` is the band
   `⟨ζ_{2n}⟩ ⊂ Oˣ` — the inner automorphisms by ±1 (and ±i, ±ω) — of order **2/4/6**, essentially a
   property of **O** (reduced mod N), *independent of deg μ*. This is **complementary** to
   `gerbiness = |ker(f)|` (the scalar-collapsing polarization automorphisms, a property of (O,μ)):
   `KG ∩ (Aut × {1})` is trivial, so the two count disjoint kinds of automorphism. Name it
   **`base_gerbiness`** — the always-present baseline that `gerbiness` refines. (⟐ alternatives if
   preferred: `unit_gerbiness`, `automorphism_band`.) Note a consistency point under Eran's Q2.1
   choice: because `base_gerbiness ≥ 2` always, it is *not* itself the moduli-stack gerbe (else deg
   μ=1 curves would be gerbey); it is the unit/torsion automorphism band of O, which the enhanced
   ±μ structure "absorbs." **`aut_gerbiness`** (= projection of KG onto the Aut factor) is a third,
   distinct quantity and must be **kept for the genus/Gauss–Bonnet normalization**
   (`enumerate-H.m:281`) — ⟐ optionally rename it too (e.g. `aut_band`) to avoid the "gerbiness"
   collision. None of the three is displayed on the website today, so all renames are free.

3. **`Gerby_gen`** = a generator of `ker(f)` (the automorphism mapping to a scalar in N/Qˣ),
   identity when deg μ = 1 — consistent with the decision. ⟐ Pin the coordinate convention:
   `AutmuO_generators` uses `Eltseq(B!·)` while the current placeholder uses `Eltseq(O!·)`; choose
   one (recommend matching `AutmuO_generators`).

4. **"gerbiness = 1 ⟺ deg μ = 1" is now an assertable theorem** on the `gerbiness = #ker(f)`
   column — a good sanity check to add. **Related bug to fix under T07/T09:** `aut_mu_O.m:66`
   asserts `f` is injective *unconditionally*, which is exactly wrong for deg μ > 1 (that
   assertion would fire on precisely the curves where gerbiness > 1). It must be dropped/relaxed
   for the deg μ > 1 rows to be generable at all.

   *One worth a 2-line check against LSSV §3.5 before T07 lands:* confirm ker(f) is precisely the
   subgroup of Aut_{±μ}(O) acting trivially on the moduli (the gerbe band) — i.e. that it injects
   into the generic object's automorphism group. Eran's reasoning (±1 absorbed into ±μ) says yes;
   a paper cross-check makes the assertion in (4) airtight.

---

## Q3. Canonicality / uniqueness of the polarized element μ

**Answer:**

1. **DECIDED (Eran): there ARE several in general — classified by Pollack conjugation.** The
   governing classification is **Rotger, *Quaternions, polarizations and class numbers*, Crelle
   561 (2003), 177–197** (arXiv:math/0211120):
   - **Def 2.3 (Pollack conjugation):** μ₁ ∼_p μ₂ over O iff **μ₁ = ᾱ μ₂ α** for a unit α ∈ Oˣ
     (note the *conjugate* ᾱ — a "twisted" conjugation, `μ ↦ ᾱμα`, not ordinary α⁻¹μα).
   - **Cor 3.7:** the first Chern class gives a bijection between the isomorphism classes of
     principal polarizations Π(A) and the Pollack classes
     `P(O) = {μ ∈ O : tr μ = 0, n(μ)·R_F = D_O}/∼_p`.
   - **Prop 4.1 / Thm 3.8 / Thm 7.1:** the count is via Eichler's theory of optimal embeddings —
     `#Pollack classes = |n(Oˣ)/N_{L/F}(Sˣ)|·e(S,O)/2`, and
     `π₀(A) = (1/2h⁺(F)) Σ_u Σ_{S∈S_u} 2^{e_S} h(S)` — a sum of **class numbers** h(S) of the
     quadratic orders S = R_F[μ] ↪ O. Over ℚ this is essentially Σ h(S), **routinely > 1**.

   So the label `discB.discO.deg_mu` **is insufficient**: `quaternion_orders_polarized` needs
   **one row per Pollack class**, disambiguated by a canonically-ordered class index appended to
   `mu_label` (e.g. `discB.discO.deg_mu.i`, or a Cremona-style letter). This is *distinct from* the
   code's `IsTwisting`/`polarization-twisting.m` (which concerns the automorphism group Aut_{±μ}(O)
   / the skew-commuting χ, **not** the enumeration of polarization classes) — so T08 must **add**
   Pollack-class enumeration; nothing in the repo does it today. (`polarization-twisting.m:213-214`'s
   worry about "many candidates for chi" is the *automorphism* multiplicity, a different thing.)
   **⟐ Cross-reference / cascade:** since the curve label is built on `mu_label`, adding a Pollack
   index there lengthens the *curve* label arity too — coordinate with Q11 (names), Q15/T29 (label
   determinism), and the frontend `LABEL_RE` (`main.py:58-61`), which will need the extra component.

2. **Canonical representative — recommended yes, keyed to the Pollack class.** For reproducible
   stored `mu`/`AutmuO_generators`, within each Pollack class store the lex-minimal short vector:
   enumerate the trace-zero lattice `O⁰` (already available as `basis_L`/`Q` via `ShimuraCurveLattice`,
   `polarization-twisting.m:25-41`), take vectors with `nrd = d·disc(O)`, and pick the minimum under
   a fixed ordering. The class index in the label (point 1) is then assigned by a canonical order on
   the classes themselves (e.g. by the invariants of S = ℤ[μ], then lex on the representative).

3. **Deterministic + complete algorithm — the short-vector route + Pollack quotient.** Replace
   `Embed`/`InternalConjugatingElement` with short-vector enumeration of `{μ ∈ O : μ²+d·disc(O)=0}`
   on `O⁰` (the abandoned block at `polarization-twisting.m:88-112`; the same technique already works
   for χ in `IsTwisting` :197-228), **then quotient by Pollack conjugation μ ↦ ᾱμα**. One routine
   thereby delivers all three needs at once: robustness (Q3.3), a canonical representative (Q3.2),
   *and* the complete multiset of classes (the multiple-rows requirement of point 1). Magma's
   optimal-embedding / `Eichler`-class machinery can cross-check the class count against Thm 7.1.

   *(Note re Q12.1: since the release ranges over all admissible squarefree deg μ AND now all
   Pollack classes per degree, the row count in `quaternion_orders_polarized` grows accordingly —
   T08's enumeration must be complete, not first-found.)*

---

## Q4. Why `assert #G/#G1plus eq 2` fails for D=6, N=5

**Answer:** **Solved, empirically (Magma V2.29-7, D=6, deg μ=1).** The expected index is **not 2
— it is φ(N)**, and it has nothing to do with square-classes of −1 or of the AL norms.

Measured `#G/#G1plus`:

| N | 3 | 5 | 7 | 11 | 13 | 25 | 35 | 49 |
|---|---|---|---|----|----|----|----|----|
| [G:G1plus] | 2 | 4 | 6 | 10 | 12 | 20 | 24 | 42 |
| φ(N)       | 2 | 4 | 6 | 10 | 12 | 20 | 24 | 42 |

and `G/G1plus ≅ (Z/N)ˣ` as an abelian group in every case (e.g. N=35 → invariants [2,12] =
(Z/35)ˣ). Order accounting for N=5: `#G = 1920 = 4·|GL₂(F₅)|`, `#G1plus = 480 = 4·|SL₂(F₅)|`.

**Mechanism.** `G ≅ Aut_{±μ}(O) ⋉ (O/N)ˣ`, and `G1plus ≅ Aut_{±μ}(O) ⋉ (O/N)¹` (reduced-norm-1
units). The quotient is the reduced-norm map `G ↠ (Z/N)ˣ` with kernel G1plus; the enhanced
lifts of the normalizer generators all have `(O/N)ˣ`-component of reduced norm ±1
(`NormalizerToAutmuO`, `elliptic-elements.m:176`), so they generate all of the SL₂-factor
`(O/N)¹` but never reach the norm direction beyond ±1. Hence `[G:G1plus] = φ(N)`.

1. So the index is **φ(N) = #(Z/N)ˣ**, not the norm-sign index 2. The "= 2" was only ever right
   because every tested N had φ(N) ≤ 2 (all shipped data is N ∈ {1,2,3,4,6}). **N=5 is simply the
   first N with φ(N) > 2** — the failure is arithmetic bookkeeping, not a real obstruction, and
   *not* because 5 ≡ 1 mod 4.

2. **No change to the "plus" subgroup is needed.** `G1plus = Aut ⋉ (O/N)¹` is already the correct
   norm-1 group for the Fuchsian/monodromy computation, and nothing downstream consumes the index
   (the Fuchsian index is computed independently, `enumerate-H.m:165-169`). The fix is a
   one-liner: replace `assert #G/#G1plus eq 2;` with `assert #G/#G1plus eq EulerPhi(N);` (or
   delete it) at `enumerate-H.m:45`, `:677`, and `genera.m:66`. **This unblocks N=5 (T10, T23)
   directly.** ⟐ One maintainer sign-off worth doing: confirm no other site silently assumes
   index 2 (I checked the three `assert` sites; only those three).

---

## Q5. Fine vs. coarse criterion

**Answer:**

1. **Correct criterion:** `is_coarse ⟺ (1,−1) ∈ H`, where `(1,−1)` is the enhanced element
   `⟨B!1, −O!1⟩` reduced into GL₄(Z/N). Concretely replace the hardcode
   (`enumerate-H.m:272`) with a membership test of `EnhancedElementInGL4modN(⟨1,−O!1⟩, N)` in H
   — this is exactly the `contains_negative_one` boolean the frontend already has
   (`main.py:294,605`). That resolves the `shimcurve_generate.py:19` TODO.

2. **Yes — every "gerbiest" H is automatically coarse.** `(1,−1)` is *always* in
   `SemidirectToNormalizerKernel` (it maps to `1·(−1)⁻¹ = −1 ≡ 1` in Bˣ/Qˣ — structural; the
   `#ker eq 1` branch even returns it explicitly, `elliptic-elements.m:142`), hence always in
   `KG`, and `EnumerateGerbiestSurjectiveH` only builds subgroups ⊇ KG (`enumerate-H.m:62`). So
   `is_coarse = true` is currently **correct for all shipped data** — the hardcode isn't yet a
   bug. **Fine curves ((1,−1) ∉ H) can only arise from non-gerbiest H**, which the main
   enumeration does not produce yet. (Ties directly into Q12 sub-question 2.)

3. **Fine-label format** is the modular-curves hyphenated form; the frontend regex
   (`main.py:59-61`) is
   `\d+\.\d+\.\d+\.\d+\.\d+-\d+\.\d+\.[a-z]+\.\d+\.\d+`, i.e. `{coarse}-{fine}`, and parsing
   branches on `"-" in label` (`main.py:627`). ⟐ You still owe the exact meaning of the fine
   suffix components when non-gerbiest enumeration is designed.

---

## Q6. `scalar_label` convention

**Answer:** `enumerate-H.m:380-387` sets `scalar_label = "{level}.{scalar_index}.1"` where
`scalar_index = [H : H ∩ G1]` = size of the image of H under reduced norm into (Z/N)ˣ. The
trailing `.1` is an admitted placeholder — the index alone does not pin down *which* subgroup of
(Z/N)ˣ the norm image is.

**Low-stakes finding:** `scalar_label` is **used by neither website** — it is commented out of
both the shimura and the modular-curves download column lists (`main.py:342`;
`modular_curves/main.py:457`) and has no live reader. So there is no reference implementation to
copy and changing it is risk-free.

**DECIDED (Eran): follow the modular-curve database convention.** T11 lifts modular curves'
`scalar_label` format verbatim rather than inventing a new one. Concrete implementation note: the
modular-curve `scalar_label` is produced in the RSZB/generation code (in lmfdb the column is
dormant — commented out of the download list and read nowhere), so T11 should pull the exact format
from the modular-curve *generation spec* and replicate it for the scalar image `nrd(H) ≤ (Z/N)ˣ`,
replacing the placeholder trailing `.1` at `enumerate-H.m:385`. Since nothing on the website
consumes `scalar_label` yet, this is low-risk and can ride along with T11 whenever convenient.

---

## Q7. Elliptic-point counting for general D

**Answer:**

1. **Signature of the bottom orbifold X(D;1)^{Aut_{±μ}(O)} — the fix is to stop hardcoding
   `[2,4,6]`.** `EnhancedEllipticPoints` (`genera.m:18`) assumes the base is the (2,4,6)-triangle
   quotient. The general fix: read the base orders off the actual elliptic generators of
   `N_{Bˣ}(O)⁺/Qˣ` (they come in the same order as σ), i.e. replace `bottom := [2,4,6]` with the
   list of their orders — **so Q7's input is exactly Q8's output; Q7 falls out once Q8 works.**
   Note (per Eran, see Q8): `FuchsianGroup(O)` gives only the O¹ base signature, *not* the
   normalizer/Aut quotient, so the enhanced bottom cannot be read straight off it. The two viable
   sources for the enhanced base orders: (a) the **normalizer elliptic generators produced by the
   fixed Q8 routine** (their orders in Bˣ/Qˣ), or (b) the **Ogg/algebraic** signatures
   `SignatureX0DNmodAtkinLehnerElement` (`X0DN_code.m:185`), already in the
   `[genus,[2,·],[3,·],[4,·],[6,·]]` shape.
   **DECIDED (Eran): validate against the formulas in the literature.** Conveniently the literature
   formula is already coded: `SignatureX0DNmodAtkinLehnerElement` implements **Ogg83** (CM orders of
   fixed points from Ogg83; genus via Riemann–Hurwitz / Ogg83 Eqn 3). So T20 should **triple-check**
   the enhanced base orders: (computed normalizer-generator orders) vs (Ogg83 via
   `SignatureX0DNmodAtkinLehnerElement`) vs (the classical Eichler elliptic-point formulas e₂/e₃ and
   Voight, *Quaternion Algebras*, Ch. 30 & 39). All three must agree — that agreement is the
   correctness certificate, and it doubles as the validation oracle for Q8(B)'s generators.

2. **Bottom is not always genus 0** for larger D (X(D;1) itself has positive genus for many D,
   and its Aut quotient can too). Good news: the genus pipeline (`EnhancedGenus`, Riemann–Hurwitz,
   and the `Area(O)` Gauss–Bonnet check) already tolerates positive-genus bases — **only the
   ν-bucketing hardcode does not.** Once `bottom` is generalized per (1), positive-genus bases need
   no further change.

3. **ν₅, ν₁₂, etc. cannot occur** — this is a theorem, and it means the schema is fine. Finite-
   order elements of N_{Bˣ}(O)⁺/Qˣ for a quaternion algebra over ℚ embed imaginary quadratic
   orders, forcing φ(n) ≤ 2, so n ∈ {2,3,4,6} only. The (ν₂,ν₃,ν₄,ν₆) columns are therefore
   **mathematically sufficient for every D in scope** (already the convention in
   `tablesX0DN.m:195-202`). ⟐ Only decision: keep the 4 fixed columns (recommended, simpler) vs
   move to a defensive (order,count)-pair list. No math reason to change; strictly scope-is-ℚ.

**Flag:** the existing deg μ=2, deg μ=6 D=6 tables were produced with the `[2,4,6]` hardcode; since
the enhanced bottom X(D;1)^{Aut_{±μ}(O)} depends on μ (while `NormalizerPlusGenerators(O)` does
not), their ν-columns should be re-checked once the base-order generalization lands.

---

## Q8. Generators of the positive-norm normalizer for general D

**Answer:** **The premise is out of date; T19 is "finish the in-progress branch," not "write."**

- The D∈{6,10,15} hardcode + `"oops, not written for this discriminant yet"` exists **only in git
  history** (commit `9651827`). Work on the general case lives on branch **`beyond_disc6`**
  (commits `db9298c "first steps to get normalizers and elliptic elements"`,
  `cbdbd7c "fixed issue with finding the elliptic elements"`, plus **uncommitted WIP** in Eran's
  working tree). It is the only branch with this; `quat_orders`/`refactor`/`roed:newmain`/both
  `main`s predate `normalizing_element_of_norm`. The working-tree `NormalizerPlusGenerators`
  (`elliptic-elements.m:109`) is already general: `require IsEichler(O)` then returns
  `[normalizing_element_of_norm(O,d) : d in HallDivisors(D*N) | d ne 1]`.
- **It is mid-debug and currently fails for D=6, d=2.** Eran's uncommitted changes: refactor the
  signature to `(O,d)`, perturb the ε-search by `D=&*ps` (the CRT modulus) instead of `d`, and — the
  key one — **add a genuine normalizer check** `assert &and[mu*b*mu^(-1) in O : b in basisO]`. That
  assert correctly fires because the construction is under-determined:
  - the scheme only keeps integrality equations whose entry denominator is exactly `Norm(mu)`
    (`nums := [Numerator(a) : a in Eltseq(A) | Denominator(a) eq Norm(mu)]`) — a
    necessary-but-not-sufficient proxy for "μ normalizes O"; and
  - **the p=2 branch is explicitly punted** (`if (d mod p eq 0) then continue; // think later how to
    handle p = 2`), and d=2 is exactly the D=6 failure. So the ±5-box CRT search returns a norm-2
    element that isn't a true w₂, and the new assert catches it. The assert is right; the search is
    incomplete.
- **Structural issue to flag:** the routine *conflates two jobs* — it filters `Trace²<4·Norm` to
  return only **elliptic** elements, but `G1plus` needs the **Atkin–Lehner generators** (involutions,
  generally not elliptic) while Q7 needs the **elliptic/torsion** elements. Different sets; bundling
  them in one Hall-divisor loop is part of the fragility.

1. **RECOMMENDED (B) — algebraic construction, decoupling the two jobs.** Correction (Eran):
   Magma's `FuchsianGroup(O)` handles only **O¹** (norm-1 units) — not Oˣ, not the normalizer — so
   it is not a drop-in (that's why `tablesX0DN.m` uses it only for the base signature and falls back
   to Ogg for AL quotients). Options were: (A) finish the current scheme search (enforce *all*
   integrality equations, handle p=2, dynamic ε-bound); (B) algebraic — AL involutions as generators
   of the two-sided ideals of norm m ‖ DM, elliptic/torsion elements from optimal embeddings of
   ℤ[ζₙ] (n∈{2,3,4,6}); (C) extend Fuchsian to the normalizer (most work).
   **Claude's recommendation: (B).** Reasons: (i) **completeness** — (A)'s fixed ε-box (`Bound:=5`)
   around CRT lifts has no guarantee the target element lies inside it, so it can *silently return
   false* for larger discriminants (scope goes to 462); even a fully-debugged (A) is a bounded
   heuristic, uncertifiable across 48 discriminants. (ii) **validation** — (B)'s output cross-checks
   against formulas already in the repo (`SignatureX0DNmodAtkinLehnerElement`, Ogg83) and the
   Eichler/Rotger class-number counts (Q3); (A) has no independent oracle. (iii) **less greenfield
   than it looks** — the elliptic/torsion half reuses `Embed`/`UnitGroup` (already used 12×/21× in
   the repo); the only new piece is AL involutions *as elements* (the repo has them only as
   *signatures* today), a standard two-sided-ideal construction (Voight, *Quaternion Algebras*,
   §28/§43) that also removes the AL-vs-elliptic conflation. **Honest caveat / hybrid:** (B) is more
   upfront code and the AL-element construction needs care on Eichler orders — if D=6/10/15 are
   needed immediately, patch (A) (p=2 + missing equations) to unblock small D now, but build (B) for
   the discO ≤ 1000 production run. ⟐ Final route is Eran's, but the release should rest on (B).

2. **Constraints the general code must preserve** (from `NormalizerToAutmuO` /
   `NormalizerPlusGeneratorsEnhanced`; Eran: "seem fine, revisit later"): each generator normalizes
   O; positive reduced norm; AL representatives have reduced norm exactly a Hall divisor m ‖ DN; the
   enhanced lift lands in the norm-±1 part of the `(O/N)ˣ`-component (this is what makes
   G1plus = Aut ⋉ (O/N)¹ — see Q4); and `kergen` (carrying `(1,−1)`) is appended so KG is generated
   correctly (see Q5).

---

## Q9. Obstructions / pointless / point-count semantics

**Answer:**

1. **Confirmed — conventions match modular curves exactly.** `obstructions` is `integer[]` of
   places, `0` = the real place ℝ, positive entries = primes p with X(ℚ_p)=∅; `has_obstruction`
   and `pointless` have identical semantics. The shimura display code
   (`web_curve.py:912-928`, `:367-371`) is a line-for-line copy of modular curves.

2. **Reality check first:** these columns are **all `\N` (NULL) in the current pipeline** —
   `has_obstruction`, `obstructions`, `pointless`, `num_known_degree1_points`,
   `num_known_degree1_noncm_points`, `cm_discriminants` are unset in both `enumerate-H.m`
   (:551,:568,:589-591,:595) and `tablesX0DN.m` (:181,:204-206,:216). The frontend can render them
   but has no data; the actual live branch is "Local obstructions … not known."
   **DECIDED (Eran): v1 first pass WITHOUT Jordan–Livné.** The building blocks exist
   (`RationalCMPointsX0DN`/`RationalCMQuotientsX0DN`, `OggCount…` in `X0DN_code.m`). v1 encodes:
   - **Shimura's D>1 theorem** → `pointless=true`, `0 ∈ obstructions` for every coarse X₀(D;N) and
     every X_H whose Aut-projection is trivial (the "covers X₀(D;N)" family — see (3));
   - the **AL-quotient exception** (X_H whose group contains Aut/AL elements of the right norm can
     acquire real points) handled case-by-case from `autmuO_norms` — do *not* blanket-mark these
     pointless;
   - **CM-point lower bounds** from `RationalCMPointsX0DN`/`RationalCMQuotientsX0DN` →
     `cm_discriminants`, `num_known_degree1_*`.
   Ogg/Jordan–Livné local criteria at p | D are **deferred past v1** (Eran).

3. **"X_H covers coarse X₀(D;N)" holds exactly when the Aut-projection of H is trivial** (positive
   norm), i.e. test the image of H under `Aut_{±μ}(O) → N_{Bˣ}(O)/Qˣ` — not
   "H ∩ ({1}⋉(O/N)ˣ) ≠ full". For the μ-level-1 coarse curves that map is injective
   (`tablesX0DN.m:177-180`), so the coarse rows always inherit "no real points."

---

## Q10. Sources for exact gonalities

**Answer:**

1. **DECIDED (Eran): import the Padurariu–Saia tables** (Eran confirms they can be used).
   `GonalityBoundListX0DN` (`X0DN_code.m:1230`) already sets *exact* `q_gonality`/`qbar_gonality`
   for coarse X₀(D;N) from published tables (Ogg83, GY17, Rotger02, and **PS24 = Padurariu–Saia**
   for bielliptic N>1), wired through `tablesX0DN.m:219-223`. The real gap is the **enhanced X_H
   curves**, which get only crude `[1, 2(g−1)]` bounds and `q_gonality = qbar_gonality = \N`
   (`enumerate-H.m:527-540,:598-601`); extending PS-style tables to general X_H is the T17 work.

2. **DECIDED (Eran): the ⌈(g+3)/2⌉ + parity improvements are wanted for v1.** ⌈(g+3)/2⌉ is the
   standard Brill–Noether ℚ̄-gonality upper bound for genus ≥ 2 (Poonen '07 App. A); the coarse code
   already uses `⌊(g+3)/2⌋` (`X0DN_code.m:1320`). Replace the enhanced curves' weak `2(g−1)` ℚ̄-upper
   bound with `⌊(g+3)/2⌋`, and apply the no-real-points even-parity rounding to the enhanced
   ℚ-gonality bounds too (already done for coarse at `X0DN_code.m:1384-1386`). Both are cheap+safe.

**Bug to flag (not in QUESTIONS but worth telling the authors):** `X0DN_code.m:1394` sets
`gon_Qbar := gon_Q_low` (looks like it should be `gon_Qbar_low`), with a related unused typo
`qon_Qbar_low` at `:1352` — may mis-set exact ℚ̄-gonality for coarse curves.

---

## Q11. Naming conventions for the `name` column

**Answer:** The grammar the frontend actually implements:

- **`X(D;1)`** — maximal order, level 1; **`X(D,N;1)`** — Eichler order of level N (comma form,
  always trailing `;1`). These are the *only* names any code produces (`tablesX0DN.m:194`).
- **`X^*(D;1)`, `X^*(D;N)`** (typed `X*(…)`, canonicalized by `canonicalize_name`,
  `web_curve.py:98`) — full Atkin–Lehner quotients; recognized by `parse_family`
  (`main.py:303-318`).
- `canonicalize_name` maps comma→semicolon and `X*`→`X^*`; the jump box additionally accepts
  fiber products of any of the above joined by `*`, resolved via the `factorization` column
  (`main.py:241-274`), not stored as a single `name`.
- Jump-box `NAME_RE = X\(\d+(;|,)\d+\)` (`main.py:62`) only matches the 2-integer forms —
  it does **not** match `X(D,N;1)` (trailing `;1`) or `X^*`, so those go through the DB-name
  lookup path, not the regex.

**DECIDED (Eran, baseline): `X_0(discB, discO; N)` for Eichler orders, recovering the usual
classical curve when N=1.** Eran is open to a revised scheme "we can vote on (including deg μ)."
Concrete gaps the code still exposes: **no script generates the `X^*(…)` names** (grep of the whole
ShimCurve repo finds no `X*`/`X^*` assignment), yet the frontend expects them — so the 391 stored
names are partly hand-curated/external, and a systematic generator needs the full grammar pinned
first. Concrete proposal for the vote is in the **appendix below**; three items need a vote.

---

## Q12. Scope decisions for the first public release

**Answer (DECIDED by Eran; grounded facts alongside):**

*Current computed coverage on disk (`data/genera-tables/`):* **D = 6 only**, deg μ ∈ {1, 2, 6},
N ∈ {1, 2, 3, 4, 6}. N=5 absent solely because of the Q4 assert (now understood — trivially
fixable). The enumerator is **structurally gerbiest-only** (`EnumerateGerbiestSurjectiveH`,
`enumerate-H.m:58`); no non-gerbiest enumerator exists.

1. **Target coverage — DECIDED: `discO ≤ 1000`, `N ≤ 6`, and all admissible squarefree `deg μ`.**
   Clarifications recorded from Eran: Eichler orders are **in**, entering via
   `discO = discB · levelO`; **N is the level of the congruence subgroup, not the order level**;
   and deg μ ranges over **all admissible squarefree degrees** — i.e. every squarefree d for which
   `HasPolarizedElementOfDegree(O, d)` returns an element (not restricted to d | N). (O, d) pairs
   with no polarized element simply get no row.
   - *Facts / consequences:* this is a large program. The 48 model discriminants (discB 6–462,
     Q1) all satisfy discO ≤ 1000, and many more orders with discO ≤ 1000 have no model yet. Every
     non-D=6 order is blocked on the T19→T20→T09→T08 chain (all currently non-working — see
     Q1.2, Q7, Q8). Since deg μ is unrestricted by N, each order O contributes a row-family for
     *every* admissible μ (as the current D=6 tables already do: deg μ ∈ {1,2,6} at every N) — so
     T08's robust, canonical, and *complete* `HasPolarizedElementOfDegree` (enumerate all classes,
     not just find one) is on the critical path, not just a hygiene fix.
2. **Non-gerbiest H — DECIDED: out of v1** (Eran: "v1 can live with only the gerbiest H, avoiding
   stacky issues"). This matches the capability limit — the enumerator cannot produce non-gerbiest
   H anyway (`enumerate-H.m:58`) — so all v1 curves are coarse and no fine curves appear (Q5).
3. **Table name — DECIDED: `gps_shimura`.** This is well-chosen: it exactly parallels the modular
   curves main table **`db.gps_gl2zhat`** (LMFDB `gps_` convention = a table keyed by subgroups of
   a group). No more-descriptive name is warranted; I'd keep `gps_shimura`. Renaming from
   `gps_shimura_test` touches ~25 references in `main.py`/`web_curve.py` (T27). Suggested parallel
   for the auxiliary tables, matching `modcurve_models/points/modelmaps/teximages/pictures`:
   keep `shimcurve_models` and add `shimcurve_points`, `shimcurve_modelmaps`, `shimcurve_teximages`,
   `shimcurve_pictures` as those land; `quaternion_orders`/`quaternion_orders_polarized` keep their
   names.
4. **Completeness claim — DEFERRED by Eran** ("have to see what we actually generate"). What is
   honestly claimable *today*: *"all gerbiest, surjective-reduced-norm enhanced level structures H
   for D=6, deg μ ∈ {1,2,6}, N ∈ {1,2,3,4,6}"* (add N=5 after the Q4 fix). Revisit once the
   discO ≤ 1000 / N ≤ 6 run completes; the honest statement will be bounded by whichever
   discriminants T19/T20 successfully process.

---

## Q13. Jacobian-column semantics + cmfdata provenance

**Answer:**

1. **Confirmed — semantics copy modular curves.** `rank` = analytic rank of Jac(X_H) =
   Σ (mult_i · analytic-rank-of-newform_i); `conductor` factored; `traces` = a_p list;
   `trace_hash` = LMFDB trace hash; `dims`/`mults`/`newforms` are parallel arrays sorted by CMF
   label; `is_simple` = one newform with multiplicity 1. Verified in `jacobian_decomp/`:
   conductor `= Factorization(∏ level(f_i)^(mult_i·dim_i))` (`newform_decomp.m:56-57`), rank
   `= Σ rank(f_i)·mult_i` where the CMF `rank` field is the Galois-orbit analytic rank (:55).

2. **cmfdata dump columns + trace depth.** `cmfdata.txt` is external, no dump script in the repo;
   format fixed (`helpers.m:65-75`): `label:level:cond:dim:rank:traces`, `traces` an eval-able Magma
   list, records kept with `level | levelbound` (default `D·N²`). T13 writes a dump from
   `db.mf_newforms` selecting **`label, level, conductor, dim, analytic_rank, traces`**. **AL-signs
   NOT needed**; the one non-obvious column is `rank = analytic_rank of the Galois orbit`.

   **Trace depth — the analysis Eran asked for.** How the matcher (`ShimuraNewformDecomposition`,
   `newform_decomp.m:59-118`) actually consumes traces: candidate set `Z = {level ≤ D·N², cond ≤ N,
   dim ≤ g}`; it builds `A = [[dim, a_{p₁}, a_{p₂}, …]]` over candidates, solves `A x = b` for the
   multiplicity vector against the quaternionic trace `b` (`HTraces`), and **grows the prime set until
   the solution is unique** (`Dimension(K)=0`). It accesses `r`traces[p]` **by prime value p**, so the
   stored list must have length ≥ the largest prime used; if it runs out it returns **rank code −3
   "cutoff reached"** (a detectable failure, not silent). So:
   - **Binding requirement:** stored traces length `T ≥ Sturm(L_max)`, where `L_max` = the max
     candidate level in scope and `Sturm(L) = ⌊(2/12)·[SL₂(ℤ):Γ₀(L)]⌋ = ⌊(1/6)·L·∏_{p|L}(1+1/p)⌋`
     (weight 2). Two distinct newforms of level ≤ L differ at some a_p with p ≤ Sturm(L), so up to
     Sturm(L_max) the candidate rows are linearly independent and the multiplicities are pinned down.
   - **Numbers for the scope** (with the M-aware bound from (3), `L_max = discO·N² ≤ 1000·36 = 36000`):
     `Sturm(36000) ≈ (1/6)·36000·2.4 ≈ 14400` → store **a_n up to n ≈ 14400** (≈ first 1700 primes).
     But that worst case is `discO=1000, N=6`; the vast majority (esp. N=1, `L_max = discO ≤ 1000`)
     need only `Sturm(≤1000) ≈ 300` (a_n to ~300). **Recommendation: tier the depth per newform** —
     store a_n up to `Sturm(ℓ·N_max²)` for a form of level ℓ (cheap for small ℓ), capped at
     Sturm(36000).
   - **Safety net:** exploit the existing `−3` return — T14 treats "cutoff reached" as *regenerate
     extended traces for that curve's candidates and retry*, so a too-short dump self-heals instead
     of producing wrong data. Concretely: dump the tiered depth above, and wire `−3 → extend+retry`.
   - **⟐ Caveat to verify:** LMFDB's default `mf_newforms.traces` column length may be shorter than
     14400 (I couldn't reach the devmirror to confirm); if so the dump must pull/compute **extended**
     a_p (e.g. via `mf_hecke_nf`) for the largest-level forms, not just read the default column.

3. **Jacquet–Langlands space — DECIDED (Eran): make it M-aware.** History (Eran): the original plan
   was maximal orders (disc D) + congruence level N, hoping to get Eichler-order-M curves as
   level-M *subgroups* — but that's inefficient, so the scope now **includes Eichler orders of level
   M directly** (disc `discO = D·M`; Q12.1). Therefore the JL space **must be M-aware**, and the
   current D,N-only code is wrong for the Eichler rows. Concretely T13 must change:
   `AmbientLevel := D*N` → **`discO*N` (= D·M·N)** (`newform_decomp.m:36`), and the candidate filter
   `level ≤ D*N²` → **`level ≤ discO*N²`** (`:66`, and `CMFLoad` `levelbound`, `helpers.m:68`). The
   **D-newness stays keyed to D** (`IsDNew(D,·)` — new at the ramified primes; forms may be old at
   p | M and p | N), which matches the classical JL statement that Jac(X₀^D(M)) ↔ the D-new subspace
   of level D·M. ⟐ Worth a cross-check that HTraces on the Eichler side already uses the level-M order
   (it takes `H` and `N`, so confirm the order passed in carries level M).

---

## Q15. Canonical ordering of subgroups H → the label tiebreaker

**Answer:**

`updateLabels` (`enumerate-H.m:288-319`) groups H by `PermutationCharacter(G, H)` — a genuine
Gassmann/permutation-equivalence invariant, so the **class letter is canonical**. The problem is
purely *within* a class: ties fall back to the order `Subgroups(G, KG)` happened to return, which
is Magma-implementation-defined ⇒ the trailing number (and, when two curves tie, effectively the
a/b assignment) is **non-deterministic**. The two tied D=6 curves are the w₆ curve
(`autmuO_norms` set {6}) and the w₃ curve (set {3}).

1. **DECIDED (Eran): tiebreaker = AL content, then a canonical generator.** Break ties within a
   Gassmann class by an intrinsic tuple: first the **Atkin–Lehner content of H** — the *set* of
   Hall divisors m with w_m ∈ H (the μ-independent shadow of `autmuO_norms`; {6} vs {3} cleanly
   separates the two D=6 curves and gives the "w₆ curve" a stable letter); then, if still tied, a
   canonical normal form of H (lex-min over the G-conjugacy class of sorted generator images, à la
   RSZB canonical generators). Store the result in a `tiebreaker` column, mirroring modular curves
   (RSZB label `level.index.genus.tiebreaker`).

2. **DECIDED (Eran): intrinsic ordering.** Invariant-based (AL content + canonical normal form),
   μ-independent, so it survives T08's change of μ representative — a fixed-μ+fixed-algorithm scheme
   would re-break the moment T08 changes μ. (T29 must supply a *complete* invariant to sort on so
   ties are always resolved; if the AL content + generator normal form ever still ties, that's a
   bug to surface, not silently order by Magma.)

3. **DECIDED (Eran): relabel the whole table.** "Still in alpha and we expected labels to change."
   So on the next reload the entire `gps_shimura` table is relabeled under the new canonical order;
   no attempt to pin the old `gps_shimura_test` labels (which aren't reproducible anyway). Any
   `update_from_file` staged by label must wait until this lands (per BOARD's PROVISIONAL rule).
   T29 step 4 can still measure how many rows move, for the record.

---

## Q14. Area normalization discrepancy

**Answer:**

`Area(O)` (`enumerate-O.m:34`) returns `φ(D)·ψ(M)/12` with `M = discO/D`; for the D=6 maximal
order this is `2/12 = 1/6`, which is what `quaternion-orders.txt` stores. The `1/3` in
`quaternion-orders.m` is a **stale artifact** of the old formula `EulerPhi(D)/6` (also missing the
Eichler `ψ(M)` factor) — that file predates the `/12` normalization and should be regenerated (or
its orphaned, undeclared area columns removed). So the factor-of-2 is not a live disagreement about
math; it's one current file and one stale file.

**Which normalization is correct for the LMFDB column:** `φ(D)ψ(M)/12`. This equals
`covol/(4π) = −χ_orb/2`, and it is exactly the value the genus identity consumes:
`genus = 1 + aut_gerbiness·index·Area(O)/#Aut − ½Σ ν_e(1−1/e)` (`enumerate-H.m:280-283`;
frontend `web_curve.py:659-683`). The full hyperbolic area/(2π) would instead be `φψ/6`. So do
**not** switch to `φψ/6` without also inserting a compensating ÷2 in both genus formulas.

**⟐ DECISION — column name.** Calling it `area` is genuinely misleading: the stored value is
neither hyperbolic-area/(2π) (`φψ/6`) nor the orbifold Euler characteristic (`−φψ/6`); it's
`covol/(4π) = −χ/2`. Your choice:
- keep storing `φψ/12` but **rename** the column to reflect `covol/(4π)` (or store `−χ/2` and call
  it `chi`); or
- store the more standard `φψ/6` and adjust both genus formulas.
I'd keep the value (`φψ/12`, no formula churn) and just rename for honesty.

**Two secondary bugs to fix under T06:** (i) regenerate/repair `quaternion-orders.m` so it agrees
with `quaternion-orders.txt` and carries the `ψ(M)` factor + declared headers; (ii) the frontend
`show_genus` drops the `aut_gerbiness` factor that the Magma Gauss–Bonnet check includes, so the
displayed genus decomposition is only correct when `aut_gerbiness = 1` — restore the factor.

---

## Cross-cutting flags worth surfacing to David

- **Immediate unblock:** the Q4 assert fix (`eq 2` → `eq EulerPhi(N)`) directly unblocks N=5 →
  T10 and T23, and is a one-liner in three places.
- **`gerbiness` = |ker(f)| (DECIDED, Q2)** — the moduli-stack gerbe, trivial iff deg μ = 1. T07
  must **recompute** the column: `enumerate-H.m` currently stores the wrong group (`#KG_level`,
  the root-of-unity band), and the `enumerate-O.m`/`tablesX0DN.m` hardcode `1` only holds for
  deg μ = 1. Keep `aut_gerbiness` for the genus formula (maybe rename). Drop the unconditional
  injectivity assert at `aut_mu_O.m:66` — it fires on exactly the deg μ > 1 rows we now need.
- **T19 is "fix," not "write":** the general normalizer path already exists but fails its own
  normalizer assert on D=6 (`elliptic-elements.m:97`) — shipped data used the old hardcoded
  generators (Q8). Claude recommends rebuilding it algebraically (option B) for the release.
- **Polarizations are NOT unique per degree (Q3, Rotger/Pollack conjugation)** — the label
  `discB.discO.deg_mu` needs a class-index suffix and `quaternion_orders_polarized` needs multiple
  rows per (order, degree); the added label component cascades into the curve label + `LABEL_RE`.
  T08 must enumerate Pollack classes *completely*, which nothing does today.
- **Jacobian decomposition is wrong for Eichler rows until the JL space is made M-aware (Q13)** —
  the code uses D,N only; with Eichler orders in scope (Q12.1) T13 must switch to D·M·N (D-newness
  still keyed to D). Ships incorrect `rank`/`conductor`/`newforms` for every M>1 row otherwise.
- **All obstruction/CM/point-count and enhanced-curve exact-gonality columns are NULL today**
  (Q9/Q10) — the frontend can display them but no data is generated.
- **`quaternion-orders.m` disagrees with `quaternion-orders.txt` on `area` by a factor of 2**
  (Q14, stale file); and the frontend genus display drops the `aut_gerbiness` factor present in
  the Magma Gauss–Bonnet check — both to fix under T06.
- **Minor code bug (Q10):** `X0DN_code.m:1394` `gon_Qbar := gon_Q_low` looks wrong.

---

## Open sub-decisions still needing Eran/David (the remaining ⟐)

Everything else is DECIDED. These are the sub-choices left:

- **Q8 (biggest):** pick the normalizer-generator route — Claude recommends **(B) algebraic**; final
  call depends on how close the `beyond_disc6` scheme (option A) is.
- **Q11:** the three name-grammar votes — second slot (level M vs discO), partial-AL notation
  (TeX quotient vs bracket), deg μ in names (principal-only vs decorated). See appendix.
- **Q14:** the `area` column name — keep value `φψ/12`, rename to `covol_over_4pi` / store `−χ/2` as
  `chi` (Claude's lean: keep value, rename).
- **Q2 (minor):** `Gerby_gen` coordinate convention (`Eltseq(B!·)` vs `Eltseq(O!·)`); whether to
  rename `aut_gerbiness`/`base_gerbiness`; the 2-line LSSV §3.5 check that ker(f) is the gerbe band.
- **Q3 (minor):** the exact canonical-μ ordering within a Pollack class; the label-cascade
  coordination (Q11/Q15/`LABEL_RE`).
- **Q7 (minor):** which signature source is authoritative (fixed normalizer generators vs Ogg
  `SignatureX0DNmodAtkinLehnerElement`) — they must agree; validation against the literature is
  already decided.
- **Q13 (minor):** the trace-depth tiering specifics; plus two things to verify on the devmirror —
  that `HTraces` is handed the level-M order, and whether the default `mf_newforms.traces` is long
  enough (else pull extended a_p).

---

## Appendix — concrete naming-scheme proposal for Q11 (to vote on)

A curve is determined by **(D, M, N, deg μ, H)**: `D` = discB (algebra discriminant),
`M = discO/D` = Eichler level (M=1 ⟺ maximal order), `N` = congruence level, `deg μ` = polarization
degree, `H ≤ Aut_{±μ}(O) ⋉ (O/N)ˣ`. As in modular curves, **only recognizable H get a `name`;
everything else is label-only (`name = NULL`)**.

### Level/order slots
Write the order data before the semicolon and the congruence level after:
**`X_∗(D, M; N)`**, with `X_∗(D, M; 1)` collapsing to the classical Shimura curve `X_∗(D, M)`, and
`M=1` giving `X_∗(D; N)` / `X_∗(D)`. This matches the current code output `X(D,M;1)` and
Eran's baseline. `canonicalize_name` (`web_curve.py:98`) already maps comma→semicolon and
`X*`→`X^*`, so store with `;` and let comma be an accepted input alias.

> **VOTE 1 — second slot.** (a) Eichler **level M** — recovers classical `X_0(D, M)`, matches
> existing code, my recommendation; vs (b) **discO = D·M** (Eran's literal wording) — fully explicit
> but maximal order reads `X_0(D, D)` rather than `X_0(D)`. Pick one; the grammar is identical
> otherwise.

### Family prefix (shape of H's congruence part at N)
Mirror modular curves; the Eichler level M already contributes Borel-at-M structure from the order:
- `X(D, M; N)` — full/complete level-N (the X(N)-analogue);
- `X_0(D, M; N)` — Borel-type at N;
- `X_1(D, M; N)` — Γ₁-type at N;
- `X_sp(D,M;N)`, `X_ns(D,M;N)`, `X_sp+`, `X_ns+` — split/nonsplit Cartan and AL-extensions,
  *only if/when* such H are enumerated (out of v1 scope, but reserve the notation).
- At N=1 all collapse to the base curve `X(D, M)`.

### Atkin–Lehner quotients (level-1, H ⊆ Aut_{±μ}(O)) — the Q1 model curves
- `X^*(D, M)` — full AL quotient (the `X*` the frontend already expects).
- Partial AL quotients:
  > **VOTE 2 — partial-AL notation.** (a) explicit TeX quotient `X_0(D,M)/\langle w_{m_1},…\rangle`
  > (readable, standard); vs (b) compact bracket `X_0(D,M)-[m_1,…]` echoing the legacy `D.N-[…]`
  > label (round-trips to the models file, uglier). I lean (a) for the display `name`, keeping the
  > bracket only in the legacy crosswalk.

### Polarization degree deg μ
> **VOTE 3 — deg μ in names.** (a) **Only deg μ = 1 (principal) curves get a classical name**;
> deg μ > 1 curves are label-only — simplest, and the exotic polarizations are exactly the
> non-classical curves (my recommendation); vs (b) name them too with a decoration, e.g. a
> superscript `X_0^{(d)}(D,M;N)` or a trailing `; μ=d`. If (b), the decoration must be chosen so
> `canonicalize_name` and `NAME_RE` can parse it.

### Frontend consequences (either way)
`NAME_RE` (`main.py:62`, currently `X\(\d+(;|,)\d+\)`) must be widened to accept the `;N`
congruence slot, the `X_0`/`X_1`/`X^*` prefixes, and (if VOTE 3b) the deg-μ decoration; `parse_family`
(`main.py:303`) and `canonicalize_name` extended to match. Fiber products via `*` stay jump-box-only
(resolved through the `factorization` column), unchanged.

**Recommended default (my vote):** VOTE 1(a) level M · VOTE 2(a) TeX quotient · VOTE 3(a)
principal-only names — i.e. `X_0(D, M; N)`, `X^*(D, M)`, `X_0(D,M)/⟨w_m⟩`, names only for deg μ=1.
