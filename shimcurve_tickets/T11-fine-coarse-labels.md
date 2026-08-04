---
id: T11
title: −1 detection, is_coarse, fine labels, scalar_label
status: review
owner: wave3-N-fable
priority: P1
tier: 1
repos: [ShimCurve, lmfdb]
depends_on: []
questions: [Q5, Q6]
---

## Context

Label/moduli bookkeeping that is currently stubbed:

- `is_coarse` is hardcoded `true` for every row (`enumerate-H.m:272`); the old upload script's TODO (`upload_scripts/shimcurve_generate.py:19`) says the missing piece is "a way to tell if −1 is in the group".
- `fine_label` is set equal to the coarse-style label, `fine_num` is `\N`; the frontend already supports hyphenated fine labels (`~/claude/lmfdb/lmfdb/shimura_curves/main.py:59` FINE regex, `web_curve.py:285-287` merges coarse data into fine pages).
- `scalar_label` ends in a hardcoded `.1` with the comment "we are not sure how to label the scalar subgroup" (`enumerate-H.m:385-386`).

Q5 decides the criterion ((1,−1) ∈ H?), whether gerbiest H are automatically coarse (KG ∋ −1 would imply the current hardcode is *accidentally right* for all shipped rows), and the fine-label grammar. Q6 decides scalar_label.

## Steps

1. **Independent of Q5**: implement `ContainsMinusOne(H)` — test whether the GL₄-image of (1, −1 mod N) lies in H (the element is `EnhancedElementInGL4modN(<identity Aut elt, OmodN!(-1)>, N)`; build it via the enhanced constructors, `code/level-structure/enhanced-constructors.m` / `embed-in-GL4.m`). Compute it for every H in the shipped D=6 enumeration and record the tally in the Log — this is also the empirical answer to Q5.2.
2. Once Q5 confirms the criterion: wire `is_coarse := ContainsMinusOne(H)` (or per answer) into `createRecord`; implement fine-label assignment in `updateLabels` (`enumerate-H.m:288`) per the grammar in Q5.3, including `fine_num`.
3. Once Q6 answers: fix `scalar_label` construction (`:380-387`).
4. Frontend check (lmfdb repo): with a fine row present in a test file, confirm `combined_data` (`web_curve.py:281-290`) resolves it — the coarse-label reconstruction `mu_label + "." + coarse_label` must match the new grammar; adjust if Q5.3 differs.
5. Regenerate the D=6 corpus if any shipped column changes (likely only if some gerbiest H turn out fine — per step 1 tally). Stage update files + commands in the Log.

## Acceptance criteria

