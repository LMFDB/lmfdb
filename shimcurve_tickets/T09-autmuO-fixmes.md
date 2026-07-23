---
id: T09
title: Fix Aut_{±μ}(O) construction for C4/C6/D4/D6 (aut_mu_O.m FIXMEs)
status: review
owner: wave1-A-fable
priority: P0
tier: 1
repos: [ShimCurve]
depends_on: []
questions: []
---

## Context

`code/level-structure/aut_mu_O.m` builds Aut_{±μ}(O) as a map from an abstract group (C_n or D_n) into Bˣ/Qˣ. Two FIXMEs mark broken cases:

- `:45` — `Dn<w_chi,w_mu>:=DihedralGroup(GrpPC, cyc_order); // FIXME: there will be another generator for D4 and D6 since magma uses prime relative orders`. For cyc_order ∈ {4,6}, Magma's pc-presentation of D_n has 3 generators with prime relative orders, so `Dn.2` does **not** have order cyc_order; the adjacent `assert Order(Dn.2) eq #Dn/2` and the element-list construction `[ <Dn.1^k*Dn.2^l, ...> ]` enumerate the wrong elements.
- `:57` — `Cn<w_mu>:=CyclicGroup(GrpPC, cyc_order); // FIXME: this will be a problem for C4 and C6` — same issue for the cyclic case (`Cn.1` has prime order in the pc-presentation for composite n).

These cases arise exactly when μ generates a cyclotomic quadratic order (the code detects sqeta = −1 → order 4, sqeta = −3 → order 6 just above, `:20-40`), so any (O, μ) whose automorphism group is C4/C6/D4/D6 currently gets a wrong `Aut` map — poisoning `AutmuO_size`, `AutmuO_label`, `AutmuO_generators`, `AutmuO_is_cyclic` in `quaternion_orders_polarized` and everything downstream in the enhanced enumeration for those μ.

The final `assert MapIsHomomorphism(grp_map : injective:=true)` (`:65`) may or may not catch the breakage (it checks the constructed element list, which could be silently wrong-but-consistent) — determine which.

## Steps

1. Build failing examples: search `quaternion_orders_polarized` (devmirror) for rows with `AutmuO_label` in ('C4','C6','D4','D6') to find concrete (O, μ); if none exist (possible — the bug may have prevented generation), construct one directly: need μ with μ²= −disc·d and a twisting pair giving the cyclotomic case; D=10 or D=15 with small degrees are natural hunting grounds; also grep `data/quaternion-orders/*polarized*` for those labels.
2. Reproduce the failure (or demonstrate silent wrongness) in a Magma session; record it in the Log.
3. Fix: use `GrpPC` presentations correctly (address elements via `Dn ! [exponent vector]` or construct via `PolycyclicGroup< a,b | a^2, b^n, b^a = b^-1 >`), or switch to `GrpPerm`/`GrpFP` (`DihedralGroup(GrpPerm, n)` has 2 generators with the expected orders — check what downstream code needs; `Domain(AutmuO)` is used for `GroupName`, `IsCyclic`, generator indexing `.1`/`.2` in `enumerate-O.m:270-273`, and as the domain of `Ahom` in `embed-in-GL4.m:373`).
4. Make the element-list construction independent of generator conventions: build `elts` by iterating over the group's elements with a well-defined decomposition rather than exponent pairs `(k,l)`.
5. Strengthen the homomorphism test to also assert `#image eq #Domain` and that orders match (`Order(g) eq Order(image under map)` for generators).
6. Add a regression test to `tests/` exercising one C4-or-C6 and one D4-or-D6 example end-to-end (`Aut` + `EnhancedImageGL4` at small N).
7. If any shipped `quaternion_orders_polarized` rows carried wrong Aut data, list the affected labels in the Log and stage corrected rows (coordinate with T06/T08 regeneration — if those run after this fix, no separate staging needed).

## Acceptance criteria