- `ContainsMinusOne` implemented + tested (add to `tests/smoke_intrinsics.m`: the full group G contains it; a constructed index-2 subgroup missing it returns false).
- Step-1 tally in the Log (and echoed under Q5 in QUESTIONS.md).
- After Q5/Q6: labels regenerate deterministically; frontend resolves both label kinds on a local check.

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22 (wave3-N-fable): **Implementation landed** on ShimCurve branch `ticket/T11-fine-coarse-labels` (worktree, base 975b2df = tier1core chain T29→T10→T07→T09→T04→T15), commits `e83fb39` (core) + `3d30898` (smoke tests). All changes in `enumerate-H.m` + `tests/smoke_intrinsics.m` only.

  **Step 1 — `ContainsMinusOne(H, O)` (Q5.1).** New intrinsics in `enumerate-H.m`: `MinusOneEnhancedGL4(O, N)` builds the enhanced element ⟨B!1, −O!1⟩ via the enhanced constructors and maps it through `EnhancedElementInGL4modN` (the result is −I₄ — right multiplication by −1 — asserted in the smoke test); `ContainsMinusOne(H, O)` tests membership at the modulus of H's base ring. For the level ≤ 2 rows (working modulus 3·level) the test agrees with the true-level test because H ⊇ ker(reduction to level) ∋ −I₄ there — noted in the docstring.

  **Step 2 — `is_coarse` wired** (`createRecord`): `s\`is_coarse := ContainsMinusOne(Hgp, O)` replaces the hardcoded `true`. **No data value changes**: the tally (below) is all-true, exactly as Q5.2 predicts — the shipped hardcode was accidentally right. Devmirror confirms 0 of 2,587 shipped rows have `is_coarse = f`.

  **Step 3 — fine-label plumbing = documented loud stub.** v1 has no fine curves (gerbiest-only enumeration, Q12.2 + Q5.2). `updateLabels` now refuses with `error "fine-label semantics pending Q5.3 decision …"` if any record lacks (1,−1), with a comment block documenting the decided hyphenated `{coarse}-{fine}` shape, the frontend's `fine_label_re`, and where the suffix assignment goes once Q5.3 closes. Emitted state for all current rows confirmed unchanged: `fine_label = coarse_label`, `fine_num = \N` (checked in-pass on all regenerated rows and on all 2,587 devmirror rows). ⟐ **Q5.3 fine-suffix semantics remain OPEN** — note the frontend suffix regex `\d+\.\d+\.[a-z]+\.\d+\.\d+` has one more numeric slot than modcurves' `M.c.m.n` (candidates: coarse index or coarse genus as 2nd slot), and modcurves store `fine_num = 0` (not NULL) on coarse rows — both to pin when Q5.3 is decided.

  **Step 4 — `scalar_label` (Q6): spec found, implemented, validated.**
  - **Spec + source:** the modular-curve generation convention is the **RSZB GL1-subgroup label `N.i.n`** — Rouse–Sutherland–Zureick-Brown, *ℓ-adic images of Galois for elliptic curves over ℚ* (arXiv:2106.11141 §2.2), implemented as `GL1Label` in `groups/gl2.m` of github.com/AndrewVSutherland/ell-adic-galois-images (MIT; local copy at `~/sage/ell-adic-galois-images`), used for `gps_gl2zhat_fine.scalar_label` (= `GL2ScalarLabel` = `GL1Label(GL2ScalarImage(H))`; knowls `gl2.label`, `columns.gps_gl2zhat_fine.scalar_label`). Components: **N** = level of the subgroup (least modulus from which it is the full preimage; full group → `1.1.1`), **i** = index in (ℤ/N)ˣ, **n** = ordinal among subgroups of the same (level, index), ordered lexicographically by their sorted lists of **Conrey indexes** of the mod-N Dirichlet characters trivial on the subgroup.
  - **Implementation:** `GL1Label(S::GrpMat)` intrinsic in `enumerate-H.m` (docstring carries the full spec + source citation); Conrey helpers ported as file-local functions (no intrinsic-name collisions with e.g. CHIMP). Applied to **nrd(H) ≤ (ℤ/N)ˣ** per the Q6 decision: `scalar_label := GL1Label(getDeterminantImage(H))`, replacing the `"{level}.{index}.1"` placeholder.
  - **Validation:** port reproduces Sutherland's stored labels **6/6** on gps_gl2zhat_fine rows reconstructed from devmirror generators (8.24.0-4.b.1.1→8.2.1, 8.24.0.d.1→8.2.2, 8.48.0-8.d.1.{1,2}→8.4.1, 4.12.0-2.a.1.{1,2}→4.2.1), plus hand-computed Conrey-pairing checks ({1,3}↔8.2.1, {1,7}↔8.2.2, {1,5}→level 4). Pinned in the smoke test.
  - **Effect on data:** every enumerated H has surjective reduced norm, so **every enhanced row's scalar_label becomes `1.1.1`** (nrd(H) = full ⇒ level 1). The X₀(D;N) rows keep `\N` (tablesX0DN unchanged). This changes all 2,198 enhanced devmirror values and all 2,373 in-tree corpus values.
  - **Reverse-engineering the shipped values** (for the T27 reload story, per coordinator/T26 intel): shipped values like `3.4.1`, `6.12.1` are `{level}.{[H : H ∩ P]}.1` where `P = O1_subs[#O1_subs]` — the **last det-trivial subgroup class in Magma's `Subgroups(G,KG)` enumeration order** (pre-T29 code, see `git show 97bef4f~1:…enumerate-H.m` line 361). P was an unstable, non-canonical pick, generally a *proper* subgroup of the norm kernel, and `[H : H∩P]` varies with H — which is why a single level shows a scatter of middle values (level 6: 2/4/6/8/12) and why `3.4.1` exceeds φ(3)=2. The shipped middle component measures nothing canonical; T29 already replaced P by the true norm kernel (making it uniformly φ(N)), and T11 now replaces the whole format.

  **Artifact staged:** `shimcurve_tickets/artifacts/T11-labels-update.txt` (label|is_coarse|scalar_label, canonical T29 labels) + `T11-labels-invariants.txt` (adds deg_mu|level|index|genus|coarse_class|coarse_num|autmuO_norms join keys) + `T11-README.md` (PROVISIONAL banner). From a fresh in-memory pass over all 16 in-tree (deg,N) parameters — **no data/ files regenerated** (the post-T08 reconciled regeneration picks the new columns up from the code). Note: since the payload is constant across rows (T | 1.1.1), this particular update is label-permutation-invariant — safe under any relabeling — but staged PROVISIONAL pending T27 per protocol anyway. Load (T27 time, after `gps_shimura` reload with canonical labels): `db.gps_shimura.update_from_file("T11-labels-update.txt", label_col="label", sep="|")`.

  **Handoff to T26 (knowl):** suggested scalar_label sentence — "the label `N.i.n` of the image of H under the reduced norm, viewed as an open subgroup of GL₁(Ẑ) = Ẑˣ, labeled exactly as for modular curves ({{KNOWL('gl2.label')}}; arXiv:2106.11141 §2.2): N = level, i = index, n = ordinal under the lexicographic ordering of the corresponding groups of Conrey characters. All v1 rows have surjective reduced norm, hence scalar_label = 1.1.1." T26's draft `shimcurve.label.md` grammar is fully consistent with what this branch emits.

- 2026-07-22 (wave3-N-fable): **Tally + verification complete → review.**

  **Step-1 tally (full pass, 16 (deg,N) pairs, 996s):** `ContainsMinusOne` true for **2,373 / 2,373** subgroups — 2,198 shipped-parameter rows (deg μ ∈ {1,2,6} × N ∈ {1,2,3,4,6}) + 175 deg-1 N=5 rows — **0 fine**; `(1,−1) ∈ KG` held mechanically at every (deg,N). Q5.2's structural argument is empirically CONFIRMED (echoed under Q5 in QUESTIONS.md as agent data). Per-pair row counts equal the in-tree file counts 16/16, and the fresh pass's canonical labels are **set-identical to the in-tree T29 corpus labels 16/16** (T11's edits do not perturb label assignment; verified by per-file diff).

  **What changes vs stays for shipped data:** `is_coarse` — no value changes (all T before and after; devmirror has 0 false among 2,587). `fine_label`/`fine_num` — no changes (`= coarse_label` / `\N` on every row, before and after). `scalar_label` — **every enhanced row changes to `1.1.1`**: in-tree T29-era corpus stores `{level}.{φ(N)}.1` (canonical G1, deterministic, placeholder format — e.g. `5.4.1` at N=5), shipped devmirror rows store pre-T29 `{level}.{[H:H∩P]}.1` for the unstable pick P (scattered values `3.4.1`, `6.12.1`, …); the 389 X₀(D;N) rows keep `\N`. No `data/` files regenerated (per plan — the post-T08 reconciled regeneration picks the new columns up from code).

  **Frontend check (ticket step 4, read-only):** `sage -python` unit check importing the real `lmfdb.shimura_curves.main` — `LABEL_RE`/`coarse_label_re` accept the emitted labels (maximal 7-comp, Eichler 8-comp, multi-letter class; all 2,373 artifact labels pass the coarse regex), the `combined_data` reconstruction identity `mu_label + "." + coarse_label == label` holds on all 2,587 devmirror rows and all fresh rows, and hypothetical fine labels matching the frontend's own `fine_label_re` reconstruct regex-valid coarse labels from the (mu_label, coarse_label) columns. **No frontend change needed for the coarse grammar.** T24 handoff (fine-row-only paths, dormant until fine curves exist): `web_curve.py:387` links `self.coarse_label` bare and `:392` searches `{'coarse_label': self.label}` — both treat the 5-component `coarse_label` COLUMN as a full label; under the column convention (suffix without mu prefix, as `combined_data:286`, `:410`, `:419` correctly assume) they should use `mu_label + "." + coarse_label` resp. match on `(mu_label, coarse_label-suffix)`. Same audit applies to `main.py:639` (`parents = [rec["coarse_label"]] + …` needs the mu prefix). `shimcurve_points/modelmaps` queries keyed on `self.coarse_label` (`web_curve.py:431,567,765-778`) should be checked against what T02/T03 store in `curve_label`/`domain_label` (full vs suffix).

  **Tests:** `tests/run_quick.m` green (0 failures, 0 skips), including T15's obstruction tests and the T29 determinism regression (which now also pins the new scalar_label). New smoke tests: acceptance pair for `ContainsMinusOne` (full G true; constructed index-2 subgroup of ⟨(1,−1)⟩ missing it false), GL1Label ground-truth values, and coarse-row invariants on generated records.

  **Flags:** (i) ⟐ **Q5.3 fine-suffix semantics OPEN** — fine labeling is a loud error stub; also pin whether shimura adopts modcurves' `fine_num = 0` for coarse rows (currently `\N`), and the meaning of the extra numeric slot in the frontend's fine-suffix regex vs modcurves' `M.c.m.n`. (ii) Q3 Pollack-index cascade PENDING — label arity untouched here, as instructed. (iii) Artifact is label-keyed → PROVISIONAL pending T27 (though this particular payload is constant across rows, hence label-permutation-invariant — see T11-README.md).