- A previously-failing (or silently wrong) example now produces a verified homomorphism with the right group; regression test in `tests/` covers it.
- `run_quick.m` green; affected-rows analysis in the Log.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave1-A-fable): **DONE → review.** Branch `ticket/T09-autmuO-fixmes` (stacked on T07 → T10 → T29 → T28), commit `b9d375f`.

  **Reproduction findings (step 1–2) — the failure model is CRASH-on-other-versions, not silent wrongness:**
  - In Magma V2.29-7 the old construction *happens to work*: `CyclicGroup(GrpPC, 4|6).1` and `DihedralGroup(GrpPC, 4|6).2` carry full element orders (measured: C4 .1→4, C6 .1→6, D4 .2→4, D6 .2→6), because this version's pc-presentations chain the composite-order generator (b² = c). But the conventions are genuinely presentation-dependent — `#Generators(DihedralGroup(GrpPC,4)) = 2` while `#Generators(DihedralGroup(GrpPC,6)) = 3` in the same version (which is why the `assert #Dngens eq 2` at :50 was already commented out).
  - **Silent wrongness is impossible in any version**: Magma's `map<>` constructor *rejects* element lists with duplicate domain elements and conflicting images (verified by direct simulation of the order-2-`.1` failure mode: "More than one image is given for a single element of the domain"), and `MapIsHomomorphism` checks f(x·y) = f(x)f(y) for **every** (element, generator) pair plus #image = #domain under `injective:=true`. A wrong-convention version therefore dies loudly at construction (asserts at :51/map<>/MapIsHomomorphism), never emitting wrong Aut data.
  - **The missing shipped rows are not bug casualties**: `quaternion_orders_polarized` has no C4/C6 anywhere (890 rows: C2 379, C2² 353, D4 119, D6 39) and lacks 10.10 / 15.3 / 15.15 — but `HasPolarizedElementOfDegree` is simply **false** for those (D=10 deg 10, D=15 deg 3 and 15 — no polarized element exists). Probed directly.
  - **C4/C6 hunt (step 1)**: searched Eichler orders for cyclotomic non-twisting (O,μ) (condition deg·discO ∈ {c², 3c²}): all instances found are **twisting** → D-groups (D=6·1 deg 2/6, 6·5 deg 30, 6·7 deg 14; D=10/15 all degrees probed directly, all C2²/D6). No C4/C6 instance is known; consistent with the shipped table having none over discO < 1000. (Side find for **T08**: for some Eichler cases, e.g. discO = 30 deg 30, `HasPolarizedElementOfDegree` returns a μ that does **not normalize O**, which crashes `IsTwisting` → `NormalizingElementToGL4` with an illegal-coercion error at `embed-in-GL4.m:51`; my hunt guarded by checking μbμ⁻¹ ⊆ O. T08's canonical μ should enforce normalization.)

  **Fix (steps 3–5), commit `b9d375f`:**
  - `aut_mu_O.m` `Aut`: generators are now **searched canonically** — w_μ := first element of order cyc_order, w_χ := first order-2 element outside ⟨w_μ⟩ with w_μ^{w_χ} = w_μ⁻¹ — never `.1/.2`; the element list is built from the explicit decomposition w_χ^k·w_μ^l with `assert #Set(...) eq #Dn` (bijectivity — the "well-defined decomposition" of step 4); homomorphy + injectivity asserted as before, plus explicit order-preservation asserts on the canonical generators (step 5; injective homs preserve orders, so this pins the convention). Third return value = the canonical generators.
  - `enumerate-O.m` `LMFDBRowEntry`: `AutmuO_generators` now comes from the canonical generators (was `Domain(AutmuO).1/.2` — the second fragile site). Downstream check (step 3): `embed-in-GL4.m` builds `Ahom` over **all** pc-generators `A.i` (i ≤ NumberOfGenerators) with map application — total and convention-safe, no change needed; `GroupName`/`IsCyclic` are presentation-independent.
  - **Regression test** `tests/regression_autmuO_construction.m` (wired into run_quick): D6 (6.2) and D4 (6.6) end-to-end — group name/order, canonical generator orders + dihedral relation + generation, image orders, and `EnhancedImageGL4` at N=3 against the honest product formula #G = #AutIm·#(O/3)ˣ/#(AutIm ∩ ONx) (note **3 ramifies in B₆ so #(O/3)ˣ = 72**, not |GL₂(F₃)| = 48 — a wrong first guess of mine, worth recording); plus the C2² deg-1 path. No C4/C6 case exists to test end-to-end (documented in the test header); the cyclic composite branch is covered by the same structural asserts inside `Aut`.

  **Affected-rows analysis (step 7): none mathematically.** New `LMFDBRowEntry` output compared against devmirror for all D=6/10/15 rows (8 labels): **μ and `AutmuO_generators` byte-identical to shipped** — the canonical search reproduces the old picks exactly in this version, so the shipped D4 (119) and D6 (39) rows carried correct Aut data and no corrected rows need staging. Only `Gerby_gen` differs — the shipped values are ±pairs in O-coordinates from an *older* code state (e.g. 6.2: `{{-1,2,1,0},{2,-2,-1,0}}`), the current repo hardcoded identity, and T07 redefines it as the primitive ker(f)-generator class rep (e.g. 6.2: `{{1,1,3,1}}`) — all 890 rows change `Gerby_gen` (+ gain `gerbiness`) at the **deferred post-T08 polarized regeneration** (T06 wave), no separate staging here per step 7.
  - `tests/run_quick.m` green: **0 failures, 0 skips** (includes T07's gerbiness checks and the new construction test).
